import gradio as gr
from .handlers import ChatHandlers
from .prompts import CHAT_STYLES


def create_interface() -> gr.Blocks:
    """Create chat interface with handlers"""

    mtextbox=gr.MultimodalTextbox(
                file_types=['text', 'image','.pdf'],
                placeholder="Type a message or upload image(s)",
                stop_btn=True,
                max_plain_text_length=2048,
                scale=13,
                min_width=90,
                render=False
            )
    
    chatbot=gr.Chatbot(
        type='messages',
        show_copy_button=True,
        min_height=560,
        avatar_images=(None, "modules/assistant/avata_bot.png"),
        render=False
    )

    input_style = gr.Radio(
        label="Chat Style:", 
        show_label=False,
        choices=list(CHAT_STYLES.keys()),
        value="正常",
        info="Select conversation style",
        render=False
    )

    with gr.Blocks() as chat_interface:

        gr.Markdown("Let me help you with ... (Powered by Bedrock)")

        # Create chat interface with history loading
        chat=gr.ChatInterface(
            fn=ChatHandlers.send_message,
            type='messages',
            multimodal=True,
            chatbot=chatbot,
            textbox=mtextbox,
            stop_btn='🟥',
            additional_inputs_accordion=gr.Accordion(
                label='Chat Settings', 
                open=False,
                render=False
            ),
            additional_inputs=[input_style]
        )

        chat.load(
            fn=ChatHandlers.load_history,
            inputs=[],
            outputs=[chat.chatbot, chat.chatbot_state]  # Update both visual and internal state
        )

    return chat_interface

# Create interface
tab_assistant = create_interface()
