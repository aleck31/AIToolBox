# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from . import multimodal_chat, CHAT_STYLES


# add a handler to call the corresponding multimodal_chat function based on chat settings

tab_chatbot = gr.ChatInterface(
    description="Let's chat ... (Powered by Bedrock)",
    fn=multimodal_chat,
    type='messages',
    multimodal=True,
    textbox=gr.MultimodalTextbox(
        file_types=['image'],
        placeholder="Type a message or upload image(s)",
        scale=13,
        min_width=90
    ),
    stop_btn='🟥',
    additional_inputs_accordion=gr.Accordion(
        label='Chat Settings', open=False),
    additional_inputs=gr.Radio(
        label="Style:", choices=list(CHAT_STYLES.keys()),
        value="正常"
    )
)
