# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from . import gen_with_think

def format_retry_input(current_input, previous_output):
    """Format the retry input maintaining conversation context"""
    if isinstance(current_input, dict):
        text = current_input.get("text", "")
        files = current_input.get("files", [])
    else:
        text = current_input if current_input else ""
        files = []
    
    retry_text = f"""
    Previous conversation:
    User: {text}
    Assistant: {previous_output}

    Please continue our conversation, taking into account the context above. 
    Feel free to:
    - Ask clarifying questions if needed
    - Build upon previous ideas
    - Suggest related topics or alternatives
    - Provide more detailed explanations
    - Challenge assumptions or explore different perspectives

    User: {text}
    """

    return {"text": retry_text, "files": files}

def handle_retry_generation(input_data, previous_output):
    """Handle retry generation with streaming response"""
    formatted_input = format_retry_input(input_data, previous_output)
    for chunk in gen_with_think(formatted_input):
        yield chunk

with gr.Blocks(theme=gr.themes.Soft()) as tab_oneshot:
    gr.Markdown("One-shot Response Generator (Powered by Claude 3.5 v2)")
    
    with gr.Row():
        with gr.Column(scale=10):
            with gr.Row():
                input_box = gr.MultimodalTextbox(
                    show_label=False,
                    file_types=['image', "video", "audio"],
                    file_count='multiple',
                    placeholder="Type a message or upload image(s)",
                    scale=13,
                    min_width=60,
                    lines=8,
                    submit_btn="✨ Go",
                    container=False
                )
            with gr.Accordion(label='Response', open=True):
                output = gr.Markdown(
                    header_links=True,
                    show_label=False,
                    line_breaks=True,
                    value=""
                )

        with gr.Column(scale=2, min_width=200):    
            retry_btn = gr.Button("🤔 Ask further", variant="secondary")  # Updated label
            clear_btn = gr.ClearButton(
                value="🗑️ Clear",
                components=[input_box, output]
            )

    examples = gr.Examples(
        examples=['写一首关于梦想的打油诗'],
        inputs=[input_box]
    )

    # Connect the submit event directly to the input box
    input_box.submit(
        fn=gen_with_think,
        inputs=input_box,
        outputs=output,
        api_name="oneshot"
    )

    # Enhanced retry functionality for better conversation flow
    retry_btn.click(
        fn=handle_retry_generation,
        inputs=[input_box, output],
        outputs=output,
        api_name="oneshot_retry"
    )
