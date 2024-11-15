# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from common import USER_CONF, verify_user
from common.chat_memory import chat_memory
from modules.coding import view_code
from modules.draw import view_draw
from modules.setting import view_setting
from modules.text import view_text
from modules.vision import view_vision
from modules.chatbot import view_chatbox
from modules.oneshot import view_oneshot


def login(username, password):
    if verify_user(username, password):
        if USER_CONF.username != username:
            # Clear old memory if exists
            chat_memory.clear()
            USER_CONF.set_user(username)
        return True
    else:
        return False


css = """ 
    footer {visibility: hidden}
    .app.svelte-182fdeq.svelte-182fdeq {padding: var(--size-4) var(--size-3)}
    """


app = gr.TabbedInterface(
    [
        view_chatbox.tab_claude, view_chatbox.tab_gemini,
        view_text.tab_translate, view_text.tab_rewrite,
        view_text.tab_summary, view_vision.tab_vision,
        view_code.tab_code, view_oneshot.tab_oneshot,
        view_draw.tab_draw, view_setting.tab_setting
    ],
    tab_names=[
        "Claude 🤖", "Gemini 👾",
        "Translate 🇺🇳", "ReWrite ✍🏼",
        "Summary 📰", "Vision 👀",
        "Code 💻", "OneShot 🎯",
        "Draw 🎨", "Setting ⚙️"
    ],
    title="AI Box - GenAI懒人工具箱",
    theme="Base",
    css=css
)


if __name__ == "__main__":
    app.queue().launch(
        # share=True,
        # debug=True,
        auth=login,
        # server_name='0.0.0.0',
        server_port=5006,
        show_api=False
    )
