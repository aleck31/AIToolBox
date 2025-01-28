# GenAI Toolbox

GenAI Toolbox is a Gen-AI application suite built with FastAPI and Gradio, offering a user-friendly interface for accessing various AI capabilities, such as chatbot, translation, summary, image&document recognition, coding and text-to-image etc.

🎉 **What's New in v2.0**
- Optimized performance and reliability
- Enhanced Settings & Configuration
- Improved session management 
- Improved tool handling with better streaming responses
- Integrated image generation directly in the chatbot
- Improved chat history management with session loading
- Optimized token usage by limiting context window
- Enhanced multimodal message handling with descriptive placeholders
- Added BedrockInvoke provider for image/video generation

## Overview
The application integrates multiple AI models including Claude and Gemini, with secure authentication via Amazon Cognito and session management. 
It provides a modular architecture that makes it easy to add new features and AI models.

Its user-friendly Gradio-based web interface provides an intuitive experience.

## Features

* **Multimodal Chatbot** 🤖
  - Claude-powered conversational AI with streaming responses
  - Gemini-powered chat interface
  - Support for text, images, and document inputs
  - Context-aware conversations
  - Tool use (function calling) integration
  - Seamless handling of generated content
  - Supported formats:
    * Images: jpg/jpeg, png, gif, webp
    * Documents: pdf, csv, doc, docx, xls, xlsx, txt, md
    * Video: mp4, webm, mov, etc.

* **Text Processing** 📝
  - Proofreading: Grammar and spelling checks
  - Text rewriting with different styles
  - Text reduction for conciseness
  - Text expansion for detail enhancement
  - Multi-language support

* **Vision Recognition** 👀
  - Image analysis and description
  - Document understanding (PDF support)
  - Multi-model support (Claude/Gemini)
  - Camera and clipboard input support

* **Advanced Features**
  - **Summary** 📰: Document and text summarization
  - **OneShot** 🎯: Quick, single-turn responses
  - **Coding** 💻: Code generation and analysis
  - **Draw** 🎨: AI-powered image generation
  - **Settings** ⚙️: Customizable configurations

## Screenshots

### Main Interface
![GenAI Toolbox](/assets/screenshot.png "Web UI")

### Multimodal Chatbot
![GenAI Toolbox](/assets/screenshot_chatbot.png "Multimodal Chatbot")

### Vision Recognition
![GenAI Toolbox](/assets/screenshot_vision.png "Vision Recognition")

## Technical Features

* **Session Management**
  - Modular architecture with clear separation of concerns:
    * Models: Standardized session data structures
    * Store: Pluggable storage backends (DynamoDB implementation)
  - Standardized session format with metadata and context
  - DynamoDB TTL-based automatic cleanup
  - Efficient session reuse with AWS Cognito token validation

* **LLM Integration**
  - Bedrock converse_stream API for real-time responses
  - Multimodal message support with proper format handling
  - Efficient file processing and streaming
  - Automatic format detection and normalization
  - Tool use (function calling) support with extensible registry
  - Enhanced tool result handling for generated content
  - Optimized streaming responses for real-time updates

## Project Structure

The project follows a clean, layered architecture:

```
llm-toolbox/
├── app.py              # Main application entry point
├── core/               # Core components
│   ├── auth.py        # Authentication handling (cognito)
│   ├── config.py      # Configuration settings
│   ├── logger.py      # Logging configuration
│   ├── module_config.py    # Module configuration
│   ├── integration/   # Service integration
│   │   ├── service_factory.py  # Service creation factory
│   │   ├── chat_service.py     # Chat service orchestration
│   │   └── gen_service.py      # General generation service
│   └── session/       # Session management
│       ├── models.py         # Data models for Session
│       └── store.py          # DynamoDB-based session storage
├── llm/               # LLM implementations
│   ├── init.py               # Base LLM interfaces
│   ├── model_manager.py      # Model management
│   ├── api_providers/        # LLM tools implementations
│   │   ├── base.py             # Abstract interface for LLM providers
│   │   ├── aws_bedrock.py      # AWS Bedrock integration
│   │   └── google_gemini.py    # Google Gemini integration
│   └── tools/         # LLM tools implementations
│       └── bedrock_tools.py  # Tool registry for Bedrock
├── common/            # Common modules
│   ├── login/            # Authentication UI
│   ├── setting/          # Module settings
│   └── main_ui.py        # UI settings
├── modules/           # Feature modules
│   ├── chatbot/          # Basic chatbot implementation
│   ├── chatbot_gemini/   # Gemini-specific chatbot
│   ├── text/             # Text processing
│   ├── summary/          # Text summarization
│   ├── vision/           # Image analysis
│   ├── oneshot/          # Single-shot responses
│   ├── coding/           # Code-related features
│   └── draw/             # Image generation
└── utils/             # Utility functions
    ├── aws.py           # AWS resource management
    ├── file.py          # File handling utilities
    ├── voice.py         # Voice processing utilities
    └── web.py           # Web-related utilities
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure AWS credentials:
```bash
aws configure
```

3. Configure environment file:
```bash
cp .env.example .env
```

4. Update environment with your settings:
- AWS region
- Cognito user pool details
- DynamoDB table names
- Model configurations

5. Run the application:

```bash
uvicorn app:app --host 127.0.0.1 --port 8080 --reload 
```

The server will start on http://localhost:8080 .


## License

MIT License - see LICENSE file for details
