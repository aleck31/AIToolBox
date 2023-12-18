# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from llm import chat, text, code, image
from utils import common



LANGS = ["en_US", "zh_CN", "zh_TW", "ja_JP", "de_DE", "fr_FR"]
STYLES = ["正常", "幽默", "极简", "理性", "可爱"]
PICSTYLES = [
    "增强(enhance)", "照片(photographic)", "老照片(analog-film)",
    "电影(cinematic)", "模拟电影(analog-film)", "美式漫画(comic-book)",  "动漫(anime)", "线稿(line-art)",
    "3D模型(3d-model)", "低多边形(low-poly)", "霓虹朋克(neon-punk)", "复合建模(modeling-compound)",
    "数字艺术(digital-art)", "奇幻艺术(fantasy-art)", "像素艺术(pixel-art)", "折纸艺术(origami)"
]
CODELANGS = ["Python", "Shell", "HTML", "Javascript", "Typescript", "Yaml", "GoLang", "Rust"]
Login_USER = ''


def login(username, password):
    global Login_USER
    if common.verify_user(username, password):
        # If a new user logs in, clear the history by default
        if username != Login_USER:
            chat.clear_memory()
        Login_USER = username 
        return True
    else:
        return False


with gr.Blocks() as tab_chat:
    description = gr.Markdown("Let's chat ... (Powered by Claude v2.1)")
    with gr.Column(variant="panel"):
        # Chatbot接收 chat history进行显示
        chatbot = gr.Chatbot(
            # avatar_images='',
            label="Chatbot",
            layout="bubble",
            height=420
        )
        with gr.Group():
            with gr.Row():
                input_msg = gr.Textbox(
                    show_label=False, container=False, autofocus=True, scale=7,
                    placeholder="Type a message..."
                )
                btn_submit = gr.Button('Chat', variant="primary", scale=1, min_width=150)                
        with gr.Row():            
            btn_clear = gr.ClearButton([input_msg, chatbot], value='🗑️ Clear')
            btn_forget = gr.Button('💊 Forget All', scale=1, min_width=200)
            btn_forget.click(chat.clear_memory, None, chatbot)
            btn_flag = gr.Button('🏁 Flag', scale=1, min_width=150)
        with gr.Accordion(label='Chatbot Style', open=False):
            input_style = gr.Radio(label="Chatbot Style", choices=STYLES, value="正常", show_label=False)
        input_msg.submit(chat.text_chat, [input_msg, chatbot, input_style], [input_msg, chatbot])
        btn_submit.click(chat.text_chat, [input_msg, chatbot, input_style], [input_msg, chatbot])

with gr.Blocks() as tab_chatm:
    description = gr.Markdown("Let's chat ... (Powered by Gemini Por)")


tab_translate = gr.Interface(
    text.text_translate,
    inputs=[
        gr.Textbox(label="Original", lines=7, scale=5),
        gr.Dropdown(label="Target Language", choices=LANGS, value='en_US', scale=1)
    ],
    outputs=gr.Textbox(label="Translated", lines=11, scale=5),
    examples=[["Across the Great Wall we can reach every corner of the world.", "zh_CN"]],
    cache_examples=False,
    description="Let me translate the text for you. (Powered by Claude v2)"
)

tab_rewrite = gr.Interface(
    text.text_rewrite,
    inputs=[
        gr.Textbox(label="Original", lines=7, scale=5),
        # gr.Accordion(),
        gr.Radio(label="Style", choices=STYLES, value="正常", scale=1)
    ],
    outputs=gr.Textbox(label="Polished", lines=11, scale=5),
    examples=[["人工智能将对人类文明的发展产生深远影响。", "幽默"]],
    cache_examples=False,
    # live=True,
    description="Let me help you polish the contents. (Powered by Claude v2)"
)

tab_summary = gr.Interface(
    text.text_summary,
    inputs=[
        gr.Textbox(label="Original", lines=12, scale=5),
    ],
    outputs=gr.Textbox(label="Translated", lines=6, scale=5),
    description="Let me summary the contents for you. (Powered by Claude v2)"
)

with gr.Blocks() as tab_code:
    description = gr.Markdown("Let's build ... (Powered by Claude v2.1)")
    with gr.Row():
        # 输入需求
        with gr.Column(scale=6, min_width=500):
            input_requirement =  gr.Textbox(label="Describe your requirements:", lines=4)         
        with gr.Column(scale=2, min_width=100):
            input_lang = gr.Radio(label="Programming Language", choices=CODELANGS, value="Python")
    with gr.Row():
        # 输出代码结果
        with gr.Column(scale=6, min_width=500):
            support_langs = ["python","markdown","json","html","javascript","typescript","yaml"]
            lang_format = input_lang.value.lower() if input_lang.value.lower() in support_langs else None
            output_codes = gr.Code(label="Code", language=lang_format, lines=9)
        with gr.Column(scale=2, min_width=100):
            btn_code_submit = gr.Button(value='⌨️ Generate')
            btn_code_submit.click(fn=code.gen_code, inputs=[input_requirement, input_lang], outputs=output_codes)
            btn_code_clear = gr.ClearButton([input_requirement, output_codes], value='🗑️ Clear')
    with gr.Row():
        error_box = gr.Textbox(label="Error", visible=False)


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
                    input_style = gr.Dropdown(choices=PICSTYLES, value='增强(enhance)', label='Picture style:')
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


with gr.Blocks() as tab_setting:
    description = gr.Markdown("Toolbox Settings")
    with gr.Row():
        with gr.Column(scale=5):
            # tobeFix: cannot get the value of global variable
            gr.Textbox(Login_USER, label="Login User", max_lines=1)
        with gr.Column(scale=2):
            pass
        with gr.Column(scale=2):
            btn_logout = gr.Button('Logout ↪️', scale=1, min_width=150)


app = gr.TabbedInterface(
    [tab_chat, tab_translate, tab_rewrite, tab_summary, tab_draw, tab_code, tab_setting], 
    tab_names= ["Chat 🤖", "Translate 🇺🇳", "ReWrite ✍🏼", "Summary 📰", "Draw 🎨", "Code 💻", "Setting ⚙️"],
    # [tab_chat, tab_chatm, tab_translate, tab_rewrite, tab_summary, tab_draw, tab_code, tab_setting], 
    # tab_names= ["Chat (Claude v2.1)", "Chat (Gemini-Pro)", "Translate (Claude v2)", "ReWrite (Claude v2)", "Summary (Claude v2)", "Draw (SDXL v1)", "Code (Claude v2)", "Setting ⚙️"],
    title="AI ToolBox ",
    theme="Base",
    css="footer {visibility: hidden}"
    )


if __name__ == "__main__":
    app.queue()
    app.launch(
        # share=True,
        # debug=True,
        auth=login,
        server_name='0.0.0.0',
        server_port=8888,
        show_api=False
    )
