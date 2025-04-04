# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from gradio_pdf import PDF
from .handlers import VisionHandlers


def create_interface() -> gr.Blocks:
    """Initialize and create the vision analysis interface

    Returns:
        gr.Blocks: The configured Gradio interface
    """

    # Create interface
    interface = gr.Blocks()
    
    with interface:
        gr.Markdown("I can see 乛◡乛")
        
        saved_path = gr.State()
        output_text = gr.Markdown(
            value="",
            line_breaks=True,
            container=True,
            show_copy_button=True,
            min_height=320,
            render=False
        )

        with gr.Row():
            with gr.Column(scale=6, min_width=450):
                with gr.Row(min_height=350):
                    with gr.Tab("🖼️Image"):
                        input_img = gr.Image(
                            label='Image Preview', 
                            type='filepath',
                            sources=['upload', 'webcam', 'clipboard'],
                            show_download_button=False,
                            elem_id="vision_image_input"
                        )
                        input_img.change(lambda x: x, input_img, saved_path)
                    with gr.Tab("📄Document"):
                        input_pdf = PDF(
                            label='PDF Preview',
                            elem_id="vision_pdf_input"
                        )
                        input_pdf.change(lambda x: x, input_pdf, saved_path)
                
                with gr.Row():
                    input_require = gr.Textbox(
                        label="What would you like me to analyze?",
                        show_label=False,
                        placeholder="Describe what you want me to look for, or leave empty for a general analysis",
                        lines=3
                    )
                
                with gr.Accordion(
                    label='Options', 
                    open=False
                ):
                    input_model = gr.Dropdown(
                        info="Select vision model",
                        show_label=False,
                        choices=VisionHandlers.get_available_models(),
                        interactive=True,
                        min_width=120
                    )
                
                with gr.Row():
                    btn_clear = gr.ClearButton(
                        value="🗑️ Clear",
                        components=[input_img, input_pdf, input_require, saved_path, output_text]
                    )
                    btn_submit = gr.Button("▶️ Analyze", variant='primary')

            with gr.Column(scale=6, min_width=450):
                gr.Markdown('Analysis Results')
                output_text.render()

        btn_submit.click(
            fn=VisionHandlers.analyze_image,
            inputs=[saved_path, input_require, input_model],
            outputs=output_text,
            api_name="vision_analyze"
        )

        # Add model selection change handler
        input_model.change(
            fn=VisionHandlers.update_model_id,
            inputs=[input_model],
            outputs=None,
            api_name=False
        )

        # Add model list refresh on load
        interface.load(
            fn=lambda: gr.Dropdown(choices=VisionHandlers.get_available_models()),
            inputs=[],
            outputs=[input_model]
        ).then(  # set selected model 
            fn=VisionHandlers.get_model_id,
            inputs=[],
            outputs=[input_model]  # Update selected model
        )

        return interface

# Create interface
tab_vision = create_interface()
