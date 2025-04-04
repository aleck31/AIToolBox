# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from .handlers import AskingHandlers


def create_interface() -> gr.Blocks:
    """Create Asking interface with handlers"""
    # Create interface without eager initialization
    interface = gr.Blocks(theme=gr.themes.Soft())
    
    with interface:
        gr.Markdown("I think, therefore I am.")
        
        # Add state for conversation history (list of message dicts)
        history = gr.State(value=[])
        
        # Define output components first to avoid reference errors
        output_thinking = gr.Markdown(
            value="",
            label='Thinking',
            show_label=False,
            header_links=True,
            line_breaks=True,
            render=False
        )
        
        output_response = gr.Markdown(
            value="",
            label='Final Response',
            show_label=False,
            header_links=True,
            line_breaks=True,
            min_height=120,
            render=False
        )
        
        # Main layout row
        with gr.Row():
            # Left column: Input and Options
            with gr.Column(scale=5, min_width=400):
                # Input box
                input_box = gr.MultimodalTextbox(
                    info="Ask your question:",
                    placeholder="Type a message or upload image(s)",
                    show_label=False,
                    file_types=['text', 'image', 'video', 'audio', '.pdf'],
                    file_count='multiple',
                    lines=6,
                    submit_btn=None,
                    max_plain_text_length=2500
                )
                
                # Options accordion
                with gr.Accordion(label="Options", open=False):
                    # Model selection dropdown
                    input_model = gr.Dropdown(
                        info="Select model",
                        show_label=False,
                        choices=AskingHandlers.get_available_models(),
                        interactive=True,
                        min_width=120
                    )
                
                # Control buttons at the bottom of left column
                with gr.Row():
                    btn_clear = gr.ClearButton(
                        value="🗑️ Clear",
                        components=[input_box, output_thinking, output_response, history]
                    )
                    btn_submit = gr.Button("✨ Go", variant="primary")
            
            # Right column: Output
            with gr.Column(scale=7, min_width=500):
                # Thinking output
                with gr.Accordion(label="Thinking", open=False):
                    # Use the pre-defined component
                    output_thinking.render()
                
                # Final response output
                with gr.Accordion(label="Final Response", open=True):
                    # Use the pre-defined component
                    output_response.render()

        # Event handler functions
        def update_btn_immediate():
            """Update button label immediately on click"""
            return "💭 Thinking"

        def update_btn_label(response):
            """Update submit button label after response"""
            return "🙋 Ask further" if response else "✨ Go"

        def update_history(input_data, history, response):
            """Update conversation history with new interaction"""
            return history + [
                {"role": "user", "content": input_data},
                {"role": "assistant", "content": response}
            ]

        # Event bindings
        btn_submit.click(
            fn=update_btn_immediate,  # First update button
            outputs=btn_submit
        ).then(
            fn=AskingHandlers.gen_with_think,  # Then generate response
            inputs=[input_box, history],
            outputs=[output_thinking, output_response],
            api_name="Asking"
        ).then(
            fn=update_history,  # update history
            inputs=[input_box, history, output_response],
            outputs=history
        ).then(
            fn=update_btn_label,
            inputs=output_response,
            outputs=btn_submit
        )

        # Reset submit button
        btn_clear.click(
            lambda: ("✨ Go"),
            outputs=[btn_submit]
        )
        
        # Add model selection change handler
        input_model.change(
            fn=AskingHandlers.update_model_id,
            inputs=[input_model],
            outputs=None,
            api_name=False
        )

        # Add model list refresh on load
        interface.load(
            fn=lambda: gr.Dropdown(choices=AskingHandlers.get_available_models()),
            inputs=[],
            outputs=[input_model]
        ).then(  # set selected model 
            fn=AskingHandlers.get_model_id,
            inputs=[],
            outputs=[input_model]  # Update selected model
        )
        
    return interface

# Create interface
tab_asking = create_interface()
