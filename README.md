# YouTube → Whisper 转录服务

一个基于 FastAPI 的异步 YouTube 音频((**youtube‑dl / yt‑dl**)转录服务，使用 Whisper AI (**本地模型**) 将 YouTube 视频转换为文字稿。

## 功能特性

- 🎥 支持 YouTube 视频链接音频提取(**youtube‑dl / yt‑dl**)
- 🤖 使用 Whisper AI 进行高精度语音识别(本地模型)
- 📊 实时进度跟踪（通过 WebSocket）
- 🚀 异步处理，不阻塞 API 请求
- 🐳 Docker 容器化部署
- 🌍 支持多语言转录
- 🔗 n8n 工作流集成支持

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

## n8n 工作流集成

![](https://raw.githubusercontent.com/lijianfeigeek/whisper-dl/refs/heads/main/SCR-20250927-suxr.png)

本项目可以与 n8n 工作流自动化平台完美集成，实现复杂的自动化转录流程。

### n8n 工作流架构

基于典型的 n8n 工作流模式，您可以构建以下自动化流程：

```
Webhook 触发 → HTTP 请求启动转录 → 轮询检查状态 → AI 处理结果 → 输出/通知
```

### 工作流节点配置

#### 1. Webhook 节点（触发器）
- **方法**: `POST` 或 `GET`
- **路径**: 自定义 webhook 路径
- **用途**: 接收 YouTube URL 和转录参数
- **示例数据**:
```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "language": "zh",
  "callback_url": "https://your-app.com/webhook"
}
```

#### 2. HTTP Request 节点（启动转录）
- **方法**: `POST`
- **URL**: `http://localhost:8000/start`
- **Headers**: `Content-Type: application/json`
- **Body**:
```json
{
  "url": "{{$json.url}}",
  "language": "{{$json.language}}"
}
```

#### 3. 条件判断节点（IF）
- **条件**: 检查 HTTP 响应状态
- **表达式**: `{{ $statusCode === 200 }}`
- **True 分支**: 继续轮询状态
- **False 分支**: 错误处理

#### 4. 循环轮询节点
- **HTTP Request**: 检查任务状态
- **URL**: `http://localhost:8000/status/{{$json.job_id}}`
- **循环条件**: 转录未完成时继续等待
- **等待时间**: 2-5 秒间隔

#### 5. AI Agent 节点（处理结果）
- **用途**: 对转录结果进行后续处理
- **可配置**:
  - 文本总结
  - 关键词提取
  - 内容分类
  - 翻译处理
- **Memory**: 存储上下文信息
- **Tools**: 自定义处理工具

#### 6. 输出节点
- **Webhook**: 回调通知
- **Email**: 发送结果邮件
- **HTTP**: 推送到其他系统
- **Database**: 保存到数据库

### 完整工作流示例

#### 场景1: 自动视频转录并总结
```
1. Webhook 接收 YouTube URL
2. 启动转录任务
3. 轮询直到转录完成
4. AI Agent 生成内容总结
5. 发送邮件通知用户
```

#### 场景2: 批量视频处理
```
1. 定时触发器（每天执行）
2. 从数据库获取待处理视频列表
3. 循环处理每个视频转录
4. AI 提取关键信息
5. 保存到知识库
6. 生成处理报告
```

#### 场景3: 实时转录服务
```
1. Webhook 接收用户请求
2. WebSocket 实时进度跟踪
3. 转录完成后 AI 分析
4. 推送到即时通讯工具
5. 更新用户界面
```

### n8n 环境配置

#### 1. 安装 n8n
```bash
# Docker 方式
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  n8nio/n8n

# 或使用 npm
npm install n8n -g
n8n start
```

#### 2. 配置环境变量
```bash
# n8n 环境变量
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=password

# OpenAI API Key（用于 AI Agent）
OPENAI_API_KEY=your-openai-api-key
```

#### 3. 工作流导入
- 在 n8n 界面中创建新工作流
- 按照上述节点配置构建工作流
- 测试每个节点的执行
- 保存并激活工作流

### 最佳实践

#### 1. 错误处理
- 在每个 HTTP 请求后添加错误处理节点
- 设置重试机制（最多3次）
- 记录错误日志到监控系统

#### 2. 性能优化
- 使用合理的轮询间隔（避免过于频繁）
- 设置超时时间（防止长时间等待）
- 批量处理时控制并发数

#### 3. 安全考虑
- 验证 Webhook 请求来源
- 使用 HTTPS 协议
- 定期轮换 API 密钥
- 限制请求频率

#### 4. 监控和日志
- 记录每个工作流的执行状态
- 设置失败告警通知
- 监控 API 调用频率和响应时间

### 工作流模板

以下是一个基础的工作流 JSON 配置模板：

```json
{
  "name": "YouTube Transcription Workflow",
  "nodes": [
    {
      "parameters": {},
      "id": "webhook-node",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [240, 300]
    },
    {
      "parameters": {
        "url": "http://localhost:8000/start",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "url",
              "value": "={{ $json.url }}"
            },
            {
              "name": "language",
              "value": "={{ $json.language }}"
            }
          ]
        }
      },
      "id": "start-transcription",
      "name": "Start Transcription",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [500, 300]
    }
  ]
}
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

### 🎉 扩展功能

通过 n8n 集成，您可以将此转录服务扩展为：

- **内容创作平台**: 自动转录 YouTube 视频并生成博客文章
- **学习管理系统**: 转录教育视频并生成学习笔记
- **媒体监控**: 监控特定频道的视频内容并生成报告
- **多语言内容**: 自动翻译转录内容到多种语言
- **知识库构建**: 将转录内容结构化存储到知识库中

n8n 的强大功能让您的转录服务能够与数百种其他应用和服务集成，构建完整的自动化工作流程。

## 许可证

本项目基于 MIT 许可证开源。

---

