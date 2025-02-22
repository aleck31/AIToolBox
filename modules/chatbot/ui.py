import gradio as gr
from .handlers import ChatbotHandlers
from .prompts import GEMINI_CHAT_STYLES


def create_interface() -> gr.Blocks:
    """Create chat interface with handlers"""

    # State to store current model choices
    model_choices_state = gr.State()

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
        avatar_images=(None, "modules/chatbot/avata_bot.png"),
        render=False
    )

    input_model = gr.Dropdown(
        label="Chat Model:", 
        show_label=False,
        info="Select chat model",
        choices=ChatbotHandlers.get_available_models(),
        interactive=True
    )

    input_style = gr.Dropdown(
        label="Chat Style:", 
        show_label=False,
        info="Select conversation style",
        choices={k: v["name"] for k, v in GEMINI_CHAT_STYLES.items()},
        value="default"
    )

    with gr.Blocks(analytics_enabled=False) as chat_interface:
        gr.Markdown("Let's chat ...")

        # Create chat interface with history loading
        chat = gr.ChatInterface(
            fn=ChatbotHandlers.send_message,
            type='messages',
            multimodal=True,
            chatbot=chatbot,
            textbox=mtextbox,
            stop_btn='🟥',
            additional_inputs_accordion=gr.Accordion(
                label='Chat Options', 
                open=False,
                render=False
            ),
            additional_inputs=[input_style, input_model]
        )

        # Load chat history and configuration on startup
        chat.load(  # Update model choices state
        #     fn=ChatbotHandlers.get_available_models,
        #     inputs=[],
        #     outputs=[model_choices_state]
        # ).success(  # Update dropdown with choices
        #     fn=lambda choices: gr.Dropdown(choices=choices),
        #     inputs=[model_choices_state],
        #     outputs=[input_model]
        # ).then(  # Load chat history and selected model
            fn=ChatbotHandlers.load_history_confs,
            inputs=[],
            outputs=[chat.chatbot, chat.chatbot_state, input_model]  # Update history and selected model
        )

        # Add model selection change handler
        input_model.change(
            fn=ChatbotHandlers.update_model_id,
            inputs=[input_model],
            outputs=None,
            api_name=False
        )

    return chat_interface

# Create interface
tab_chatbot = create_interface()
