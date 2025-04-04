# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from .handlers import CodingHandlers, DEV_LANGS


def create_interface() -> gr.Blocks:
    """Create coding interface with handlers"""
    # Create interface without eager initialization
    interface = gr.Blocks(theme=gr.themes.Soft())
    
    with interface:
        gr.Markdown("Code Generation")

        # Define output components first to avoid reference errors
        arch_thinking = gr.Markdown(
            label='Design',
            show_label=False,
            value="",
            line_breaks=True,
            header_links=True,
            render=False
        )
        
        output_code = gr.Markdown(
            label='Code',
            show_label=False,
            line_breaks=True,
            min_height=300,
            show_copy_button=True,
            header_links=True,
            render=False
        )

        # Main layout row
        with gr.Row():
            # Left column: Input and Options
            with gr.Column(scale=5, min_width=400):
                # Requirements input
                input_requirement = gr.Textbox(
                    label="Describe your requirements:",
                    placeholder="What would you like me to help you code?",
                    lines=5,
                    show_copy_button=True
                )

                # Options accordion
                with gr.Accordion(label="Options", open=True):
                    # Language selection
                    input_lang = gr.Radio(
                        label="Programming Language",
                        choices=DEV_LANGS,
                        value="Python"
                    )
                    
                    # Model selection dropdown
                    input_model = gr.Dropdown(
                        info="Select model",
                        show_label=False,
                        choices=CodingHandlers.get_available_models(),
                        interactive=True,
                        min_width=120
                    )

                # Control buttons at the bottom of left column
                with gr.Row():
                    btn_clear = gr.ClearButton(
                        value="🗑️ Clear",
                        components=[input_requirement, arch_thinking, output_code]
                    )
                    btn_submit = gr.Button(
                        value="⌨️ Generate",
                        variant="primary"
                    )

            # Right column: Output
            with gr.Column(scale=7, min_width=500):
                # Architecture Design output
                with gr.Accordion(label="Architecture Design", open=True):
                    # Use the pre-defined component
                    arch_thinking.render()
                
                # Generated code output
                with gr.Accordion(label="Generated Code", open=True):
                    # Use the pre-defined component
                    output_code.render()

        # Event handler functions
        def update_btn_phase(phase: str):
            """Update button label for current phase"""
            labels = {
                "arch": "🤔 Designing",
                "code": "⌨️ Coding"
            }
            return labels.get(phase, "⌨️ Generate")

        # Event bindings for two-phase generation
        btn_submit.click(
            fn=lambda: update_btn_phase("arch"),
            outputs=btn_submit
        ).then(
            fn=CodingHandlers.design_arch,
            inputs=[input_requirement, input_lang],
            outputs=arch_thinking,
            api_name="design_arch"
        ).then(
            fn=lambda: update_btn_phase("code"),
            outputs=btn_submit
        ).then(
            fn=CodingHandlers.gen_code,
            inputs=[arch_thinking, input_lang],
            outputs=output_code,
            api_name="gen_code"
        ).then(
            fn=lambda: update_btn_phase("done"),
            outputs=btn_submit
        )

        # Add model selection change handler
        input_model.change(
            fn=CodingHandlers.update_model_id,
            inputs=[input_model],
            outputs=None,
            api_name=False
        )

        # Add model list refresh on load
        interface.load(
            fn=lambda: gr.Dropdown(choices=CodingHandlers.get_available_models()),
            inputs=[],
            outputs=[input_model]
        ).then(  # set selected model 
            fn=CodingHandlers.get_model_id,
            inputs=[],
            outputs=[input_model]  # Update selected model
        )

    return interface

# Create interface
tab_coding = create_interface()
