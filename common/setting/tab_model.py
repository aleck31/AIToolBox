import gradio as gr
from .models import ModelHandlers
from llm import VAILD_CATEGORY, VALID_MODALITY


# API Provider choices
API_PROVIDERS = ["Bedrock", "BedrockInvoke", "Gemini", "OpenAI"]

def create_model_tab(model_choices_state):
    """Create model management tab UI components"""
    with gr.Tab("Model Management"):
        with gr.Row():
            with gr.Column(scale=11):
                gr.Markdown("Add, view, and delete LLM models that can be used across different modules.")
            with gr.Column(scale=1):
                btn_refresh_models = gr.Button(value='🔃 Refresh Models', min_width=28, size='sm')

        with gr.Row():
            models_list = gr.Dataframe(
                headers=[
                    "Name", "Model ID", "API Provider", "Vendor", "Category", 
                    "Streaming", "Tool Use", "Reasoning", "Context Window"
                ],
                datatype=["str", "str", "str", "str", "str", "bool", "bool", "bool", "number"],
                label="Available Models",
                show_label=False,
                interactive=False,
                col_count=(9, "fixed")
            )

        # Edit Model Form
        with gr.Group() as model_form:
            form_title = gr.Markdown("| **Add New Model**")
            with gr.Row():
                # Left column - Basic Model Info
                with gr.Column(scale=6):
                    model_id = gr.Textbox(
                        label="Model ID",
                        placeholder="e.g., anthropic.claude-3-sonnet-20240229-v1:0"
                    )
                    with gr.Row():
                        with gr.Column():
                            model_name = gr.Textbox(
                                label="Model Name",
                                placeholder="e.g., Claude 3 Sonnet"
                            )
                        with gr.Column():
                            model_vendor = gr.Textbox(
                                label="Vendor",
                                placeholder="e.g., Anthropic, Google, Amazon"
                            )
                    with gr.Row():
                        with gr.Column():
                            model_provider = gr.Dropdown(
                                label="API Provider",
                                choices=API_PROVIDERS,
                                value="Bedrock"
                            )
                        with gr.Column():
                            model_category = gr.Dropdown(
                                label="Category",
                                choices=VAILD_CATEGORY,
                                value="text"
                            )
                    model_desc = gr.Textbox(
                        label="Description",
                        placeholder="Describe the model's purpose",
                        lines=2
                    )

                # Right column - Model Capabilities
                with gr.Column(scale=6):
                    # gr.Markdown("Model Capabilities", elem_classes=["model-capabilities-header"])
                    context_window = gr.Number(
                        label="Context Window (max tokens)",
                        value=2048,
                        precision=0,
                        interactive=True
                    )
                    input_modality = gr.CheckboxGroup(
                        label="Input Modalities",
                        choices=VALID_MODALITY,
                        interactive=True
                    )
                    output_modality = gr.CheckboxGroup(
                        label="Output Modalities",
                        choices=VALID_MODALITY,
                        interactive=True
                    )
                    gr.Markdown("Other capabilities")
                    with gr.Row():
                        streaming = gr.Checkbox(
                            label="Streaming Support",
                            interactive=True
                        )
                        tool_use = gr.Checkbox(
                            label="Tool Use Support",
                            interactive=True
                        )
                        reasoning = gr.Checkbox(
                            label="Reasoning Support",
                            interactive=True
                        )

                    # Buttons row at the bottom, aligned to the right
                    with gr.Row():
                        with gr.Column(scale=4):
                            # Spacer
                            pass
                        with gr.Column(scale=8):
                            with gr.Row():
                                btn_cancel = gr.Button("Cancel", variant="secondary", size="sm", visible=False)
                                btn_delete = gr.Button("Delete Model", variant="stop", size="sm", visible=False)
                                btn_submit = gr.Button("Add Model", variant="primary", size="sm")

        # Handle model selection for editing
        def handle_model_select(evt: gr.SelectData, models):
            if evt.value:
                row = models.iloc[evt.index[0]]
                # Get the model details from the model manager
                model = ModelHandlers._model_manager.get_model_by_id(row.iloc[1])
                if model:
                    return {
                        form_title: gr.Markdown("| **Edit Model**"),
                        model_name: model.name,
                        model_id: gr.Textbox(value=model.model_id, interactive=False),
                        model_provider: model.api_provider,
                        model_vendor: model.vendor,
                        model_category: model.category,
                        input_modality: model.capabilities.input_modality,
                        output_modality: model.capabilities.output_modality,
                        streaming: model.capabilities.streaming,
                        tool_use: model.capabilities.tool_use,
                        reasoning: model.capabilities.reasoning,
                        context_window: model.capabilities.context_window,
                        model_desc: model.description,
                        btn_submit: gr.Button(value="Update Model", variant="primary"),
                        btn_delete: gr.Button(visible=True),
                        btn_cancel: gr.Button(visible=True)
                    }
            return {
                form_title: gr.Markdown("| **Add New Model**"),
                model_name: "",
                model_id: gr.Textbox(value="", interactive=True),
                model_provider: "Bedrock",
                model_vendor: "",
                model_category: "text",
                model_desc: "",
                input_modality: ["text"],
                output_modality: ["text"],
                streaming: True,
                tool_use: False,
                reasoning: False,
                context_window: 128*1024,
                btn_submit: gr.Button(value="Add Model", variant="primary"),
                btn_delete: gr.Button(visible=False),
                btn_cancel: gr.Button(visible=True)
            }

        models_list.select(
            fn=handle_model_select,
            inputs=[models_list],
            outputs=[
                form_title,
                model_name,
                model_id,
                model_provider,
                model_vendor,
                model_category,
                model_desc,
                input_modality,
                output_modality,
                streaming,
                tool_use,
                reasoning,
                context_window,
                btn_submit,
                btn_delete,
                btn_cancel
            ]
        )

        # Submit button handler for add/update
        def handle_submit(name, id, provider, vendor, category, desc, 
                        input_mods, output_mods, stream, tools, reasoning, context, btn_text):
            if btn_text == "Update Model":
                ModelHandlers.update_model(name, id, provider, vendor, category, desc,
                                        input_mods, output_mods, stream, tools, reasoning, context)
            else:
                ModelHandlers.add_model(name, id, provider, vendor, category, desc,
                                      input_mods, output_mods, stream, tools, reasoning, context)
            
            # Update models list and choices
            models = ModelHandlers.refresh_models()
            choices = ModelHandlers.get_model_choices()
            return models, choices

        btn_submit.click(
            fn=handle_submit,
            inputs=[
                model_name,
                model_id,
                model_provider,
                model_vendor,
                model_category,
                model_desc,
                input_modality,
                output_modality,
                streaming,
                tool_use,
                reasoning,
                context_window,
                btn_submit
            ],
            outputs=[models_list, model_choices_state]
        )

        # Delete button handler
        def handle_delete(id):
            ModelHandlers.delete_model(id)
            # Update models list and choices
            models = ModelHandlers.refresh_models()
            choices = ModelHandlers.get_model_choices()
            return models, choices

        btn_delete.click(
            fn=handle_delete,
            inputs=[model_id],
            outputs=[models_list, model_choices_state]
        ).then(
            # Reset form after deletion
            lambda: (
                gr.Markdown("| **Add New Model**"),
                "",
                gr.Textbox(value="", interactive=True),
                "Bedrock",
                "",
                "text",
                "",
                ["text"],
                ["text"],
                True,
                False,
                False,
                128*1024,
                gr.Button(value="Add Model", variant="primary"),
                gr.Button(visible=False),
                gr.Button(visible=False)
            ),
            outputs=[
                form_title,
                model_name,
                model_id,
                model_provider,
                model_vendor,
                model_category,
                model_desc,
                input_modality,
                output_modality,
                streaming,
                tool_use,
                reasoning,
                context_window,
                btn_submit,
                btn_delete,
                btn_cancel
            ]
        )

        # Cancel button handler
        btn_cancel.click(
            lambda: (
                gr.Markdown("| **Add New Model**"),
                "",
                gr.Textbox(value="", interactive=True),
                "Bedrock",
                "",
                "text",
                "",
                ["text"],
                ["text"],
                True,
                False,
                False,
                128*1024,
                gr.Button(value="Add Model", variant="primary"),
                gr.Button(visible=False),
                gr.Button(visible=False)
            ),
            outputs=[
                form_title,
                model_name,
                model_id,
                model_provider,
                model_vendor,
                model_category,
                model_desc,
                input_modality,
                output_modality,
                streaming,
                tool_use,
                reasoning,
                context_window,
                btn_submit,
                btn_delete,
                btn_cancel
            ]
        )

        # Refresh models button handler
        def handle_refresh():
            models = ModelHandlers.refresh_models()
            choices = ModelHandlers.get_model_choices()
            return models, choices

        btn_refresh_models.click(
            fn=handle_refresh,
            inputs=[],
            outputs=[models_list, model_choices_state]
        )

    return models_list, model_choices_state
