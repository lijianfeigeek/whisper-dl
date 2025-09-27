# 基础镜像
FROM python:3.11-slim

LABEL maintainer="you@example.com"

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y ffmpeg git cmake build-essential && \
    rm -rf /var/lib/apt/lists/*

# 下载并编译 whisper.cpp，只编译 whisper-cli
WORKDIR /opt
RUN git clone https://github.com/ggerganov/whisper.cpp.git && \
    cd whisper.cpp && \
    cmake -B build -DMETAL=ON && \
    cmake --build build -j && \
    cp build/bin/whisper-cli /usr/local/bin/


# 切换到应用目录
WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制模型文件
COPY whisper_bin/ /app/whisper_bin/
RUN chmod +r /app/whisper_bin/*.bin || true

# 复制 FastAPI 程序
COPY main.py .

# 暴露端口
EXPOSE 8000

# 启动 FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
