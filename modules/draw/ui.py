"""Draw module UI interface"""
import gradio as gr
from .handlers import DrawHandlers, IMAGE_STYLES, IMAGE_RATIOS


def create_interface() -> gr.Blocks:
    """Create image generation interface with handlers"""
    # Create interface without eager initialization
    interface = gr.Blocks(theme=gr.themes.Soft())
    
    with interface:
        gr.Markdown("Draw something interesting...")

        with gr.Row():
            # Input column
            with gr.Column(scale=6):
                with gr.Group():
                    input_prompt = gr.Textbox(
                        label="Prompt:",
                        lines=3,
                        placeholder="Describe what you want to draw..."
                    )
                    original_prompt = gr.State()  # Store original prompt

                # Optional parameters
                input_negative = gr.Text(
                    label="Negative Prompt",
                    placeholder="What you don't want in the image..."
                )

                with gr.Row():
                    # SDXL preset style
                    input_style = gr.Dropdown(
                        choices=IMAGE_STYLES,
                        value='增强(enhance)',
                        label='Picture style:',
                        min_width=240,
                        scale=3
                    )
                    input_ratio = gr.Dropdown(
                        choices=IMAGE_RATIOS,
                        value='2:3',
                        label='Aspect Ratio:',
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
                        components=[input_prompt, original_prompt, input_negative],
                        value='🗑️ Clear'
                    )
                    btn_optimize = gr.Button(
                        "✨ Optimize",
                        variant='secondary'
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
        
        # Save original prompt when input
        input_prompt.input(
            fn=lambda x: x,
            inputs=[input_prompt],
            outputs=[original_prompt]
        )

        # Handle prompt optimization
        btn_optimize.click(
            fn=DrawHandlers.optimize_prompt,
            inputs=[original_prompt, input_style],  # Use stored original prompt
            outputs=[input_prompt]
        )

        # Handle image generation
        btn_img_gen.click(
            fn=DrawHandlers.generate_image,
            inputs=[
                input_prompt,
                input_negative,
                input_ratio,
                input_seed,
                seed_random
            ],
            outputs=[output_image, input_seed]
        )

    return interface

# Create interface
tab_draw = create_interface()
