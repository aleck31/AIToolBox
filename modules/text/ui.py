# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from common import AppConf
from utils import web
from . import text_translate, text_rewrite, text_summary

with gr.Blocks() as tab_text:

    with gr.Tab("Translate 🇺🇳"):
        iface_translate = gr.Interface(
            text_translate,
            inputs=[
                gr.Textbox(label="Original", lines=7),
                gr.Dropdown(label="Source Language", choices=[
                            'auto'], value='auto', container=False),
                gr.Dropdown(label="Target Language",
                            choices=AppConf.LANGS, value='en_US')
            ],
            outputs=gr.Textbox(label="Translated", lines=11, scale=5),
            examples=[
                ["Across the Great Wall we can reach every corner of the world.", "auto", "zh_CN"]],
            cache_examples=False,
            description="Let me help you with the translation. (Powered by Bedrock)",
            submit_btn=gr.Button("▶️ Go", variant='primary'),
            clear_btn=gr.Button("🗑️ Clear")
        )

    with gr.Tab("ReWrite ✍🏼"):
        iface_rewrite = gr.Interface(
            text_rewrite,
            inputs=[
                gr.Textbox(label="Original", lines=7, scale=5),
                # gr.Accordion(),
                gr.Radio(label="Style", choices=AppConf.STYLES, value="正常", scale=1)
            ],
            outputs=gr.Textbox(label="Polished", lines=11, scale=5),
            examples=[["人工智能将对人类文明的发展产生深远影响。", "幽默"]],
            cache_examples=False,
            # live=True,
            description="Let me help you refine the contents. (Powered by Bedrock)",
            submit_btn=gr.Button("▶️ Go", variant='primary'),
            clear_btn=gr.Button("🗑️ Clear")
        )

    with gr.Tab("Summary 📰"):
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
                            # Test only: fetch webpage content
                            # fetched_text = gr.Textbox(label="Fetched text", lines=5)
                            # btn_fetch.click(web.convert_url_text, input_url, fetched_text)
                            input_url.change(lambda: gr.Button(
                                visible=True, interactive=True), None, btn_fetch)
                            btn_fetch.click(lambda: gr.Button('⏳', interactive=False), None, btn_fetch).then(
                                web.convert_url_text, input_url, saved_text).success(lambda: gr.Button('🟢'), None, btn_fetch)

                with gr.Row():
                    input_lang = gr.Radio(label="Language", choices=[
                                        'original', 'Chinese', 'English'], value="original", scale=1, interactive=False)
                with gr.Row():
                    btn_clear = gr.Button("🗑️ Clear")
                    btn_summit = gr.Button("▶️ Go", variant='primary')

            with gr.Column(scale=6, min_width=450):
                gr.Markdown('Summary')
                output = gr.Code(
                    label='markdown',
                    language='markdown'
                )
                # with gr.Accordion('Summary text:', open=True):
                #     output = gr.Markdown(label="Summary", show_label=True, line_breaks=True)            

            btn_clear.click(None, None, [input_text, input_url, output])
            btn_summit.click(text_summary, [saved_text, input_lang], output).then(
                lambda: gr.Button('🧲', ), None, btn_fetch)
