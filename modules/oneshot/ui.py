# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from .handlers import OneshotHandlers

with gr.Blocks(theme=gr.themes.Soft()) as tab_oneshot:
    gr.Markdown("One-shot Response Generator (Powered by Claude 3.5 v2)")
    
    # Add state for conversation history (list of message dicts)
    history = gr.State(value=[])
    
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
                    submit_btn=None,
                    container=False
                )
            
            with gr.Accordion(label='Thinking Process', open=False):
                thinking_output = gr.Markdown(
                    header_links=True,
                    show_label=False,
                    line_breaks=True,
                    value=""
                )
                
            with gr.Accordion(label='Response', open=True):
                response_output = gr.Markdown(
                    header_links=True,
                    show_label=False,
                    line_breaks=True,
                    value=""
                )

        with gr.Column(scale=2, min_width=200):
            submit_btn = gr.Button("✨ Go", variant="primary", scale=1)  
            clear_btn = gr.ClearButton(
                value="🗑️ Clear",
                components=[input_box, thinking_output, response_output]
            )

    def update_btn_immediate():
        """Update button label immediately on click"""
        return "💭 Thinking"

    def update_btn_label(response):
        """Update submit button label after response"""
        return "🤔 Ask further" if response else "✨ Go"

    def update_history(input_data, history, response):
        """Update conversation history with new interaction"""
        return history + [
            {"role": "user", "content": input_data},
            {"role": "assistant", "content": response}
        ]

    # Connect the submit button with history
    submit_btn.click(
        fn=update_btn_immediate,  # First update button
        outputs=submit_btn
    ).then(
        fn=OneshotHandlers.gen_with_think,  # Then generate response
        inputs=[input_box, history],
        outputs=[thinking_output, response_output],
        api_name="oneshot"
    ).then(
        fn=update_history,  # update history
        inputs=[input_box, history, response_output],
        outputs=history
    ).then(
        fn=update_btn_label,
        inputs=response_output,
        outputs=submit_btn
    )

    # Clear all content and reset submit button
    clear_btn.click(
        lambda: (None, None, None, [], "✨ Go"),
        outputs=[input_box, thinking_output, response_output, history, submit_btn]
    )
    # Add Enter key support for input box
    input_box.submit(
        fn=lambda: None,  # Trigger submit button click
        outputs=None
    ).then(
        fn=lambda: gr.Button.click(submit_btn),
        outputs=None
    )
