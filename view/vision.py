# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from llm import claude3, gemini



def analyze_img(image_url, prompt, model):
    match model:
        case 'Claude3':
            resp = claude3.analyze_img(image_url, prompt)
        case 'Gemini':
            resp = gemini.analyze_img(image_url, prompt)
        case _:
            pass
    return resp


tab_vision = gr.Interface(
    analyze_img,
    inputs=[
        gr.Image(label='Image', type='filepath', show_download_button=False, scale=2),
        gr.Textbox(label="What do you want me to do?", lines=2, scale=4),
        gr.Radio(label="Model", choices=['Claude3', 'Gemini'], value='Claude3')
    ],
    outputs=gr.Textbox(label='Output', lines=15, scale=4),
    # live=True,
    description="I can see 乛◡乛 ",
    submit_btn= gr.Button("↩️ Go"),
    clear_btn=gr.Button("🗑️ Clear")
)
