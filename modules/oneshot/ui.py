# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from .handlers import OneshotHandlers


def create_oneshot_interface() -> gr.Blocks:
    """Create oneshot interface with handlers"""
    # Create interface without eager initialization
    interface = gr.Blocks(theme=gr.themes.Soft())
    
    with interface:
        gr.Markdown("One-shot Response Generator (Powered by Claude 3.5 v2)")
        
        # Add state for conversation history (list of message dicts)
        history = gr.State(value=[])
        
        with gr.Row():
            with gr.Column(scale=10): # Main content column
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
                        max_plain_text_length=2500,
                        container=False
                    )
                
                with gr.Accordion(label='Thinking Process', open=False):
                    output_thinking = gr.Markdown(
                        header_links=True,
                        show_label=False,
                        line_breaks=True,
                        value=""
                    )
                    
                with gr.Accordion(label='Response', open=True):
                    output_response = gr.Markdown(
                        header_links=True,
                        show_label=False,
                        line_breaks=True,
                        value=""
                    )

            with gr.Column(scale=2, min_width=120): # Button column
                clear_btn = gr.ClearButton(
                    value="🗑️ Clear",
                    components=[input_box, output_thinking, output_response]
                )
                submit_btn = gr.Button("✨ Go", variant="primary")  

        # Event handler functions
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

        # Event bindings
        submit_btn.click(
            fn=update_btn_immediate,  # First update button
            outputs=submit_btn
        ).then(
            fn=OneshotHandlers.gen_with_think,  # Then generate response
            inputs=[input_box, history],
            outputs=[output_thinking, output_response],
            api_name="oneshot"
        ).then(
            fn=update_history,  # update history
            inputs=[input_box, history, output_response],
            outputs=history
        ).then(
            fn=update_btn_label,
            inputs=output_response,
            outputs=submit_btn
        )

        # Clear all contents and reset submit button
        clear_btn.click(
            lambda: (None, None, None, [], "✨ Go"),
            outputs=[input_box, output_thinking, output_response, history, submit_btn]
        )
        
    return interface

# Create interface
tab_oneshot = create_oneshot_interface()
