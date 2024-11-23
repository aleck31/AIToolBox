# Copyright iX.
# SPDX-License-Identifier: MIT-0
import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from modules.login import router as login_router, get_user
import gradio as gr
from common.llm_config import init_default_llm_models
from modules.chatbot.ui import tab_chatbot
from modules.chatbot_gemini.ui import tab_gemini
from modules.text.ui import tab_text
from modules.vision.ui import tab_vision
from modules.coding import view_code
from modules.oneshot.ui import tab_oneshot
from modules.draw import view_draw
from modules.setting.ui import tab_setting


def initialize_app():
    """Initialize app configurations"""
    # Initialize default LLM models if none exist
    init_default_llm_models()

css = """ 
    footer {visibility: hidden}
    .app.svelte-182fdeq.svelte-182fdeq {padding: var(--size-4) var(--size-3)}
    """

app = FastAPI()

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get('SECRET_KEY') or "a_very_secret_key",
    session_cookie="session"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include login routes
app.include_router(login_router)

@app.get('/')
def public(request: Request):
    """Root route handler"""
    user = get_user(request)
    if user:
        return RedirectResponse(url='/main')
    else:
        return RedirectResponse(url='/login')

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Create main interface with authentication
_main_ui = gr.TabbedInterface(
    [
        tab_chatbot, tab_gemini, tab_text, tab_vision, tab_oneshot,
        view_code.tab_coding, view_draw.tab_draw, tab_setting
    ],
    tab_names=[
        "Claude 🤖", "Gemini 👾", "Text 📝", "Vision 👀", "OneShot 🎯",
        "Coding 💻", "Draw 🎨", "Setting ⚙️"
    ],
    title="AI Box - GenAI懒人工具箱",
    theme="Base",
    css=css
).queue()

# Mount main interface with auth
app = gr.mount_gradio_app(app, _main_ui, path="/main", auth_dependency=get_user)

if __name__ == "__main__":
    # Initialize app configurations
    initialize_app()
    uvicorn.run(
        app,
        host='127.0.0.1', 
        port=8886
    )
