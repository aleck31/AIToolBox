import os
import gradio as gr
from fastapi import Request
from typing import Callable, Dict
from .handlers import ChatHandlers, CHAT_STYLES
from core.logger import logger


def create_chat_interface() -> gr.ChatInterface:
    """Create chat interface with handlers"""
    
    # Create chat interface
    chat_interface = gr.ChatInterface(
        description="Let's chat ... (Powered by Bedrock)",
        fn=ChatHandlers.handle_chat,
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
        additional_inputs=[
            gr.Radio(
                label="Style:", 
                choices=list(CHAT_STYLES.keys()),
                value="正常",
                info="Select conversation style"
            )
        ]
    )

    return chat_interface

# Create interface
tab_chatbot = create_chat_interface()
