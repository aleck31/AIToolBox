import gradio as gr
from .handlers import ChatHandlers
from .prompts import CHAT_STYLES


def create_interface() -> gr.Blocks:
    """Create chat interface with optimized handlers and error handling"""

    # Supported file types with specific extensions
    SUPPORTED_FILES = [
        'text', 
        'image',
        '.pdf', '.doc', '.docx', '.md'  # Additional document types
    ]

    mtextbox = gr.MultimodalTextbox(
        file_types=SUPPORTED_FILES,
        placeholder="Type a message or upload files (images/documents)",
        stop_btn=True,
        max_plain_text_length=2048,
        scale=13,
        min_width=90,
        render=False
    )
    
    chatbot = gr.Chatbot(
        type='messages',
        show_copy_button=True,
        min_height=560,
        avatar_images=(None, "modules/assistant/avata_bot.png"),
        render=False,
        height=600,  # Fixed height for better performance
    )

    input_style = gr.Radio(
        label="Chat Style:", 
        show_label=False,
        choices=list(CHAT_STYLES.keys()),
        value="正常",
        info="Select conversation style",
        render=False,
        container=False  # Reduce container overhead
    )

    # Initialize model dropdown
    input_model = gr.Dropdown(
        label="Chat Model:", 
        show_label=False,
        info="Select chat model",
        choices=ChatHandlers.get_available_models(),
        interactive=True
    )

    with gr.Blocks() as chat_interface:

        gr.Markdown("Let me help you with ... (Powered by Bedrock)")

        # Create optimized chat interface
        chat = gr.ChatInterface(
            fn=ChatHandlers.send_message,
            type='messages',
            multimodal=True,
            chatbot=chatbot,
            textbox=mtextbox,
            stop_btn='🟥',
            additional_inputs_accordion=gr.Accordion(
                label='Options', 
                open=False,
                render=False
            ),
            additional_inputs=[input_style, input_model]
        )

        chat.load(
            fn=ChatHandlers.load_history_confs,
            inputs=[],
            outputs=[chat.chatbot, chat.chatbot_state, input_model] # The return value of load_history_confs does not match the outputs
        )

        # Add model selection change handler
        input_model.change(
            fn=ChatHandlers.update_model_id,
            inputs=[input_model],
            outputs=None,
            api_name=False
        )

    return chat_interface

# Create interface
tab_assistant = create_interface()
