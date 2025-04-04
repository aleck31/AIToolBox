# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from .handlers import SummaryHandlers


def create_interface() -> gr.Blocks:
    """Create summary interface"""
    # Create interface with Blocks
    interface = gr.Blocks()
    
    with interface:
        gr.Markdown("Summarize text or webpage content for you. (Powered by Bedrock)")

        # Define output components first to avoid reference errors
        output_text = gr.Markdown(
            value="",  # Initialize with empty value for streaming
            label="Summary",
            show_copy_button=True,
            header_links=True,
            line_breaks=True,
            container=True,
            min_height=320,
            render=False
        )

        # Main layout row
        with gr.Row():
            with gr.Column(scale=1):
                input_text = gr.Textbox(
                    label="Text or URL",
                    placeholder="Enter text or paste a URL (@url) to summarize",
                    lines=11
                )
                
                with gr.Accordion(label='Options', open=False):
                    input_lang = gr.Radio(
                        label="Target Language:",
                        show_label=False,
                        info='Select target language',
                        choices=['Original', 'Chinese', 'English'],
                        value="Original"
                    )

                    input_model = gr.Dropdown(
                        info="Select summary model",
                        show_label=False,
                        choices=SummaryHandlers.get_available_models(),
                        interactive=True,
                        min_width=120
                    )
                
                with gr.Row():
                    btn_clear = gr.ClearButton(
                        value="🗑️ Clear",
                        components=[input_text, input_lang, output_text]
                    )
                    btn_submit = gr.Button("▶️ Summary", variant='primary')
            
            with gr.Column(scale=1):
                output_text.render()
        
        # Handle submit button click
        btn_submit.click(
            fn=SummaryHandlers.summarize_text,
            inputs=[input_text, input_lang, input_model],
            outputs=output_text,
            api_name="summary"
        )
        
        # Add model selection change handler
        input_model.change(
            fn=SummaryHandlers.update_model_id,
            inputs=[input_model],
            outputs=None,
            api_name=False
        )

        # Add model list refresh on load
        interface.load(
            fn=lambda: gr.Dropdown(choices=SummaryHandlers.get_available_models()),
            inputs=[],
            outputs=[input_model]
        ).then(  # set selected model 
            fn=SummaryHandlers.get_model_id,
            inputs=[],
            outputs=[input_model]  # Update selected model
        )
    
    return interface

# Create interface
tab_summary = create_interface()
