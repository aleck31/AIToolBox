# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from typing import List, Any, Tuple
from core.logger import logger
from .handlers import TEXT_OPERATIONS, LANGS, TextHandlers

# moved TEXT_OPERATIONS to handlers.py

def create_text_interface() -> gr.Blocks:
    """Initialize service and create text processing interface with handlers"""
    # Initialize service
    TextHandlers.initialize()
    
    def update_interface(operation: str) -> List[Any]:
        """Update interface based on selected operation"""
        values = []
        for op_name in TEXT_OPERATIONS:
            values.append(gr.Column(visible=(op_name == operation)))
        description = f"{TEXT_OPERATIONS[operation]['description']}"
        values.insert(0, description)
        return values

    def clear_inputs() -> Tuple[str, str, str]:
        """Clear all input and output fields"""
        return (
            "",
            "",
            "",
        )

    # Create interface
    interface = gr.Blocks(theme=gr.themes.Soft())
    
    with interface:
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
        
        # Handle interface updates
        input_operation.change(
            fn=update_interface,
            inputs=[input_operation],
            outputs=[operation_description] + list(input_option.values())
        )
        
        # Handle submit button click - Note: Gradio automatically handles the request parameter
        submit_inputs = [input_operation, input_text] + list(option_components.values()) + [target_language]
        submit_btn.click(
            fn=TextHandlers.process_text,
            inputs=submit_inputs,
            outputs=output_text,
            api_name="text_process"
        )
        
        # Handle clear button click
        clear_btn.click(
            fn=clear_inputs,
            inputs=None,
            outputs=[input_text, input_text, output_text]
        )

    return interface

# Create interface
tab_text = create_text_interface()
