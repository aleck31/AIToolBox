"""Draw module UI interface"""
import gradio as gr
from .handlers import DrawHandlers, IMAGE_STYLES, IMAGE_RATIOS


def create_interface() -> gr.Blocks:
    """Create image generation interface with handlers"""
    # Create interface without eager initialization
    interface = gr.Blocks(theme=gr.themes.Soft())
    
    with interface:
        gr.Markdown("Draw something interesting...")

        # Define output components first
        output_image = gr.Image(
            interactive=False,
            label="Generated Image",
            render=False
        )

        # Main layout row
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
                    input_negative = gr.Textbox(
                        info="Negative Prompt",
                        show_label=False,
                        placeholder="What you don't want in the image..."
                    )

                with gr.Accordion(label='Options', open=True):
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
                            scale=7
                        )
                        seed_random = gr.Checkbox(
                            value=True,
                            label='🎲 Random Seed',
                            scale=3
                        )
                    # Add model selection dropdown
                    input_model = gr.Dropdown(
                        info="Select image generation model",
                        show_label=False,
                        choices=DrawHandlers.get_available_models(),
                        interactive=True,
                        min_width=120
                    )
                
                with gr.Row():
                    btn_clean = gr.ClearButton(
                        components=[input_prompt, original_prompt, input_negative, output_image],
                        value='🗑️ Clear'
                    )
                    btn_optimize = gr.Button(
                        "✨ Optimize",
                        variant='secondary'
                    )
                    btn_draw = gr.Button(
                        "🪄 Draw",
                        variant='primary'
                    )
            
            # Output column
            with gr.Column(scale=6):
                output_image.render()
        
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
            outputs=[input_prompt, input_negative]
        )

        # Handle image generation
        btn_draw.click(
            fn=DrawHandlers.generate_image,
            inputs=[
                input_prompt,
                input_negative,
                input_ratio,
                input_seed,
                seed_random,
                input_model
            ],
            outputs=[output_image, input_seed]
        )
        
        # Add model selection change handler
        input_model.change(
            fn=DrawHandlers.update_model_id,
            inputs=[input_model],
            outputs=None,
            api_name=False
        )

        # Add model list refresh on load
        interface.load(
            fn=lambda: gr.Dropdown(choices=DrawHandlers.get_available_models()),
            inputs=[],
            outputs=[input_model]
        ).then(  # set selected model 
            fn=DrawHandlers.get_model_id,
            inputs=[],
            outputs=[input_model]  # Update selected model
        )

    return interface

# Create interface
tab_draw = create_interface()
