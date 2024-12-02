# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from . import multimodal_chat


tab_gemini = gr.ChatInterface(
    fn=multimodal_chat,
    type='messages',
    multimodal=True,
    description="Let's chat ... (Powered by Gemini)",
    textbox=gr.MultimodalTextbox(
        file_types=['image', "video", "audio"],
        file_count='multiple',
        placeholder="Type a message or upload image(s)",
        scale=13,
        min_width=90
    ),
    stop_btn='🟥'
)
