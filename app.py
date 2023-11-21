# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
import random
from llm import chat, text, code, image
from utils import auth



LANGS = ["en_US", "zh_CN", "zh_TW", "ja_JP", "de_DE", "fr_FR"]
STYLES = ["正常", "幽默", "极简", "理性", "可爱"]
PICSTYLES = [
    "照片(photographic)", "动漫(anime)", "美式漫画(comic-book)", 
    "数字艺术(digital-art)", "老照片(analog-film)", "电影(cinematic)", 
    "线稿(line-art)", "3D模型(3d-model)", "黏土(craft-clay)"
    ]
CODELANGS = ["Python", "Shell", "HTML", "Javascript", "Typescript", "Yaml", "GoLang", "Rust"]


def random_seed():
    return random.randrange(10000000, 99999999)

def login(username, password):
    user_dict = auth.get_userdict()
    if username == user_dict.get('username') and password == user_dict.get('password'):
        # global LoginUser = username
        # clear memory of last session
        chat.clear_memory()
        return True

with gr.Blocks() as tab_chat:
    description = gr.Markdown("Let's chat ...")
    with gr.Column(variant="panel"):
        # Chatbot接收 chat history进行显示
        chatbot = gr.Chatbot(
            # avatar_images='',
            label="Chatbot",
            layout="bubble",
            height=360
        )
        with gr.Group():
            with gr.Row():
                input_msg = gr.Textbox(
                    show_label=False, container=False, autofocus=True, scale=7,
                    placeholder="Type a message..."            
                )
                btn_submit = gr.Button('Chat', variant="primary", scale=1, min_width=150)                
        with gr.Row():
            btn_undo = gr.Button('↩️ Undo', scale=1, min_width=150)
            btn_clear = gr.ClearButton([input_msg, chatbot], value='🗑️  Clear')
            btn_forget = gr.Button('💊 Forget All', scale=1, min_width=200)
            btn_forget.click(chat.clear_memory, None, chatbot)
        with gr.Accordion(label='Chatbot Style', open=False):
            input_style = gr.Radio(label="Chatbot Style", choices=STYLES, value="正常", show_label=False)
        input_msg.submit(chat.text_chat, [input_msg, chatbot, input_style], [input_msg, chatbot])
        btn_submit.click(chat.text_chat, [input_msg, chatbot, input_style], [input_msg, chatbot])

tab_translate = gr.Interface(
    text.text_translate,
    inputs=[
        gr.Textbox(label="Original", lines=6, scale=5),
        gr.Dropdown(label="Target Language", choices=LANGS, value='en_US', scale=1)
    ],
    outputs=gr.Textbox(label="Translated", lines=11, scale=5),
    examples=[["Across the Great Wall we can reach every corner of the world.", "zh_CN"]],
    cache_examples=False,
    description="Let me translate the text for you."
)

tab_rewrite = gr.Interface(
    text.text_rewrite,
    inputs=[
        gr.Textbox(label="Original", lines=6, scale=5),
        # gr.Accordion(),
        gr.Radio(label="Style", choices=STYLES, value="正常", scale=1)
    ],
    outputs=gr.Textbox(label="Polished", lines=11, scale=5),
    examples=[["人工智能将对人类文明的发展产生深远影响。", "幽默"]],
    cache_examples=False,
    # live=True,
    description="Let me help you polish the paragraph."
)

tab_summary = gr.Interface(
    text.text_summary,
    inputs=[
        gr.Textbox(label="Original", lines=12, scale=5),
    ],
    outputs=gr.Textbox(label="Translated", lines=6, scale=5),
    description="Let me summary the text for you."
)

with gr.Blocks() as tab_code:
    with gr.Row():
        # 输入需求
        with gr.Column(scale=6, min_width=500):
            input_requirement =  gr.Textbox(label="Requirement Description:", lines=4)         
        with gr.Column(scale=2, min_width=100):
            input_lang = gr.Radio(label="Programming Language", choices=CODELANGS, value="Python")
    with gr.Row():
        # 输出代码结果
        with gr.Column(scale=6, min_width=500):
            support_langs = ["python","markdown","json","html","javascript","typescript","yaml"]
            lang_format = input_lang.value.lower() if input_lang.value.lower() in support_langs else None
            output_codes = gr.Code(label="Code", language=lang_format, lines=9)
        with gr.Column(scale=2, min_width=100):
            btn_code_submit = gr.Button()
            btn_code_submit.click(fn=code.gen_code, inputs=[input_requirement, input_lang], outputs=output_codes)
            btn_code_clear = gr.ClearButton([input_requirement, output_codes])
    with gr.Row():
        error_box = gr.Textbox(label="Error", visible=False)


with gr.Blocks() as tab_draw:
    description = gr.Markdown("Draw anything according to your words.")
    with gr.Tab("Text-Image"):
        with gr.Row():
            with gr.Column(scale=6):
                # input_params = []
                input_prompt = gr.Textbox(label="Prompt", lines=5)
                # optional parameters
                input_negative = gr.Text(label="Negative Prompt")
                input_style = gr.Dropdown(choices=PICSTYLES, label='Picture style:')
                input_step = gr.Slider(10, 150, value=50, step=1, label="Step")
                # gr.Slider(0, 30, value=10, step=1, label="Strength")
                with gr.Row():
                    # with gr.Column(scale=5):
                    # seed randrange(10000000, 99999999)
                    input_seed = gr.Number(value=-1, label="Seed", scale=5)
                    # with gr.Column(scale=1):
                    btn_random = gr.Button('🎲 Random', scale=1)
                    btn_random.click(random_seed, None, input_seed)
                with gr.Row():
                    with gr.Column(scale=1):
                        btn_text_img = gr.Button("Generate")          
                    with gr.Column(scale=1):
                        btn_text_clean = gr.ClearButton([input_prompt, input_negative])                
            with gr.Column(scale=6):
                output_image = gr.Image(interactive=False, height=480)            
            btn_text_img.click(
                fn=image.text_image, 
                inputs=[input_prompt, input_negative, input_style, input_step, input_seed], 
                outputs=output_image
            )

    with gr.Tab("Image-Image"):
        gr.Markdown('TBD')


app = gr.TabbedInterface(
    [tab_chat, tab_translate, tab_rewrite, tab_summary, tab_draw, tab_code], 
    tab_names= ["Chat (Claude v2)", "Translate (Claude v2)", "ReWrite (Claude v2)", "Summary (Claude v2)", "Draw (SDXL v0.8)", "Code (Claude v2)"],
    title="AI ToolBox (powered by Bedrock)",
    theme="Base",
    css="footer {visibility: hidden}"
    )


if __name__ == "__main__":
    app.queue()
    app.launch(
        # share=True,
        debug=True,
        auth=login,
        # ssl_certfile="cert.pem",
        # ssl_keyfile="key.pem"
        server_name='0.0.0.0',
        server_port=8888
    )
