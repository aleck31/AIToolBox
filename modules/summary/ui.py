# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from utils import web
from . import text_summary


with gr.Blocks() as tab_summary:
    gr.Markdown("Summarize article or webpage for you.  (Powered by Bedrock)")
    with gr.Row():
        saved_text = gr.State()
        with gr.Column(scale=6, min_width=450):
            with gr.Row():
                with gr.Tab("Original Text"):
                    input_text = gr.Textbox(
                        label='text', show_label=False, lines=11)
                    input_text.change(lambda x: x, input_text, saved_text)
                with gr.Tab("Web URL"):
                    with gr.Row():
                        input_url = gr.Textbox(
                            label='url', show_label=False, lines=1, scale=11)
                        btn_fetch = gr.Button('🧲', min_width=16, visible=False, size='sm', scale=1)
                        input_url.change(lambda: gr.Button(
                            visible=True, interactive=True), None, btn_fetch)
                        btn_fetch.click(lambda: gr.Button('⏳', interactive=False), None, btn_fetch).then(
                            web.convert_url_text, input_url, saved_text).success(lambda: gr.Button('🟢'), None, btn_fetch)

            with gr.Row():
                input_lang = gr.Radio(label="Target Language:", choices=[
                                    'original', 'Chinese', 'English'], value="original", scale=1)
            with gr.Row():
                btn_clear = gr.Button("🗑️ Clear")
                btn_summit = gr.Button("▶️ Go", variant='primary')

        with gr.Column(scale=6, min_width=450):
            gr.Markdown('Summary')
            output = gr.Markdown(
                header_links=True,
                line_breaks=True,
                container=True,
                show_copy_button=True,
                min_height=320,
                value=""  # Initialize with empty value for streaming
            )

        btn_clear.click(
            lambda: [None, None, ""],
            outputs=[input_text, input_url, output]
        )
        # Update to use streaming response
        btn_summit.click(
            fn=text_summary,
            inputs=[saved_text, input_lang],
            outputs=output,
            api_name="summary"
        )
