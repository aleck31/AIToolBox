# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from .handlers import SummaryHandlers

def create_summary_interface() -> gr.Interface:
    """Initialize service and create summary interface"""
    # Initialize service
    SummaryHandlers.initialize()
    
    # Create interface
    interface = gr.Interface(
        fn=SummaryHandlers.summarize_text,
        inputs=[
            gr.Textbox(
                label="Text or URL",
                placeholder="Enter text to summarize or paste a URL",
                lines=11
            )
        ],
        additional_inputs=[
            gr.Radio(
                label="Target Language:",
                show_label=False,
                choices=['original', 'Chinese', 'English'],
                value="original"
            )
        ],
        additional_inputs_accordion=gr.Accordion(
            label='Target Language', 
            open=True
        ),
        outputs=[
            gr.Markdown(
                label="Summary",
                header_links=True,
                line_breaks=True,
                container=True,
                show_copy_button=True,
                min_height=320,
                value=""  # Initialize with empty value for streaming
            )
        ],
        description="Summarize text or webpage content for you. (Powered by Bedrock)",
        submit_btn=gr.Button("⌨️ Format", variant='primary'),
        clear_btn=gr.Button("🗑️ Clear"),
        flagging_mode='never',
        api_name="summary"
    )
    
    return interface

# Create interface
tab_summary = create_summary_interface()
