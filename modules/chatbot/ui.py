# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from common import AppConf
from llm import claude3


tab_chatbot = gr.ChatInterface(
    fn=claude3.multimodal_chat,
    type='messages',
    multimodal=True,
    description="Let's chat ... (Powered by Bedrock)",
    textbox=gr.MultimodalTextbox(
        file_types=['image'],
        placeholder="Type a message or upload image(s)",
        scale=13,
        min_width=60
    ),
    stop_btn='🟥',
    additional_inputs_accordion=gr.Accordion(
        label='Chatbot Style', open=False),
    additional_inputs=gr.Radio(
        label="style", choices=AppConf.STYLES,
        value="正常", show_label=False
    )
)
