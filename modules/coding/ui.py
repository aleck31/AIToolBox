# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from .handlers import CodingHandlers, DEV_LANGS


def create_coding_interface() -> gr.Blocks:
    """Create coding interface with handlers"""
    # Create interface without eager initialization
    interface = gr.Blocks(theme=gr.themes.Soft())
    
    with interface:
        gr.Markdown("Code Generation")
        
        # Main layout row
        with gr.Row():
            # Left column: Input and output
            with gr.Column(scale=7, min_width=500):
                # Requirements input
                input_requirement = gr.Textbox(
                    label="Describe your requirements:",
                    placeholder="What would you like me to help you code?",
                    lines=5,
                    show_copy_button=True
                )
                
                # Architecture Design output
                with gr.Accordion(label="Architecture Design"):
                    arch_thinking = gr.Markdown(
                        label='Design',
                        show_label=False,
                        line_breaks=True,
                        header_links=True,
                        value=""
                    )
                
                # Generated code output
                with gr.Accordion(label="Generated Code"):
                    output_code = gr.Markdown(
                        label='Code',
                        show_label=False,
                        line_breaks=True,
                        min_height=120,
                        show_copy_button=True,
                        header_links=True
                    )
            
            # Right column: Settings and controls
            with gr.Column(scale=3, min_width=120):
                # Language selection
                input_lang = gr.Radio(
                    label="Programming Language",
                    choices=DEV_LANGS,
                    value="Python"
                )
                with gr.Row():
                    btn_clear = gr.ClearButton(
                        value="🗑️ Clear",
                        components=[input_requirement, arch_thinking, output_code]
                    )
                    btn_code_submit = gr.Button(
                        value="⌨️ Generate",
                        variant="primary"
                    )

        # Event handler functions
        def update_btn_phase(phase: str):
            """Update button label for current phase"""
            labels = {
                "arch": "🤔 Designing",
                "code": "⌨️ Coding"
            }
            return labels.get(phase, "⌨️ Generate")

        # Event bindings for two-phase generation
        btn_code_submit.click(
            fn=lambda: update_btn_phase("arch"),
            outputs=btn_code_submit
        ).then(
            fn=CodingHandlers.design_arch,
            inputs=[input_requirement, input_lang],
            outputs=arch_thinking,
            api_name="design_arch"
        ).then(
            fn=lambda: update_btn_phase("code"),
            outputs=btn_code_submit
        ).then(
            fn=CodingHandlers.gen_code,
            inputs=[arch_thinking, input_lang],
            outputs=output_code,
            api_name="gen_code"
        ).then(
            fn=lambda: update_btn_phase("done"),
            outputs=btn_code_submit
        )
        
    return interface

# Create interface
tab_coding = create_coding_interface()
