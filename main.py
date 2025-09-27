import os
import uuid
import subprocess
import re
from pathlib import Path
from typing import Dict, Optional

import asyncio
import yt_dlp
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="YouTube → Whisper API (Async + Progress)")

# ---------- 配置 ----------
DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

WHISPER_BIN = os.getenv("WHISPER_BIN", "/usr/local/bin/whisper-cli")
WHISPER_MODEL = os.getenv(
    "WHISPER_MODEL",
    "/app/whisper_bin/whisper-ggml-large-v3-turbo-q5_0.bin"
)

# ---------- 内存 job 存储 ----------
jobs: Dict[str, dict] = {}

class DownloadRequest(BaseModel):
    url: str
    language: Optional[str] = None  # "zh", "en" 或 None

# ---------- WebSocket hub ----------
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[job_id] = websocket

    def disconnect(self, job_id: str):
        self.active_connections.pop(job_id, None)

    async def send_progress(self, job_id: str, progress: float):
        ws = self.active_connections.get(job_id)
        if ws:
            try:
                await ws.send_json({"job_id": job_id, "progress": progress})
            except:
                pass

manager = ConnectionManager()

# ---------- 启动事件循环 ----------
@app.on_event("startup")
async def startup():
    app.state.loop = asyncio.get_running_loop()

# ---------- 更新进度 ----------
def set_progress(job_id: str, value: float):
    job = jobs.get(job_id)
    if not job:
        return
    job["progress"] = max(job.get("progress", 0.0), value)
    loop = app.state.loop
    coro = manager.send_progress(job_id, job["progress"])
    asyncio.run_coroutine_threadsafe(coro, loop)

# ---------- 下载 + 转写 ----------
def download_and_transcribe(job_id: str, url: str, language: Optional[str]):
    try:
        # 1. 下载音频
        outtmpl = str(DATA_DIR / "%(title)s.%(ext)s")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
        }
        set_progress(job_id, 0.1)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        title = info.get("title", "unknown")
        ext = info.get("ext", "mp3")
        audio_file = DATA_DIR / f"{title}.{ext}"
        if not audio_file.exists():
            raise RuntimeError("Downloaded file missing")

        set_progress(job_id, 0.2)

        # 2. 转 WAV 保证兼容性
        wav_file = DATA_DIR / f"{title}.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(audio_file),
            "-ar", "16000", "-ac", "1", str(wav_file)
        ], check=True)
        audio_file.unlink(missing_ok=True)
        audio_file = wav_file
        set_progress(job_id, 0.3)

        # 3. Whisper 转写
        txt_path = Path(str(audio_file) + ".txt")
        cmd = [
            str(WHISPER_BIN),
            "-m", str(WHISPER_MODEL),
            "-otxt", str(txt_path),
            str(audio_file)
        ]
        if language:
            cmd.extend(["--language", language])

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        pattern = re.compile(r"([0-9.]+)%")
        for line in process.stdout:
            m = pattern.search(line)
            if m:
                percent = float(m.group(1))
                set_progress(job_id, 0.3 + (percent / 100) * 0.6)

        process.wait()
        if process.returncode != 0:
            raise RuntimeError("Whisper failed")

        set_progress(job_id, 0.95)

        # 4. 读取 txt
        if not txt_path.exists():
            raise RuntimeError(f"Whisper output missing: {txt_path}")
        with txt_path.open("r", encoding="utf-8") as f:
            transcript = f.read().strip()

        # 5. 清理音频文件
        audio_file.unlink(missing_ok=True)

        set_progress(job_id, 1.0)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["transcript"] = transcript

    except Exception as e:
        set_progress(job_id, 1.0)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

# ---------- API ----------
@app.post("/start")
async def start_task(req: DownloadRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "progress": 0.0}
    background_tasks.add_task(download_and_transcribe, job_id, req.url, req.language)
    return {"job_id": job_id}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "transcript": job.get("transcript"),
        "error": job.get("error"),
    }

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await manager.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # 维持连接即可
    except WebSocketDisconnect:
        manager.disconnect(job_id)

# ---------- 健康检查 ----------
@app.get("/ping")
async def ping():
    return JSONResponse({"status": "ok"})
