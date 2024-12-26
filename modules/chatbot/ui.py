import gradio as gr
from .handlers import ChatHandlers
from .prompts import CHAT_STYLES
from core.logger import logger


def create_chat_interface() -> gr.ChatInterface:
    """Create chat interface with handlers"""
    
    # Create chat interface
    chat_interface = gr.ChatInterface(
        description="Let's chat ... (Powered by Bedrock)",
        fn=ChatHandlers.streaming_reply,
        type='messages',
        multimodal=True,
        textbox=gr.MultimodalTextbox(
            file_types=['text', 'image','.pdf'],
            placeholder="Type a message or upload image(s)",
            stop_btn=True,
            max_plain_text_length=2048,
            scale=13,
            min_width=90
        ),
        stop_btn='🟥',
        additional_inputs_accordion=gr.Accordion(
            label='Chat Settings', open=False),
        additional_inputs=[
            gr.Radio(
                label="Chat Style:", 
                show_label=False,
                choices=list(CHAT_STYLES.keys()),
                value="正常",
                info="Select conversation style"
            )
        ]
    )

    return chat_interface

# Create interface
tab_chatbot = create_chat_interface()
