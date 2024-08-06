# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from common import AppConf
from llm import claude3, gemini


def post_text(message, history):
    '''post message on chatbox ui before get LLM response'''
    # history = history + [(message, None)]
    history.append([message, None])
    return gr.Textbox(value="", interactive=False), message, history


def post_media(file, history):
    '''post media on chatbox ui before get LLM response'''
    history.append([(file.name,), None])
    return history


tab_claude = gr.ChatInterface(
    claude3.multimodal_chat,
    multimodal=True,
    description="Let's chat ... (Powered by Bedrock)",
    chatbot=gr.Chatbot(
        avatar_images=(None, "assets/avata_claude.jpg"),
        label="Chatbot",
        layout="bubble",
        bubble_full_width=False,
        height=420
    ),
    textbox=gr.MultimodalTextbox(
        file_types=['image'],
        placeholder="Type a message or upload image(s)",
        scale=13,
        min_width=60
    ),
    # undo_btn="↩️ Undo",
    undo_btn=None,
    # retry_btn='🔃 Retry',
    retry_btn=None,
    # clear_btn="💊 Forget All",
    clear_btn=None,
    stop_btn='🟥',
    additional_inputs_accordion=gr.Accordion(
        label='Chatbot Style', open=False),
    additional_inputs=gr.Radio(
        label="style", choices=AppConf.STYLES,
        value="正常", show_label=False
    )
)


tab_gemini = gr.ChatInterface(
    gemini.multimodal_chat,
    multimodal=True,
    description="Let's chat ... (Powered by Gemini Pro)",
    chatbot=gr.Chatbot(
        avatar_images=(None, "assets/avata_google.jpg"),
        label="Chatbot",
        layout="bubble",
        bubble_full_width=False,
        height=420
    ),
    textbox=gr.MultimodalTextbox(
        file_types=['image', "video", "audio"],
        file_count='multiple',
        placeholder="Type a message or upload image(s)",
        scale=13,
        min_width=60
    ),
    # undo_btn="↩️ Undo",
    undo_btn=None,
    # retry_btn='🔃 Retry',
    retry_btn=None,
    # clear_btn="💊 Forget All",
    clear_btn=None,
    stop_btn='🟥'
)

# with gr.Blocks() as tab_gemini:
#     description = gr.Markdown("Let's chat ... (Powered by Gemini Pro)")
#     with gr.Column(variant="panel"):
#         chatbox = gr.Chatbot(
#             avatar_images=(None, "assets/avata_google.jpg"),
#             # elem_id="chatbot",
#             bubble_full_width=False,
#             height=420
#         )
#         with gr.Group():
#             with gr.Row():
#                 input_msg = gr.Textbox(
#                     show_label=False, container=False, scale=12,
#                     placeholder="Enter text or upload an image"
#                 )
#                 btn_file = gr.UploadButton(
#                     "📁", file_types=["image", "video", "audio"], scale=1)
#                 btn_submit = gr.Button(
#                     'Chat', variant="primary", scale=2, min_width=150)

#         with gr.Row():
#             btn_clear = gr.ClearButton(
#                 [input_msg, chatbox], value='🗑️ Clear', scale=1)
#             btn_forget = gr.Button('💊 Forget All', scale=1, min_width=150)
#             btn_forget.click(gemini.clear_memory, None, chatbox)
#             btn_flag = gr.Button('🏁 Flag', scale=1, min_width=150)

#         # temp save user message in State()
#         saved_msg = gr.State()
#         btn_file.upload(
#             post_media, [btn_file, chatbox], [chatbox], queue=False
#         ).then(
#             gemini.media_chat, [btn_file, chatbox], chatbox
#         )

#         txt_msg = input_msg.submit(
#             post_text, [input_msg, chatbox], [
#                 input_msg, saved_msg, chatbox], queue=False
#         ).then(
#             gemini.text_chat, [saved_msg, chatbox], chatbox
#         )
#         # restore interactive for input textbox
#         txt_msg.then(lambda: gr.Textbox(interactive=True), None, [input_msg])

#         btn_submit.click(
#             post_text, [input_msg, chatbox], [
#                 input_msg, saved_msg, chatbox], queue=False
#         ).then(
#             gemini.text_chat, [saved_msg, chatbox], [chatbox]
#         ).then(lambda: gr.Textbox(interactive=True), None, [input_msg])
