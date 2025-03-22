# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from .handlers import SummaryHandlers


def create_interface() -> gr.Interface:
    """Create summary interface"""
    # Create interface without eager initialization
    interface = gr.Interface(
        fn=SummaryHandlers.summarize_text,
        inputs=[
            gr.Textbox(
                label="Text or URL",
                placeholder="Enter text or paste a URL (@url) to summarize",
                lines=11
            )
        ],
        additional_inputs_accordion=gr.Accordion(
            label='Options', 
            open=True
        ),
        additional_inputs=[
            gr.Radio(
                label="Target Language:",
                show_label=False,
                info='Select target language',
                choices=['Original', 'Chinese', 'English'],
                value="Original"
            )
        ],
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
        submit_btn=gr.Button("▶️ Summary", variant='primary'),
        clear_btn=gr.Button("🗑️ Clear"),
        flagging_mode='never',
        api_name="summary"
    )
    
    return interface

# Create interface
tab_summary = create_interface()
