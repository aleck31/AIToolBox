"""Draw module UI interface"""
import gradio as gr
from core.module_config import AppConf
from core.logger import logger
from .handlers import DrawHandlers


def create_interface() -> gr.Blocks:
    """Initialize service and create image generation interface with handlers"""
    # Initialize handlers
    handlers = DrawHandlers()
    
    # Create interface
    interface = gr.Blocks(theme=gr.themes.Soft())
    
    with interface:
        gr.Markdown("Creative...")

        with gr.Row():
            with gr.Column(scale=2):
                # Operation area
                input_task = gr.Radio(
                    choices=['Image-Generation', 'Image-Editing', 'Video-Generation'],
                    label="Task type",
                    value="Image-Generation"
                )

            with gr.Column(scale=2):
                input_copy_numb = gr.Number(
                    value=1,
                    label="Number of copies",
                    container=False
                )


        with gr.Row():
            # Input column
            with gr.Column(scale=6):
                input_prompt = gr.Textbox(
                    label="Prompt:",
                    lines=5,
                    placeholder="Describe what you want to draw..."
                )
                
                # Optional parameters
                input_negative = gr.Text(
                    label="Negative Prompt",
                    placeholder="What you don't want in the image..."
                )

            
            # Output column
            with gr.Column(scale=6):
                output_image = gr.Image(
                    interactive=False,
                    label="Generated Image"
                )
        
        # Handle image generation
        btn_img_gen.click(
            fn=handlers.generate_image,
            inputs=[
            ],
            outputs=[output_image]
        )

    return interface

# Create interface
tab_creative = create_interface()
