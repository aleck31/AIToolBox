# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from utils import AppConf, web
from llm import lang



tab_translate = gr.Interface(
    lang.text_translate,
    inputs=[
        gr.Textbox(label="Original", lines=7),
        gr.Dropdown(label="Source Language", choices=['auto'], value='auto', container=False),
        gr.Dropdown(label="Target Language", choices=AppConf.LANGS, value='en_US')
    ],
    outputs=gr.Textbox(label="Translated", lines=11, scale=5),
    examples=[["Across the Great Wall we can reach every corner of the world.", "auto", "zh_CN"]],
    cache_examples=False,
    description="Let me translate the text for you. (Powered by Claude3)",
    submit_btn= gr.Button("▶️ Go"),
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
    description="Let me help you polish the contents. (Powered by Claude3)",
    submit_btn= gr.Button("▶️ Go"),
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

def save_to_state(input):
    '''save input content into tmp State'''
    state = input
    return state


with gr.Blocks() as tab_summary:
    description = gr.Markdown("Summarize articles or webpage for you.   (Powered by Claude3)")           
    with gr.Row():
        saved_text = gr.State()       
        with gr.Column(scale=6, min_width=450):
            with gr.Row():
                with gr.Tab("Original Text"):
                    input_text =  gr.Textbox(label='text', show_label=False, container=False, lines=8)
                    input_text.change(save_to_state, input_text, saved_text)
                with gr.Tab("Web URL"): 
                    input_url = gr.Textbox(label='url',show_label=False, container=False, lines=1)
                    input_url.change(save_to_state, input_url, saved_text)
                    # fetch webpage content for debug
                    # btn_fetch = gr.Button(value='⌨️ Fetch')
                    # fetched_text = gr.Textbox(label="Fetched text", lines=5)
                    # btn_fetch.click(web.fetch_web_text, input_url, fetched_text)
            with gr.Row():
                # btn_clear = gr.ClearButton([input_text, input_url, output], value='🗑️ Clear')
                btn_clear = gr.Button("🗑️ Clear") 
                btn_summit = gr.Button("▶️ Go")

        with gr.Column(scale=6, min_width=450):
            output = gr.Textbox(label="Summary text", lines=11)        
        
        btn_clear.click(None, None, [input_text, input_url, output])
        btn_summit.click(fn=lang.text_summary, inputs=saved_text, outputs=output)
