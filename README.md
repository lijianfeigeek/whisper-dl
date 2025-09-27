# YouTube → Whisper 转录服务

一个基于 FastAPI 的异步 YouTube 音频转录服务，使用 Whisper AI 模型将 YouTube 视频转换为文字稿。

## 功能特性

- 🎥 支持 YouTube 视频链接音频提取
- 🤖 使用 Whisper AI 进行高精度语音识别
- 📊 实时进度跟踪（通过 WebSocket）
- 🚀 异步处理，不阻塞 API 请求
- 🐳 Docker 容器化部署
- 🌍 支持多语言转录

## 快速开始

### 前置要求

- Docker 和 Docker Compose
- 至少 1GB 可用磁盘空间（用于模型文件）

### 1. 下载 Whisper 模型

本项目使用 Whisper.cpp 的 GGML 格式模型，推荐下载以下模型：

```bash
# 创建模型目录
mkdir -p whisper_bin

# 下载 large-v3-turbo 模型（推荐平衡性能和质量）
cd whisper_bin
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin

# 或者下载其他模型：
# 小模型（速度快，质量较低）
# wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin

# 中等模型（平衡）
# wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin

# 大模型（高质量，速度较慢）
# wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin
```

### 2. 启动服务

```bash
# 构建并启动 Docker 容器
docker-compose up --build -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

服务启动后，API 将在 `http://localhost:8000` 运行。

## API 接口

### 1. 启动转录任务

**POST** `/start`

请求体：
```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "language": "zh"  // 可选：zh, en 等，不指定则自动检测
}
```

响应：
```json
{
  "job_id": "uuid-string"
}
```

### 2. 查询任务状态

**GET** `/status/{job_id}`

响应：
```json
{
  "job_id": "uuid-string",
  "status": "completed",  // queued, processing, completed, failed
  "progress": 1.0,        // 0.0 到 1.0
  "transcript": "转录的文字内容...",
  "error": null
}
```

### 3. WebSocket 实时进度

**WebSocket** `/ws/{job_id}`

连接后接收实时进度更新：
```json
{
  "job_id": "uuid-string",
  "progress": 0.45
}
```

### 4. 健康检查

**GET** `/ping`

响应：
```json
{
  "status": "ok"
}
```

## API 文档

启动服务后，访问以下地址查看交互式 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 使用示例

### Python 示例

```python
import requests
import json
import time

# 启动转录任务
response = requests.post("http://localhost:8000/start", json={
    "url": "https://www.youtube.com/watch?v=example",
    "language": "zh"
})
job_id = response.json()["job_id"]

# 轮询查询结果
while True:
    status = requests.get(f"http://localhost:8000/status/{job_id}").json()
    print(f"进度: {status['progress']*100:.1f}%")

    if status["status"] == "completed":
        print("转录完成:")
        print(status["transcript"])
        break
    elif status["status"] == "failed":
        print("转录失败:", status["error"])
        break

    time.sleep(2)
```

### cURL 示例

```bash
# 启动任务
curl -X POST "http://localhost:8000/start" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=example", "language": "zh"}'

# 查询状态
curl "http://localhost:8000/status/{job_id}"
```

## 项目结构

```
whisper-dl/
├── main.py              # FastAPI 应用主文件
├── docker-compose.yml   # Docker 容器编排
├── Dockerfile          # Docker 镜像构建
├── requirements.txt    # Python 依赖
├── whisper_bin/        # Whisper 模型文件目录
│   └── ggml-large-v3-turbo-q5_0.bin
├── downloads/          # 下载的音频和转录文件
├── .gitignore          # Git 忽略文件
└── README.md           # 项目说明
```

## 工作原理

1. **音频下载**: 使用 yt-dlp 下载 YouTube 视频的音频
2. **格式转换**: 使用 ffmpeg 将音频转换为 16kHz 单声道 WAV
3. **语音识别**: 使用 Whisper.cpp 进行本地语音识别
4. **进度跟踪**: 通过 WebSocket 实时推送进度更新
5. **文件清理**: 转录完成后自动删除临时音频文件

## 环境变量

可以通过环境变量配置 Whisper 参数：

```bash
# Whisper 可执行文件路径
WHISPER_BIN=/usr/local/bin/whisper-cli

# 模型文件路径
WHISPER_MODEL=/app/whisper_bin/whisper-ggml-large-v3-turbo-q5_0.bin
```

## 故障排除

### 常见问题

1. **模型文件不存在**
   - 确保 `whisper_bin/` 目录中有 `.bin` 模型文件
   - 检查 Docker 卷挂载是否正确

2. **音频下载失败**
   - 检查 YouTube 链接是否有效
   - 确认网络连接正常

3. **转录速度慢**
   - 使用更小的模型（如 base 或 medium）
   - 检查系统资源使用情况

### 查看日志

```bash
# 查看容器日志
docker-compose logs -f yt-whisper-api

# 进入容器调试
docker-compose exec yt-whisper-api bash
```

### 重置项目

```bash
# 停止并删除容器
docker-compose down

# 删除下载的文件
rm -rf downloads/*

# 重新构建并启动
docker-compose up --build -d
```

## 许可证

本项目基于 MIT 许可证开源。