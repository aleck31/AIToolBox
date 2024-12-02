# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from utils import web
from . import STYLES, LANGS, text_proofread, text_rewrite, text_expand, text_reduce

TEXT_OPERATIONS = {
    "Proofreading ✍️": {
        "description": "Check spelling, grammar, and improve clarity",
        "function": text_proofread,
        "options": {}
    },
    "Rewrite 🔄": {
        "description": "Rewrite with different style and tone",
        "function": text_rewrite,
        "options": {
            "label": "Style",
            "type": "radio",
            "choices": list(STYLES.keys()),
            "default": "正常"
        }
    },
    "Reduction ✂️": {
        "description": "Simplify and remove redundant information",
        "function": text_reduce,
        "options": {}
    },
    "Expansion 📝": {
        "description": "Add details and background information",
        "function": text_expand,
        "options": {}
    }
}

def get_label_w_count(chars, base_label):
    """Get textbox label with character count"""
    count = len(chars) if chars else 0
    return f"{base_label} (Characters: {count})"

with gr.Blocks(theme=gr.themes.Soft()) as tab_text:
    # Description area
    operation_description = gr.Markdown(
        value=f"{TEXT_OPERATIONS['Proofreading ✍️']['description']}"
    )
    
    with gr.Column():
        with gr.Row():
            with gr.Column(scale=2):
                # Operation area
                input_operation = gr.Radio(
                    choices=list(TEXT_OPERATIONS.keys()),
                    label="Select Operation",
                    value="Proofreading ✍️",
                    scale=3
                )
            with gr.Column(scale=2):
                # Options area
                option_components = {}
                input_option = {}
                
                for op_name, op_info in TEXT_OPERATIONS.items():
                    with gr.Row(visible=(op_name == "Proofreading ✍️")) as options_row:
                        if op_info["options"]:
                            options = op_info["options"]
                            if options["type"] == "dropdown":
                                option_components[f"{op_name}_{options['label']}"] = gr.Dropdown(
                                    label=options["label"],
                                    choices=options["choices"],
                                    value=options["default"]
                                )
                            elif options["type"] == "radio":
                                option_components[f"{op_name}_{options['label']}"] = gr.Radio(
                                    label=options["label"],
                                    choices=options["choices"],
                                    value=options["default"]
                                )
                    input_option[op_name] = options_row

        with gr.Row():
            # Input column
            with gr.Column(scale=2):
                input_text = gr.Textbox(
                    label="Original Text",
                    lines=8,
                    placeholder="Enter your text here...",
                    show_copy_button=True
                )

                # Action buttons
                with gr.Row():
                    clear_btn = gr.Button("🗑️ Clear", size="lg")
                    submit_btn = gr.Button("▶️ Process", variant="primary", size="lg")

            # Output column
            with gr.Column(scale=2):
                output_text = gr.Textbox(
                    label="Processed Result",
                    lines=8,
                    show_copy_button=True
                )

                target_language = gr.Dropdown(
                    label="Target Language",
                    choices=LANGS,
                    value='en_US'
                )
        
        # Examples section
        gr.Examples(
            examples=[
                ["Proofreading ✍️", "the quick fox jumped over the lazy dogs back but it didnt land good", None, "en_US"],
                ["Rewrite 🔄", "Across the Great Wall we can reach every corner of the world.", "新闻", "zh_CN"],
                ["Reduction ✂️", "Artificial Intelligence, commonly abbreviated as AI, is a broad field of computer science that focuses on creating intelligent machines that can perform tasks that typically require human intelligence. These tasks include visual perception, speech recognition, decision-making, and language translation.", None, "en_US"],
                ["Expansion 📝", "AI改变世界。", None, "zh_CN"]
            ],
            inputs=[input_operation, input_text] + list(option_components.values()) + [target_language]
        )

    # Event handlers
    def update_interface(operation):
        outputs = []
        values = []
        for op_name in TEXT_OPERATIONS:
            values.append(gr.Column(visible=(op_name == operation)))
        description = f"{TEXT_OPERATIONS[operation]['description']}"
        values.insert(0, description)
        return values

    def process_text(*args):
        # Extract arguments
        operation = args[0]
        text = args[1]
        target_lang = args[-1]  # Last argument is always target_lang
        other_args = args[2:-1]  # Any additional arguments between text and target_lang
        
        if text.strip() == '':
            return "", gr.Textbox(label=get_label_w_count("", "Processed Result"))
        
        # Collect options for the current operation
        options = {"target_lang": target_lang}  # Add target language to all operations
        op_info = TEXT_OPERATIONS[operation]
        if op_info["options"]:
            opt = op_info["options"]
            # Find the corresponding argument from other_args that matches this option
            for arg in other_args:
                if arg is not None:  # Only use non-None arguments
                    options[opt['label'].lower()] = arg
                    break
        
        result = op_info["function"](text, options)
        return result, gr.Textbox(label=get_label_w_count(result, "Processed Result"))
    
    # Handle textbox cha event handlers
    # input_text.change(
    #     fn=lambda x: gr.Textbox(label=get_label_w_count(x, "Original Text")),
    #     inputs=[input_text],
    #     outputs=[input_text]
    # )
    
    output_text.change(
        fn=lambda x: gr.Textbox(label=get_label_w_count(x, "Processed Result")),
        inputs=[output_text],
        outputs=[output_text]
    )
    
    # Handle interface updates
    input_operation.change(
        fn=update_interface,
        inputs=[input_operation],
        outputs=[operation_description] + list(input_option.values())
    )
    
    # Handle submit button click
    submit_inputs = [input_operation, input_text] + list(option_components.values()) + [target_language]
    submit_btn.click(
        fn=process_text,
        inputs=submit_inputs,
        outputs=[output_text, output_text],
        api_name="text_process"
    )
    
    # Handle clear button click
    def clear_inputs():
        return (
            "",
            gr.Textbox(label=get_label_w_count("", "Original Text")),
            "",
            gr.Textbox(label=get_label_w_count("", "Processed Result"))
        )
    
    clear_btn.click(
        fn=clear_inputs,
        inputs=None,
        outputs=[input_text, input_text, output_text, output_text]
    )
