# GenAI Toolbox

GenAI Toolbox 是一个基于 FastAPI 和 Gradio 构建的 GenAI 应用，提供了用户友好的界面，用于展示和访问 AWS Bedrock 平台的各种 AI 能力，包括聊天机器人、工具调用、翻译、摘要、图像和文档识别、代码生成以及图像生成等功能。

## 概述

该应用程序集成了 AWS Bedrock 平台的多种生成式 AI 模型，通过 Amazon Cognito 提供安全认证和会话管理。基于 Gradio 的 Web 界面提供了直观的用户体验，让您可以轻松体验 AWS Bedrock 的强大功能。

## 功能特点

* **多模态助手** 🤖
  - 由 AWS Bedrock 提供支持的智能 AI 助手，支持流式响应
  - 上下文感知对话能力
  - 多模态内容(文本、图像和文档)支持
  - Tool use (function calling) 集成
  - 支持模型推理扩展思维(Extended thinking)

* **文本处理** 📝
  - 语法和拼写检查
  - 不同风格的文本重写
  - 文本精简以提高简洁性
  - 文本扩展以增强细节
  - 多语言支持

* **视觉识别** 👀
  - 图像分析和描述
  - 文档理解（支持 PDF）
  - 多模型支持（Claude/Nova）
  - 支持相机和剪贴板输入

* **高级功能**
  - **摘要** 📰：文档和文本摘要生成
  - **问答** 🧠：提供带有全面思考过程的回答
  - **编程** 💻：代码生成和分析
  - **绘画** 🎨：AI图像生成
  - **设置** ⚙️：可自定义配置

## 截图展示

### 主界面
![GenAI Toolbox](/assets/screenshot.png "Web UI")

### 多模态聊天
![GenAI Toolbox](/assets/screenshot_chatbot.png "Multimodal Chat")

### 视觉识别
![GenAI Toolbox](/assets/screenshot_vision.png "Vision Recognition")

## 技术特点

* **AWS Bedrock 集成**
  - 灵活的 LLM Provider 管理：
    * 统一的 LLM 配置处理
    * 提供商特定参数优化
    * 高效的提供商缓存和重用
  - 高级流式处理能力：
    * 实时响应流
    * 多模态内容支持
    * 优化的内容处理和规范化
  - 工具集成：
    * 工具使用（函数调用）集成，具有可扩展的注册表

* **服务架构**
  - 分层设计与基础服务抽象：
    * BaseService：Common Session 和 LLM Provider 管理
    * 专门用于聊天、绘画和通用内容的服务
    * 统一的服务工厂，实现高效实例化
  - 模块化会话管理：
    * 标准化的会话数据结构
    * 可插拔存储后端（基于 DynamoDB）
    * 基于 TTL 的高效缓存清理
    * 用于模型和上下文跟踪的会话元数据

## 项目结构

该项目遵循清晰的分层架构：

```
llm-toolbox/
├── app.py          # Main application entry point
├── core/           # Core components
│   ├── auth.py        # Authentication handling (cognito)
│   ├── config.py      # Configuration settings
│   ├── logger.py      # Logging configuration
│   ├── module_config.py    # Module configuration
│   ├── service/         # Service integration
│   │   ├── init.py           # Base service with common functionality
│   │   ├── gen_service.py      # General content generation service
│   │   ├── chat_service.py     # Chat service implementation
│   │   ├── draw_service.py     # Image generation service
│   │   └── service_factory.py    # Service creation factory
│   └── session/        # Session management
│       ├── models.py         # Data models for Session
│       └── store.py          # DynamoDB-based session storage
├── llm/               # LLM implementations
│   ├── init.py               # Base LLM interfaces
│   ├── model_manager.py      # Model management
│   ├── api_providers/        # LLM tools implementations
│   │   ├── init.py             # Abstract interface for LLM providers
│   │   ├── bredrock_converse.py    # Bedrock Converse integration
│   │   └── bedrock_invoke.py    # Bedrock invoke integration
│   └── tools/         # LLM tools implementations
│       └── tool_registry.py  # Tool registry for Bedrock
├── common/            # Common modules
│   ├── login/            # Authentication UI
│   ├── setting/          # Module settings
│   └── main_ui.py        # UI settings
├── modules/           # Feature modules
│   ├── init.py           # Base handler class 
│   ├── assistant/        # Smart Assistant powered by Bedrock 
│   ├── chatbot/          # Basic chatbot implementation
│   ├── text/             # Text processing
│   ├── summary/          # Text summarization
│   ├── vision/           # Image analysis
│   ├── asking/           # Q&A with thinking
│   ├── coding/           # Code-related features
│   └── draw/             # Image generation
└── utils/             # Utility functions
    ├── aws.py           # AWS resource management
    ├── file.py          # File handling utilities
    ├── voice.py         # Voice processing utilities
    └── web.py           # Web-related utilities
```

## 设置

1. 安装依赖项：
```bash
pip install -r requirements.txt
```

2. 配置 AWS 凭证：
```bash
aws configure
```

3. 配置环境文件：
```bash
cp .env.example .env
```

4. 使用您的设置更新环境：
- AWS Region
- Cognito User Pool
- DynamoDB Table name
- 默认 LLM 模型配置

5. 运行应用程序：

```bash
# 在后台运行
./run.sh start

# 或者用于本地测试
uvicorn app:app --host 127.0.0.1 --port 8080 --reload 
```

应用将在 http://localhost:8080 上启动。


## License

MIT License - see LICENSE file for details
