# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from llm import claude3
from utils import common, AppConf
from view import chatbox, text, code, vision, draw



def login(username, password):
    # tobeFix: cannot set the value to login_user
    AppConf.login_user = username 
    if common.verify_user(username, password):
        # If a new user logs in, clear the history by default
        if username != AppConf.login_user:
            claude3.clear_memory()        
        return True
    else:
        return False


def update_setting(model_id):
    AppConf.model_id = model_id
    gr.Info("App settings updated.")


with gr.Blocks() as tab_setting:
    description = gr.Markdown("Toolbox Settings")
    with gr.Row():
        with gr.Column(scale=15):            
            input_model = gr.Textbox(AppConf.model_id, label="Language Model", max_lines=1)
            image_model = gr.Textbox(AppConf.image_llm, label="Image Model", max_lines=1, interactive=False)
        with gr.Column(scale=1):
            gr.Textbox(AppConf.login_user, label='User', max_lines=1, interactive=False)
    with gr.Row():
        with gr.Column(scale=1):   
            btn_submit = gr.Button(value='☑️ Update', min_width=120)
            btn_submit.click(update_setting, input_model, None)
        with gr.Column(scale=15):
            pass


app = gr.TabbedInterface(
    [
        chatbox.tab_claude, chatbox.tab_gemini, 
        text.tab_translate, text.tab_rewrite, text.tab_summary, 
        code.tab_code, code.tab_format, 
        vision.tab_vision, draw.tab_draw, 
        tab_setting
    ], 
    tab_names= [
        "Claude 🤖", "Gemini 👾", 
        "Translate 🇺🇳", "ReWrite ✍🏼", "Summary 📰", 
        "Code 💻", "Formatter 🔣", 
        "Vision 👀", "Draw 🎨", 
        "Setting ⚙️"
    ],
    title="AI ToolBox",
    theme="Base",
    css="footer {visibility: hidden}"
    )


if __name__ == "__main__":
    app.queue().launch(
        # share=True,
        # debug=True,
        auth=login,
        server_name='0.0.0.0',
        server_port=8886,
        show_api=False
    )
