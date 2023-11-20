import gradio as gr


def yes_man(message, history):
    if message.endswith("?"):
        return "Yes"
    else:
        return "Ask me anything!"

gr.ChatInterface(
    yes_man,
    chatbot=gr.Chatbot(height=300),
    textbox=gr.Textbox(placeholder="Ask me a yes or no question", container=False, scale=7),
    title="Yes Man",
    description="Ask Yes Man any question",
    theme="soft",
    examples=["Hello", "Am I cool?", "Are tomatoes vegetables?"],
    cache_examples=True,
    retry_btn="Retry",
    undo_btn="Delete Previous",
    clear_btn="Clear",
).launch()

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