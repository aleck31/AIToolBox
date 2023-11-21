import gradio as gr
import random
import time
from llm import chat



with gr.Blocks() as tab_chat:
    description = gr.Markdown("Let's chat ...")
    with gr.Column(variant="panel"):
        # Chatbot接收 chat history进行显示
        chatbot = gr.Chatbot(label="Chatbot")
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
            btn_forget = gr.Button('🎲 Forget All', scale=1, min_width=200)
            btn_forget.click(chat.clear_memory, None, chatbot)
        with gr.Accordion(label='Chatbot Style', open=False):
            input_style = gr.Radio(label="Chatbot Style", choices=['AA','b','c'], value="AA", show_label=False)
        input_msg.submit(chat.text_chat, [input_msg, chatbot, input_style], [input_msg, chatbot])


tab_chat.load(chat.clear_memory, None, None)
tab_chat.launch()


# def respond(message, chat_history):
#     bot_message = random.choice(["How are you?", "I love you", "I'm very hungry"])
#     chat_history.append((message, bot_message))
#     time.sleep(2)
#     return "", chat_history

# gr.ChatInterface(
#     yes_man,
#     chatbot=gr.Chatbot(height=300),
#     textbox=gr.Textbox(placeholder="Ask me a yes or no question", container=False, scale=7),
#     title="Yes Man",
#     description="Ask Yes Man any question",
#     theme="soft",
#     examples=["Hello", "Am I cool?", "Are tomatoes vegetables?"],
#     cache_examples=True,
#     retry_btn="Retry",
#     undo_btn="Delete Previous",
#     clear_btn="Clear",
# ).launch()

# define the input component
# input_textbox = gr.Textbox()

# with gr.Blocks() as demo:
#     error_box = gr.Textbox(label="Error", visible=False)

#     # define the gr.Examples object
#     gr.Examples(["hello", "bonjour", "merhaba"], input_textbox)
#     # render input component
#     input_textbox.render()

#     name_box = gr.Textbox(label="Name")
#     age_box = gr.Number(label="Age")
#     symptoms_box = gr.CheckboxGroup(["Cough", "Fever", "Runny Nose"])
#     submit_btn = gr.Button("Submit")

#     with gr.Column(visible=False) as output_col:
#         diagnosis_box = gr.Textbox(label="Diagnosis")
#         patient_summary_box = gr.Textbox(label="Patient Summary")

#     def submit(name, age, symptoms):
#         if len(name) == 0:
#             return {error_box: gr.update(value="Enter name", visible=True)}
#         if age < 0 or age > 200:
#             return {error_box: gr.update(value="Enter valid age", visible=True)}
#         return {
#             output_col: gr.update(visible=True),
#             diagnosis_box: "covid" if "Cough" in symptoms else "flu",
#             patient_summary_box: f"{name}, {age} y/o"
#         }

#     submit_btn.click(
#         submit,
#         [name_box, age_box, symptoms_box],
#         [error_box, diagnosis_box, patient_summary_box, output_col],
#     )

# demo.launch()