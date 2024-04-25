# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from common import USER_CONF, verify_user
# from llm import claude3
from view import chatbox, text, code, vision, draw, setting


def login(username, password):
    # tobeFix: cannot set the value to login_user
    # AppConf.login_user = username
    if verify_user(username, password):
        if USER_CONF.username != username:
            USER_CONF.set_user(username)
        # If a new user logs in, clear the history by default
        # if username != AppConf.login_user:
        #     claude3.clear_memory()
        return True
    else:
        return False


css = """ 
    footer {visibility: hidden}
    .app.svelte-182fdeq.svelte-182fdeq {padding: var(--size-4) var(--size-3)}
    """


app = gr.TabbedInterface(
    [
        chatbox.tab_claude, chatbox.tab_gemini,
        text.tab_translate, text.tab_rewrite,
        text.tab_summary, vision.tab_vision,
        code.tab_code, code.tab_format,
        draw.tab_draw, setting.tab_setting
    ],
    tab_names=[
        "Claude 🤖", "Gemini 👾",
        "Translate 🇺🇳", "ReWrite ✍🏼",
        "Summary 📰", "Vision 👀",
        "Code 💻", "Formatter 🔣",
        "Draw 🎨", "Setting ⚙️"
    ],
    title="AI ToolBox",
    theme="Base",
    css=css
)


if __name__ == "__main__":
    app.queue().launch(
        # share=True,
        # debug=True,
        auth=login,
        server_name='0.0.0.0',
        server_port=5006,
        show_api=False
    )
