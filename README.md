# 智能翻译 Agent

这是一个基于 FastAPI 和 LangChain 构建的智能翻译代理服务。它提供了一个异步 API，用于处理文本和文档的翻译任务，并利用大型语言模型提供高质量的翻译结果。

## ✨ 主要特性

- **异步任务处理**: 使用 FastAPI 的后台任务，实现非阻塞的翻译请求处理，适合处理大型文档或耗时较长的翻译任务。
- **高性能翻译引擎**:
  - **并行处理**: 通过并行处理文档块组，最大化翻译效率。
  - **上下文感知**: 在组内按顺序翻译文本块，以保持翻译的连贯性和上下文准确性。
  - **并发控制**: 使用信号量控制对外部API的并发请求，防止速率限制或服务过载。
- **支持自定义术语**: 允许用户提供术语词典，确保特定术语在翻译过程中的一致性和准确性。
- **可配置和可扩展**:
  - **模型灵活**: 支持配置不同的OpenAI模型（或其他兼容的LLM）。
  - **易于集成**: 提供清晰的 RESTful API 接口，方便与其他服务集成。
- **详细的日志记录**: 内置结构化日志，方便追踪和调试。
- **多种文档格式支持**: 支持处理纯文本、PDF、DOCX 等多种格式的内容。

## 🚀 快速开始

### 1. 环境准备

- Python 3.8+
- poetry (可选, 用于依赖管理)

### 2. 安装依赖

克隆本项目到本地：
```bash
git clone https://github.com/your-username/Translation_agent.git
cd Translation_agent/src
```

安装所需的依赖包：
```bash
pip install -r requirements.txt
```

### 3. 配置

在 `src/` 目录下创建一个 `.env` 文件，并填入必要的配置信息。

```env
OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# 如果使用自定义的OpenAI兼容API，请设置此项
OPENAI_BASE_URL="https://api.openai.com/v1" 
```

你也可以在 `src/config.py` 文件中修改默认的模型、并发数等设置。

### 4. 启动服务

```bash
python main.py
```
或者使用 `uvicorn` 进行热重载开发：
```bash
uvicorn main:app --host 0.0.0.0 --port 8099 --reload
```
服务启动后，API将在 `http://localhost:8099` 上可用。

## 📚 API 文档

服务启动后，你可以在 [http://localhost:8099/docs](http://localhost:8099/docs) 访问自动生成的 Swagger UI API 文档。

### 主要端点

#### `POST /translation/start`

启动一个异步翻译任务。

- **请求体**:
```json
{
  "content": "This is the text to be translated.",
  "target_language": "中文",
  "terminology": {
    "text": "文本"
  }
}
```
- **成功响应 (202 Accepted)**:
```json
{
  "task_id": "some-unique-task-id",
  "status_url": "http://localhost:8099/translation/status/some-unique-task-id",
  "result_url": "http://localhost:8099/translation/result/some-unique-task-id"
}
```

#### `GET /translation/status/{task_id}`

查询翻译任务的当前状态。

- **成功响应 (200 OK)**:
```json
{
  "task_id": "some-unique-task-id",
  "status": "running", // "pending", "running", "completed", "error"
  "error": null
}
```

#### `GET /translation/result/{task_id}`

获取翻译任务的结果。

- **成功响应 (200 OK)**:
```json
{
  "task_id": "some-unique-task-id",
  "status": "completed",
  "translated_content": "这是待翻译的文本。",
  "original_content": "This is the text to be translated.",
  "target_language": "中文",
  "usage": {
    "total_input_tokens": 10,
    "total_output_tokens": 8
  }
}
```

- **任务处理中响应 (202 Accepted)**:
```json
{
  "detail": "任务仍在处理中，当前状态: running"
}
```

## 📝 项目结构
```
Translation_agent/
├── src/
│   ├── api/             # FastAPI相关，包括模型、服务和任务管理器
│   ├── core/            # 核心翻译逻辑，包括文档分块和翻译引擎
│   ├── utils/           # 工具函数，如日志和token计算
│   ├── logs/            # 日志文件目录
│   ├── main.py          # FastAPI应用入口
│   ├── config.py        # 配置文件
│   ├── requirements.txt # Python依赖
│   └── .env.example     # 环境变量示例
└── README.md
```
