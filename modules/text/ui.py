# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from typing import List, Any, Tuple
from core.logger import logger
from .handlers import TEXT_OPERATIONS, LANGS, TextHandlers


def create_interface() -> gr.Blocks:
    """Create text processing interface with handlers"""
    def update_interface(operation: str) -> List[Any]:
        """Update interface based on selected operation"""
        values = []
        for op_name in TEXT_OPERATIONS:
            values.append(gr.Column(visible=(op_name == operation)))
        description = f"{TEXT_OPERATIONS[operation]['description']}"
        values.insert(0, description)
        return values

    # Create interface
    interface = gr.Blocks(theme=gr.themes.Soft())
    
    with interface:
        # Description area
        operation_description = gr.Markdown(
            value=f"{TEXT_OPERATIONS['Proofreading ✍️']['description']}"
        )

        # Define output components first to avoid reference errors
        output_text = gr.Textbox(
            label="Processed Result",
            lines=8,
            show_copy_button=True,
            render=False
        )

        # Main layout row
        with gr.Row():
            with gr.Column(scale=2):
                # Operation area
                input_operation = gr.Radio(
                    choices=list(TEXT_OPERATIONS.keys()),
                    label="Select Operation",
                    value="Proofreading ✍️"
                )

            with gr.Column(scale=2):
                with gr.Row():
                    # Target language selection
                    target_language = gr.Dropdown(
                        label="Target Language",
                        show_label=False,
                        info='Select target language',
                        choices=LANGS,
                        value='en_US'
                    )

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
                                        show_label=False,
                                        info='Choose writing style',
                                        choices=options["choices"],
                                        value=options["default"]
                                    )
                                elif options["type"] == "radio":
                                    option_components[f"{op_name}_{options['label']}"] = gr.Radio(
                                        label=options["label"],
                                        show_label=False,
                                        info='Choose writing style',
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
                    btn_clear = gr.ClearButton(
                        value="🗑️ Clear",
                        components=[input_text, output_text]
                    )
                    btn_submit = gr.Button("▶️ Process", variant="primary")

            # Output column
            with gr.Column(scale=2):
                output_text.render()

        # Examples section
        gr.Examples(
            examples=[
                ["Proofreading ✍️", "the quickly fox jumped over the lazy dogs back but it didnt land good", "en_US", None],
                ["Rewrite 🔄", "Across the Great Wall we can reach every corner of the world.", "zh_CN", "新闻"],
                ["Reduction ✂️", "Artificial Intelligence, commonly abbreviated as AI, is a broad field of computer science that focuses on creating intelligent machines that can perform tasks that typically require human intelligence. These tasks include visual perception, speech recognition, decision-making, and language translation.", "en_US", None],
                ["Expansion 📝", "AI改变世界。", "zh_CN", None]
            ],
            inputs=[input_operation, input_text, target_language] + list(option_components.values())
        )
        
        # Handle interface updates
        input_operation.change(
            fn=update_interface,
            inputs=[input_operation],
            outputs=[operation_description] + list(input_option.values())
        )
        
        # Handle submit button click - Note: Gradio automatically handles the request parameter
        submit_inputs = [input_operation, input_text, target_language] + list(option_components.values())
        btn_submit.click(
            fn=TextHandlers.process_text,
            inputs=submit_inputs,
            outputs=output_text,
            api_name="text_process"
        )

    return interface

# Create interface
tab_text = create_interface()
