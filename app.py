# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from common import USER_CONF, verify_user
from common.chat_memory import chat_memory
from common.llm_config import init_default_llm_models
from modules.coding import view_code
from modules.draw import view_draw
from modules.setting.ui import tab_setting
from modules.text.ui import tab_text
from modules.vision import view_vision
from modules.chatbot import view_chatbox
from modules.chatbot_gemini.ui import tab_gemini
from modules.oneshot.ui import tab_oneshot


def login(username, password):
    if verify_user(username, password):
        if USER_CONF.username != username:
            # Clear old memory if exists
            chat_memory.clear()
            USER_CONF.set_user(username)
        return True
    else:
        return False


def initialize_app():
    """Initialize app configurations"""
    # Initialize default LLM models if none exist
    init_default_llm_models()


css = """ 
    footer {visibility: hidden}
    .app.svelte-182fdeq.svelte-182fdeq {padding: var(--size-4) var(--size-3)}
    """


app = gr.TabbedInterface(
    [
        view_chatbox.tab_claude, tab_gemini,
        tab_text, view_vision.tab_vision,
        view_code.tab_coding, tab_oneshot,
        view_draw.tab_draw, tab_setting
    ],
    tab_names=[
        "Claude 🤖", "Gemini 👾",
        "Text 📝", "Vision 👀",
        "Coding 💻", "OneShot 🎯",
        "Draw 🎨", "Setting ⚙️"
    ],
    title="AI Box - GenAI懒人工具箱",
    theme="Base",
    css=css
)


if __name__ == "__main__":
    # Initialize app configurations
    initialize_app()
    
    app.queue().launch(
        # share=True,
        # debug=True,
        auth=login,
        # server_name='0.0.0.0',
        server_port=8886,
        show_api=False
    )
