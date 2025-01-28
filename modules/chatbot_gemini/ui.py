import gradio as gr
from .handlers import GeminiChatHandlers
from .prompts import GEMINI_CHAT_STYLES


def create_interface() -> gr.Blocks:
    """Create chat interface with handlers"""

    mtextbox=gr.MultimodalTextbox(
                file_types=['text', 'image', '.pdf', 'audio', 'video'],
                file_count='multiple',
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
        avatar_images=(None, "modules/chatbot_gemini/avata_bot.png"),
        render=False
    )

    input_style = gr.Dropdown(
        label="Chat Style:", 
        show_label=False,
        info="Select conversation style",
        choices={k: v["name"] for k, v in GEMINI_CHAT_STYLES.items()},
        value="default"
    )

    with gr.Blocks() as chat_interface:
        gr.Markdown("Let's chat ... (Powered by Gemini)")

        # Create chat interface with history loading
        chat = gr.ChatInterface(
            fn=GeminiChatHandlers.send_message,
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

        # Load chat history on startup
        chat.load(
            fn=GeminiChatHandlers.load_history,
            inputs=[],
            outputs=[chat.chatbot, chat.chatbot_state]  # Update both visual and internal state
        )

    return chat_interface

# Create interface
tab_gemini = create_interface()
