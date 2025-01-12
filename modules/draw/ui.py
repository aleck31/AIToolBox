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
        gr.Markdown("Draw something interesting...")

        with gr.Row():
            with gr.Column(scale=2):
                # Operation area
                input_task = gr.Radio(
                    choices=['Text-Image', 'Nova-Generation', 'Nova-Editing'],
                    label="Task type",
                    value="Proofreading ✍️"
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
                
                with gr.Row():
                    # SDXL preset style
                    input_style = gr.Dropdown(
                        choices=AppConf.PICSTYLES,
                        value='增强(enhance)',
                        label='Picture style:',
                        min_width=240,
                        scale=3
                    )
                    input_step = gr.Slider(
                        minimum=10,
                        maximum=150,
                        value=50,
                        step=1,
                        label='Step:',
                        min_width=240,
                        scale=3
                    )
                
                with gr.Row():
                    input_seed = gr.Number(
                        value=0,
                        label="Seed",
                        container=False,
                        scale=5
                    )
                    seed_random = gr.Checkbox(
                        value=True,
                        label='🎲 Random',
                        scale=1
                    )
                
                with gr.Row():
                    btn_text_clean = gr.ClearButton(
                        components=[input_prompt, input_negative],
                        value='🗑️ Clear'
                    )
                    btn_img_gen = gr.Button(
                        "🪄 Draw",
                        variant='primary'
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
                input_prompt,
                input_negative,
                input_style,
                input_step,
                input_seed,
                seed_random
            ],
            outputs=[output_image, input_seed]
        )

    return interface

# Create interface
tab_draw = create_interface()
