# UI module for Gradio components
import gradio as gr
from fastapi import Request
from modules.chatbot.ui import tab_chatbot
from modules.chatbot_gemini.ui import tab_gemini
from modules.text.ui import tab_text
from modules.summary.ui import tab_summary
from modules.vision.ui import tab_vision
from modules.coding.ui import tab_coding
from modules.oneshot.ui import tab_oneshot
from modules.draw.ui import tab_draw
from common.setting.ui import tab_setting
from core.logger import logger

# Custom CSS
css = """ 
    footer {visibility: hidden}
    .app.svelte-182fdeq.svelte-182fdeq {padding: var(--size-4) var(--size-3)}
    """

def create_main_interface(request: Request = None):
    """Create the main Gradio interface with all tabs
    
    Args:
        request: FastAPI request object for auth context
    """
    # Log when interface is being created
    logger.debug(f"Creating chat interface for user: {request.session.get('user', {}).get('username') if request else None}")
    
    interface = gr.TabbedInterface(
        [
            tab_chatbot, tab_gemini, tab_text,
            tab_summary, tab_vision, tab_oneshot,
            tab_coding, tab_draw, 
            tab_setting
        ],
        tab_names=[
            "Claude 🤖", "Gemini 👾", "Text 📝", 
            "Summary 📰", "Vision 👀", "OneShot 🎯",
            "Coding 💻", "Draw 🎨", 
            "Setting ⚙️"
        ],
        title="AI Box - GenAI懒人工具箱",
        theme="Base",
        css=css,
        analytics_enabled=False,  # Disable analytics to prevent session issues
    ).queue()
    
    logger.debug("Main Gradio interface created successfully")
    return interface
