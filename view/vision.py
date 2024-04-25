# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from gradio_pdf import PDF
from llm import claude3, gemini


def handle_file(file_url, prompt, model):
    match model:
        case 'Claude3':
            resp = claude3.vision_analyze(file_url, prompt)
        case 'Gemini':
            resp = gemini.vision_analyze(file_url, prompt)
        case _:
            pass
    return resp

# tab_vision_deprecated = gr.Interface(
#     analyze_img,
#     inputs=[
#         gr.Image(label='Image', type='filepath', sources=['upload', 'webcam'], show_download_button=False, scale=2),
#         gr.Textbox(label="What do you want me to do?", lines=2, scale=4),
#         gr.Radio(label="Model", choices=['Claude3', 'Gemini'], value='Claude3')
#     ],
#     outputs=gr.Textbox(label='Output', lines=15, scale=4),
#     # live=True,
#     description="I can see 乛◡乛 ",
#     submit_btn= gr.Button("▶️ Go"),
#     clear_btn=gr.Button("🗑️ Clear")
# )


def save_to_state(input):
    '''save input content into tmp State'''
    state = input
    return state


with gr.Blocks() as tab_vision:
    description = gr.Markdown("I can see 乛◡乛")
    with gr.Row():
        saved_path = gr.State()
        with gr.Column(scale=6, min_width=450):
            with gr.Row():
                with gr.Tab("Image"):
                    input_img = gr.Image(label='Image', type='filepath', sources=[
                                         'upload', 'webcam'], show_download_button=False, scale=2)
                    input_img.change(save_to_state, input_img, saved_path)
                with gr.Tab("PDF"):
                    input_pdf = PDF(label='Document', scale=2)
                    input_pdf.change(save_to_state, input_pdf, saved_path)
            with gr.Row():
                with gr.Column(scale=6):
                    input_desc = gr.Textbox(
                        label="What do you want me to do?", lines=2, scale=4)
                with gr.Column(scale=1, min_width=120):
                    input_model = gr.Radio(label="Model", show_label=False, interactive=True,
                                           choices=['Claude3', 'Gemini'], value='Claude3')
            with gr.Row():
                # btn_clear = gr.ClearButton([input_img, input_pdf, input_desc, output], value='🗑️ Clear')
                btn_clear = gr.Button("🗑️ Clear")
                btn_summit = gr.Button("▶️ Go")

        with gr.Column(scale=6, min_width=450):
            output = gr.Textbox(label="Output", lines=15, show_label=True)

        btn_clear.click(None, None, [input_img, input_pdf, output])
        btn_summit.click(fn=handle_file, inputs=[
                         saved_path, input_desc, input_model], outputs=output)
