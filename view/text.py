# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from common import AppConf
from llm import lang
from utils import web


tab_translate = gr.Interface(
    lang.text_translate,
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


tab_rewrite = gr.Interface(
    lang.text_rewrite,
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


# tab_summary = gr.Interface(
#     lang.text_summary,
#     inputs=[
#         gr.Textbox(label="Original", lines=12, scale=5),
#     ],
#     outputs=gr.Textbox(label="Summary text", lines=6, scale=5),
#     description="Let me summary the contents for you. (Powered by Claude3 Sonnet v1)",
#     submit_btn= gr.Button("↩️ Run"),
#     clear_btn=gr.Button("🗑️ Clear")
# )


with gr.Blocks() as tab_summary:
    description = gr.Markdown(
        "Summarize article or webpage for you.  (Powered by Bedrock)")
    with gr.Row():
        saved_text = gr.State()
        with gr.Column(scale=6, min_width=450):
            with gr.Row():
                with gr.Tab("Original Text"):
                    input_text = gr.Textbox(
                        label='text', show_label=False, container=False, lines=8)
                    input_text.change(lambda x: x, input_text, saved_text)
                with gr.Tab("Web URL"):
                    with gr.Row():
                        input_url = gr.Textbox(
                            label='url', show_label=False, container=False, lines=1, scale=11)
                        btn_fetch = gr.Button('🧲', min_width=16, visible=False, size='sm', scale=1)
                        # Test only: fetch webpage content
                        # fetched_text = gr.Textbox(label="Fetched text", lines=5)
                        # btn_fetch.click(web.convert_url_text, input_url, fetched_text)
                        input_url.change(lambda: gr.Button(visible=True, interactive=True), None, btn_fetch)
                        btn_fetch.click(web.convert_url_text, input_url, saved_text).then(
                            lambda: gr.Button('🟢', interactive=False), None, btn_fetch)
                    
            with gr.Row():
                btn_clear = gr.Button("🗑️ Clear")
                btn_summit = gr.Button("▶️ Go", variant='primary')

        with gr.Column(scale=6, min_width=450):
            output = gr.Textbox(label="Summary text", lines=11)

        btn_clear.click(None, None, [input_text, input_url, output])
        btn_summit.click(lang.text_summary, saved_text, output).then(
                        lambda: gr.Button('🧲', ), None, btn_fetch)
