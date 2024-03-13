# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from utils import AppConf
from llm import image



with gr.Blocks() as tab_draw:
    description = gr.Markdown("Draw something interesting... (Powered by SDXL v1)")
    with gr.Tab("Text-Image"):
        with gr.Row():
            with gr.Column(scale=6):
                # input_params = []
                input_prompt = gr.Textbox(label="Prompt", lines=5)
                # optional parameters
                input_negative = gr.Text(label="Negative Prompt")
                with gr.Row():
                    # SDXL preset style
                    input_style = gr.Dropdown(choices=AppConf.PICSTYLES, value='增强(enhance)', label='Picture style:')
                with gr.Row():
                    input_seed = gr.Number(
                        value=-1, label="Seed", 
                        container=False, scale=5
                    )
                    # with gr.Column(scale=1):
                    btn_random = gr.Button('🎲 Random', scale=1)
                    btn_random.click(image.random_seed, None, input_seed)
                with gr.Row():
                    input_step = gr.Slider(10, 150, value=50, step=1, label="Step", scale=6)
                    # with gr.Column(scale=5):
                    # seed randrange(10000000, 99999999)
                with gr.Row():        
                    btn_img_gen = gr.Button("🪄 Draw")                
                    btn_text_clean = gr.ClearButton([input_prompt, input_negative], value='🗑️ Clear')
            with gr.Column(scale=6):
                output_image = gr.Image(interactive=False)            
            btn_img_gen.click(
                fn=image.text_image, 
                inputs=[input_prompt, input_negative, input_style, input_step, input_seed], 
                outputs=output_image
            )

    with gr.Tab("Image-Image"):
        gr.Markdown('TBD')
