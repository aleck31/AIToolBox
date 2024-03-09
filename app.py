# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from llm import claude3, text, code, image, gemini
from utils import common, AppConf



def login(username, password):
    # tobeFix: cannot set the value to login_user
    AppConf.login_user = username 
    if common.verify_user(username, password):
        # If a new user logs in, clear the history by default
        if username != AppConf.login_user:
            claude3.clear_memory()        
        return True
    else:
        return False

def post_text(message, history):
    '''post message on chatbox ui before get LLM response'''
    # history = history + [(message, None)]
    history.append([message, None])
    return gr.Textbox(value="", interactive=False), message, history

def post_media(file, history):
    '''post media on chatbox ui before get LLM response'''
    history.append([(file.name,), None])
    return history
    

with gr.Blocks() as tab_claude:
    description = gr.Markdown("Let's chat ... (Powered by Claude3 Sonnet v1)")
    with gr.Column(variant="panel"):
        # Chatbot接收 chat history进行显示
        chatbox = gr.Chatbot(
            avatar_images=(None, "assets/avata_claude.jpg"),
            label="Chatbot",
            layout="bubble",
            bubble_full_width=False,
            height=420
        )
        with gr.Group():
            with gr.Row():
                input_msg = gr.Textbox(
                    show_label=False, container=False, autofocus=True, scale=7,
                    placeholder="Type a message or upload an image"
                )
                btn_file = gr.UploadButton("📁", file_types=["image"], scale=1)
                btn_submit = gr.Button('Chat', variant="primary", scale=1, min_width=150)          
        with gr.Row():
            btn_clear = gr.ClearButton([input_msg, chatbox], value='🗑️ Clear')
            btn_forget = gr.Button('💊 Forget All', scale=1, min_width=150)
            btn_forget.click(claude3.clear_memory, None, chatbox)
            btn_flag = gr.Button('🏁 Flag', scale=1, min_width=150)
        with gr.Accordion(label='Chatbot Style', open=False):
            input_style = gr.Radio(label="Chatbot Style", choices=AppConf.STYLES, value="正常", show_label=False)
        
        # temp save user message in State()
        saved_msg = gr.State()
        # saved_chats = (
        #     gr.State(chatbot.value) if chatbot.value else gr.State([])
        # )
        media_msg = btn_file.upload(
            post_media, [btn_file, chatbox], [chatbox], queue=False
        ).then(
            claude3.media_chat, [btn_file, chatbox], chatbox
        )

        input_msg.submit(
            post_text, [input_msg, chatbox], [input_msg, saved_msg, chatbox], queue=False
        ).then(
            claude3.text_chat, [saved_msg, chatbox, input_style], chatbox
        ).then(
            # restore interactive for input textbox
            lambda: gr.Textbox(interactive=True), None, input_msg
        )

        btn_submit.click(
            post_text, [input_msg, chatbox], [input_msg, saved_msg, chatbox], queue=False
        ).then(
            claude3.text_chat, [saved_msg, chatbox, input_style], [chatbox]
        ).then(lambda: gr.Textbox(interactive=True), None, input_msg)


with gr.Blocks() as tab_gemini:
    description = gr.Markdown("Let's chat ... (Powered by Gemini Pro)")    
    with gr.Column(variant="panel"):
        chatbox = gr.Chatbot(
            avatar_images=(None, "assets/avata_google.jpg"),
            # elem_id="chatbot",
            bubble_full_width=False,
            height=420
        )
        with gr.Group():
            with gr.Row():
                input_msg = gr.Textbox(
                    show_label=False, container=False, scale=12,
                    placeholder="Enter text or upload an image"
                )
                btn_file = gr.UploadButton("📁", file_types=["image", "video", "audio"], scale=1)
                btn_submit = gr.Button('Chat', variant="primary", scale=2, min_width=150)

        with gr.Row():
            btn_clear = gr.ClearButton([input_msg, chatbox], value='🗑️ Clear', scale=1)
            btn_forget = gr.Button('💊 Forget All', scale=1, min_width=150)
            btn_forget.click(gemini.clear_memory, None, chatbox)
            btn_flag = gr.Button('🏁 Flag', scale=1, min_width=150)

        # temp save user message in State()
        saved_msg = gr.State()
        media_msg = btn_file.upload(
            post_media, [btn_file, chatbox], [chatbox], queue=False
        ).then(
            gemini.media_chat, [btn_file, chatbox], chatbox
        )

        txt_msg = input_msg.submit(
            post_text, [input_msg, chatbox], [input_msg, saved_msg, chatbox], queue=False
        ).then(
            gemini.text_chat, [saved_msg, chatbox], chatbox
        )
        # restore interactive for input textbox
        txt_msg.then(lambda: gr.Textbox(interactive=True), None, [input_msg])

        btn_submit.click(
            post_text, [input_msg, chatbox], [input_msg, saved_msg, chatbox], queue=False
        ).then(
            gemini.text_chat, [saved_msg, chatbox], [chatbox]
        ).then(lambda: gr.Textbox(interactive=True), None, [input_msg])


tab_translate = gr.Interface(
    text.text_translate,
    inputs=[
        gr.Textbox(label="Original", lines=7),
        gr.Dropdown(label="Source Language", choices=['auto'], value='auto', container=False),
        gr.Dropdown(label="Target Language", choices=AppConf.LANGS, value='en_US')
    ],
    outputs=gr.Textbox(label="Translated", lines=11, scale=5),
    examples=[["Across the Great Wall we can reach every corner of the world.", "auto", "zh_CN"]],
    cache_examples=False,
    description="Let me translate the text for you. (Powered by Claude3 Sonnet v1)"
)


tab_rewrite = gr.Interface(
    text.text_rewrite,
    inputs=[
        gr.Textbox(label="Original", lines=7, scale=5),
        # gr.Accordion(),
        gr.Radio(label="Style", choices=AppConf.STYLES, value="正常", scale=1)
    ],
    outputs=gr.Textbox(label="Polished", lines=11, scale=5),
    examples=[["人工智能将对人类文明的发展产生深远影响。", "幽默"]],
    cache_examples=False,
    # live=True,
    description="Let me help you polish the contents. (Powered by Claude3 Sonnet v1)"
)


tab_summary = gr.Interface(
    text.text_summary,
    inputs=[
        gr.Textbox(label="Original", lines=12, scale=5),
    ],
    outputs=gr.Textbox(label="Summary text", lines=6, scale=5),
    description="Let me summary the contents for you. (Powered by Claude3 Sonnet v1)"
)


with gr.Blocks() as tab_code:
    description = gr.Markdown("Let's build ... (Powered by Claude3 Sonnet v1)")
    with gr.Row():
        # 输入需求
        with gr.Column(scale=6, min_width=500):
            input_requirement =  gr.Textbox(label="Describe your requirements:", lines=4)         
        with gr.Column(scale=2, min_width=100):
            input_lang = gr.Radio(label="Programming Language", choices=AppConf.CODELANGS, value="Python")
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


with gr.Blocks() as tab_format:
    description = gr.Markdown("A JSON Formatter... (Powered by Claude3 Sonnet v1)")
    with gr.Row():
        # 输入需求
        with gr.Column(scale=6, min_width=500):
            input_text =  gr.Textbox(label="Please input the text to be formatted.", lines=4)         
        with gr.Column(scale=2, min_width=100):
            input_format = gr.Radio(label="File format", choices=["JSON"], value="JSON")
    with gr.Row():
        # 输出代码结果
        with gr.Column(scale=6, min_width=500):
            support_formats = ["json","yaml","xml","csv"]
            target_format = input_format.value.lower() if input_format.value.lower() in support_formats else None
            output_codes = gr.Code(label="Code", language=target_format, lines=9)
        with gr.Column(scale=2, min_width=100):
            btn_code_submit = gr.Button(value='⌨️ Format')
            btn_code_submit.click(fn=code.format_code, inputs=[input_text, input_format], outputs=output_codes)
            btn_code_clear = gr.ClearButton([input_text, output_codes], value='🗑️ Clear')
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
                    input_style = gr.Dropdown(choices=AppConf.PICSTYLES, value='增强(enhance)', label='Picture style:')
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


def update_setting(model_id):
    AppConf.model_id = model_id
    gr.Info("App settings updated.")


with gr.Blocks() as tab_setting:
    description = gr.Markdown("Toolbox Settings")
    with gr.Row():
        with gr.Column(scale=15):            
            input_model = gr.Textbox(AppConf.model_id, label="Language Model", max_lines=1)
            image_model = gr.Textbox(AppConf.image_llm, label="Image Model", max_lines=1, interactive=False)
        with gr.Column(scale=1):
            gr.Textbox(AppConf.login_user, label='User', max_lines=1, interactive=False)
    with gr.Row():
        with gr.Column(scale=1):   
            btn_submit = gr.Button(value='✅ Update', min_width=120)
            btn_submit.click(update_setting, input_model, None)
        with gr.Column(scale=15):
            pass


app = gr.TabbedInterface(
    [tab_claude, tab_gemini, tab_translate, tab_rewrite, tab_summary, tab_code, tab_format, tab_draw, tab_setting], 
    tab_names= ["Claude 🤖", "Gemini 👾", "Translate 🇺🇳", "ReWrite ✍🏼", "Summary 📰", "Code 💻", "JSON 🔣", "Draw 🎨", "Setting ⚙️"],
    title="AI ToolBox",
    theme="Base",
    css="footer {visibility: hidden}"
    )


if __name__ == "__main__":
    app.queue().launch(
        # share=True,
        # debug=True,
        auth=login,
        server_name='0.0.0.0',
        server_port=8886,
        show_api=False
    )
