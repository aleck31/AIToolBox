import gradio as gr
from .handlers import GeminiChatHandlers
from .prompts import GEMINI_CHAT_STYLES
from core.logger import logger


def create_chat_interface() -> gr.ChatInterface:
    """Create chat interface with handlers"""
    
    # Create chat interface
    chat_interface = gr.ChatInterface(
        description="Let's chat ... (Powered by Gemini)",
        fn=GeminiChatHandlers.streaming_reply,
        type='messages',
        multimodal=True,
        textbox=gr.MultimodalTextbox(
            file_types=['text', 'image', '.pdf', 'audio', 'video'],
            file_count='multiple',
            placeholder="Type a message or upload image(s)",
            stop_btn=True,
            max_plain_text_length=1024,
            scale=13,
            min_width=90
        ),
        stop_btn='🟥',
        additional_inputs_accordion=gr.Accordion(
            label='Chat Settings', open=False),
        additional_inputs=[
            gr.Dropdown(
                label="Chat Style:", 
                show_label=False,
                info="Select conversation style",
                choices={k: v["name"] for k, v in GEMINI_CHAT_STYLES.items()},
                value="default"
            )
        ]
    )

    return chat_interface

# Create interface
tab_gemini = create_chat_interface()
