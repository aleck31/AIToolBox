# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from common import USER_CONF


def save_setting(m1, m2, m3, m4, m5, m6, m7, m8, m9):
    '''Save settings to database'''
    try:
        USER_CONF.set_model_list([
            {"name": "claude3", "model_id": m1},
            {"name": "gemini", "model_id": m2},
            {"name": "gemini-vision", "model_id": m3},
            {"name": "summary", "model_id": m4},
            {"name": "translate", "model_id": m5},
            {"name": "rewrite", "model_id": m6},
            {"name": "vision", "model_id": m7},
            {"name": "code", "model_id": m8},
            {"name": "image", "model_id": m9}
        ])
        gr.Info("App settings updated.")
        return USER_CONF.username
    except:
        raise


def load_setting():
    '''Load settings from database'''
    m1 = USER_CONF.get_model_id('claude3')
    m2 = USER_CONF.get_model_id('gemini')
    m3 = USER_CONF.get_model_id('gemini-vision')
    m4 = USER_CONF.get_model_id('summary')
    m5 = USER_CONF.get_model_id('translate')
    m6 = USER_CONF.get_model_id('rewrite')
    m7 = USER_CONF.get_model_id('vision')
    m8 = USER_CONF.get_model_id('code')
    m9 = USER_CONF.get_model_id('image')
    uname = USER_CONF.username
    return m1, m2, m3, m4, m5, m6, m7, m8, m9, uname


with gr.Blocks() as tab_setting:
    description = gr.Markdown("Configure models for each scenarios")
    with gr.Row():
        with gr.Column(scale=14):
            m1 = gr.Textbox(USER_CONF.get_model_id('claude3'), 
                            label="Model for Chatbot", max_lines=1, interactive=True)
            m2 = gr.Textbox(USER_CONF.get_model_id('gemini'),
                            label="Gemini", max_lines=1, visible=False)
            m3 = gr.Textbox(USER_CONF.get_model_id('gemini-vision'),
                            label="Gemini-Vision", max_lines=1, visible=False)
            m4 = gr.Textbox(USER_CONF.get_model_id('summary'),
                            label="Model for Text", max_lines=1)
            m5 = gr.Textbox(USER_CONF.get_model_id('translate'),
                            label="Translate", max_lines=1)
            m6 = gr.Textbox(USER_CONF.get_model_id('rewrite'),
                            label="Rewrite", max_lines=1, visible=False)
            m7 = gr.Textbox(USER_CONF.get_model_id('vision'),
                            label="Model for Vision", max_lines=1)
            m8 = gr.Textbox(USER_CONF.get_model_id('code'),
                            label="Model for Coding", max_lines=1)
            m9 = gr.Textbox(USER_CONF.get_model_id('image'),
                            label="Text-Image Model", max_lines=1)
        with gr.Column(scale=2):
            uname = gr.Textbox(USER_CONF.username, label='User',
                               max_lines=1, interactive=False)
            
            btn_refresh = gr.Button(value='🔄 Refresh', size='sm')
            btn_refresh.click(load_setting, None, [
                             m1, m2, m3, m4, m5, m6, m7, m8, m9, uname])
            
            btn_submit = gr.Button(value='💾 Save')
            btn_submit.click(save_setting, [
                             m1, m2, m3, m4, m5, m6, m7, m8, m9], uname)
