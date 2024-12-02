# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from common import AppConf
from . import text_image


with gr.Blocks() as tab_draw:
    description = gr.Markdown(
        "Draw something interesting... (Powered by Stable Diffusion)")
    # with gr.Tab("Text-Image"):
    with gr.Row():
        with gr.Column(scale=6):
            # input_params = []
            input_prompt = gr.Textbox(label="Description:", lines=5)
            # optional parameters
            input_negative = gr.Text(label="Negative Prompt")
            with gr.Row():
                # SDXL preset style
                input_style = gr.Dropdown(
                    choices=AppConf.PICSTYLES, value='增强(enhance)', label='Picture style:', min_width=240, scale=3)
                input_step = gr.Slider(
                    10, 150, value=50, step=1, label='Step:', min_width=240, scale=3)
            with gr.Row():
                input_seed = gr.Number(
                    value=0, label="Seed",
                    container=False, scale=5
                )
                # with gr.Column(scale=1):
                # seed randrange(000000001, 4294967295)
                seed_random = gr.Checkbox(True, label='🎲 Random', scale=1)
                # btn_random.click(image.random_seed, None, input_seed)
            with gr.Row():
                btn_text_clean = gr.ClearButton(
                    [input_prompt, input_negative], value='🗑️ Clear')
                btn_img_gen = gr.Button("🪄 Draw", variant='primary')
        with gr.Column(scale=6):
            output_image = gr.Image(interactive=False)
        btn_img_gen.click(
            fn=text_image,
            inputs=[input_prompt, input_negative, input_style,
                    input_step, input_seed, seed_random],
            outputs=[output_image, input_seed]
        )

    # with gr.Tab("Image-Image"):
    #     gr.Markdown('TBD')
