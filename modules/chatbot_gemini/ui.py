import gradio as gr
from .handlers import GeminiChatHandlers
from core.logger import logger


def create_chat_interface() -> gr.ChatInterface:
    """Create chat interface with handlers"""
    
    # Create chat interface
    chat_interface = gr.ChatInterface(
        description="Let's chat ... (Powered by Gemini)",
        fn=GeminiChatHandlers.handle_chat,
        type='messages',
        multimodal=True,
        textbox=gr.MultimodalTextbox(
            file_types=['image', "video", "audio"],
            file_count='multiple',
            placeholder="Type a message or upload image(s)",
            scale=13,
            min_width=90
        ),
        stop_btn='🟥'
    )

    return chat_interface

# Create interface
tab_gemini = create_chat_interface()
