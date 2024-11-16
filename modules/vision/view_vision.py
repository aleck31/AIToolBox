# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from gradio_pdf import PDF
from . import vision_analyze_claude, vision_analyze_gemini


def handle_file(file_path, prompt, model):
    if not file_path:
        yield "Please upload an image or document first."
        return

    match model:
        case 'Claude3':
            for chunk in vision_analyze_claude(file_path, prompt):
                yield chunk
        case 'Gemini':
            for chunk in vision_analyze_gemini(file_path, prompt):
                yield chunk
        case _:
            yield "Invalid model selected"


with gr.Blocks() as tab_vision:
    description = gr.Markdown("I can see 乛◡乛")
    with gr.Row():
        saved_path = gr.State()
        with gr.Column(scale=6, min_width=450):
            with gr.Row():
                with gr.Tab("Image"):
                    input_img = gr.Image(
                        label='Preview', type='filepath',
                        sources=['upload', 'webcam'],
                        show_download_button=False
                    )
                    input_img.change(lambda x: x, input_img, saved_path)
                with gr.Tab("Document"):
                    input_pdf = PDF(label='PDF preview')
                    input_pdf.change(lambda x: x, input_pdf, saved_path)
            with gr.Row():
                input_desc = gr.Textbox(
                    label="What do you want me to do?", lines=3, scale=6)
                input_model = gr.Radio(
                    label="Model:", interactive=True, scale=1, min_width=120,
                    choices=['Claude3', 'Gemini'], value='Claude3')
            with gr.Row():
                # btn_clear = gr.ClearButton([input_img, input_pdf, input_desc, output], value='🗑️ Clear')
                btn_clear = gr.Button("🗑️ Clear")
                btn_summit = gr.Button("▶️ Go", variant='primary')

        with gr.Column(scale=6, min_width=450):
            with gr.Accordion('Output:', open=True):
                output = gr.Markdown(label="Output", show_label=True, line_breaks=True)

        btn_clear.click(None, None, [input_img, input_pdf, output])
        btn_summit.click(
            fn=handle_file,
            inputs=[saved_path, input_desc, input_model],
            outputs=output
        )
