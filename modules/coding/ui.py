# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from .handlers import CodingHandlers, DEV_LANGS


def create_coding_interface() -> gr.Blocks:
    """Initialize service and create coding interface with handlers"""
    # Initialize service
    CodingHandlers.initialize()
    
    # Create interface
    interface = gr.Blocks(theme=gr.themes.Soft())
    
    with interface:
        gr.Markdown("Code Generation")
        
        # Main layout row
        with gr.Row():
            # Left column: Input and output
            with gr.Column(scale=7, min_width=500):
                # Requirements input
                input_requirement = gr.Textbox(
                    label="Describe your requirements:",
                    placeholder="What would you like me to help you code?",
                    lines=5,
                    show_copy_button=True
                )
                
                # Architecture Design output
                with gr.Accordion(label="Architecture Design", open=False):
                    output_thinking = gr.Markdown(
                        label='Design',
                        show_label=False,
                        line_breaks=True,
                        header_links=True,
                        value=""
                    )
                
                # Generated code output
                with gr.Accordion(label="Generated Code", open=True):
                    code_output = gr.Markdown(
                        label='Code',
                        show_label=False,
                        line_breaks=True,
                        min_height=120,
                        show_copy_button=True,
                        header_links=True
                    )
            
            # Right column: Settings and controls
            with gr.Column(scale=3, min_width=120):
                # Language selection
                input_lang = gr.Radio(
                    label="Programming Language",
                    choices=DEV_LANGS,
                    value="Python"
                )
                with gr.Row():
                    btn_code_clear = gr.ClearButton(
                        value="🗑️ Clear",
                        components=[input_requirement, output_thinking, code_output]
                    )
                    btn_code_submit = gr.Button(
                        value="⌨️ Generate",
                        variant="primary"
                    )

        # Event handler functions
        def update_btn_immediate():
            """Update button label immediately on click"""
            return "💭 Thinking"

        def update_btn_label(code):
            """Update submit button label after response"""
            return "🤔 Regenerate" if code else "⌨️ Generate"

        # Event bindings
        btn_code_submit.click(
            fn=update_btn_immediate,  # First update button
            outputs=btn_code_submit
        ).then(
            fn=CodingHandlers.gen_code,  # Then generate code
            inputs=[input_requirement, input_lang],
            outputs=[output_thinking, code_output],
            api_name="gen_code"
        ).then(
            fn=update_btn_label,  # Update button based on result
            inputs=code_output,
            outputs=btn_code_submit
        )
        
    return interface

# Create interface
tab_coding = create_coding_interface()
