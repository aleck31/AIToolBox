# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from fastapi import HTTPException
from llm import VALID_MODALITY
from llm.tools.tool_registry import br_registry
from core.logger import logger
from .account import account
from .models import (
    get_model_choices,
    refresh_models,
    add_model,
    update_model,
    delete_model
)
from .modules import (
    MODULE_LIST,
    update_module_configs,
    refresh_module_configs
)


# Update tools interactivity based on model selection
def set_tools_visible(model_id):
    if model_id and "claude" in model_id.lower():
        return gr.CheckboxGroup(visible=True)
    else:
        return gr.CheckboxGroup(visible=False)


with gr.Blocks() as tab_setting:
    # State to store current model choices
    model_choices_state = gr.State()

    with gr.Tab("Account"):
        with gr.Row():
            gr.Markdown("Manage your account settings and session.")
        with gr.Row():
            with gr.Column(scale=1):
                user_name = gr.Textbox(
                    label="Username",
                    show_label=False,
                    info="Logined user:",
                    max_lines=1,
                    interactive=False
                )
            with gr.Column(scale=1):
                btn_logout = gr.Button(
                    value='🚪 Logout',
                    link="/logout",
                    min_width=12
                )
            with gr.Column(scale=10):
                # 占位
                pass

        with gr.Row():
            # Active Sessions
            sessions_list = gr.Dataframe(
                headers=["Module", "Session ID", "Records", "Created", "Last Updated"],
                datatype=["str", "str", "number", "str", "str"],
                label="Active Sessions",
                interactive=False,
                col_count=(5, "fixed")
            )
        with gr.Row():
            with gr.Row(equal_height=True):
                btn_refresh_sessions = gr.Button("🔃 Refresh Sessions", size="sm")
                btn_clear_history = gr.Button("🧹 Clear History", size="sm", visible=False)
                btn_delete_session = gr.Button("🗑️ Delete Session", variant='stop', size="sm", visible=False)

            # Track selected session id
            selected_session_id = gr.State(value=None)
            # Event handlers
            def handle_session_select(evt: gr.SelectData, sessions):
                """Store session ID and enable action buttons when a session is selected"""
                if evt.value:
                    session_id = sessions.iloc[evt.index[0]].get('Session ID')
                    logger.debug(f"Session ID: {session_id}")
                    return [
                        session_id,
                        gr.Button(visible=True),  # Delete button
                        gr.Button(visible=True)   # Clear history button
                    ]
                return [
                    None,
                    gr.Button(visible=False),
                    gr.Button(visible=False)
                ]

            sessions_list.select(
                fn=handle_session_select,
                inputs=[sessions_list],
                outputs=[selected_session_id, btn_delete_session, btn_clear_history]
            )

            btn_refresh_sessions.click(
                fn=account.list_active_sessions,
                inputs=[user_name],
                outputs=[sessions_list],
                api_name="refresh_sessions"
            )

            btn_delete_session.click(
                fn=account.delete_session,
                inputs=[selected_session_id, user_name],
                outputs=[sessions_list]
            )

            btn_clear_history.click(
                fn=account.clear_session_history,
                inputs=[selected_session_id, user_name],
                outputs=[sessions_list]
            )

    with gr.Tab("Module Configuration"):
        with gr.Row():
            with gr.Column(scale=10):
                gr.Markdown("Configure settings for each module.")
            with gr.Column(scale=2):
                btn_refresh_all = gr.Button(value='🔃 Refresh Configs', min_width=28, size='sm')

        with gr.Row():
            with gr.Column(scale=13):
                # Generate configuration blocks for each module
                module_models = {}
                module_params = {}
                module_tools = {}
                module_save_btns = {}
                # Tools List from registry
                available_tools = list(br_registry.tools.keys())

                for module_name in MODULE_LIST:
                    with gr.Group():
                        with gr.Row():
                            gr.Markdown(f"| **{module_name.title()} Module Settings**")
                            # Save Button
                            module_save_btns[module_name] = gr.Button("💾 Save", size='sm')
                        
                        with gr.Row():
                            with gr.Column(scale=6):
                                # Default Model
                                module_models[module_name] = gr.Dropdown(
                                    label="Default Model",
                                    choices=[],  # Will be populated from state
                                    interactive=True
                                )
                                # Tools config
                                module_tools[module_name] = gr.CheckboxGroup(
                                    label="Enabled Tools",
                                    choices=available_tools,
                                    interactive=True,
                                    visible=False       # Default to invisible
                                )

                            with gr.Column(scale=6):
                                # Parameters
                                module_params[module_name] = gr.Code(
                                    label="Parameters",
                                    language="json",
                                    lines=6
                                )

                        # event handler for default model change
                        module_models[module_name].change(
                            fn=set_tools_visible,
                            inputs=[module_models[module_name]],
                            outputs=[module_tools[module_name]]
                        )

                        module_save_btns[module_name].click(
                            fn=lambda params, tools, model, m=module_name: update_module_configs(m, params, tools, model),
                            inputs=[
                                module_params[module_name],
                                module_tools[module_name],
                                module_models[module_name]
                            ],
                            outputs=[]
                        )
        # Refresh button handler
        btn_refresh_all.click(
            fn=refresh_module_configs,
            inputs=[],
            outputs=[
                *[module_models[m] for m in MODULE_LIST],        # Models
                *[module_params[m] for m in MODULE_LIST],        # Parameters
                *[module_tools[m] for m in MODULE_LIST]          # Tools
            ]
        )

    with gr.Tab("Models"):
        with gr.Row():
            with gr.Column(scale=11):
                gr.Markdown("Add, view, and delete LLM models that can be used across different modules.")
            with gr.Column(scale=1):
                btn_refresh_models = gr.Button(value='🔃 Refresh Models', min_width=28, size='sm')

        with gr.Row():
            models_list = gr.Dataframe(
                headers=["Name", "Model ID", "API Provider", "Vendor", "Modality", "Description"],
                datatype=["str", "str", "str", "str", "str", "str"],
                label="Available Models",
                show_label=False,
                interactive=False,  # Set to false since we'll use select for editing
                col_count=(6, "fixed")
            )

        # API Provider choices
        API_PROVIDERS = ["Bedrock", "BedrockInvoke", "Gemini", "OpenAI"]

        with gr.Row():
            with gr.Column(scale=8):
                # Unified form for Add/Edit Model
                with gr.Group() as model_form:
                    form_title = gr.Markdown("| **Add New Model**")
                    model_name = gr.Textbox(
                        label="Model Name",
                        placeholder="e.g., Claude 3 Sonnet"
                    )
                    model_id = gr.Textbox(
                        label="Model ID",
                        placeholder="e.g., anthropic.claude-3-sonnet-20240229-v1:0"
                    )
                    model_provider = gr.Dropdown(
                        label="API Provider",
                        choices=API_PROVIDERS,
                        value="Bedrock"
                    )
                    model_vendor = gr.Textbox(
                        label="Vendor",
                        placeholder="e.g., Anthropic, Google, Amazon"
                    )                    
                    model_modality = gr.Dropdown(
                        label="Modality",
                        choices=VALID_MODALITY,
                        value="text"
                    )
                    model_desc = gr.Textbox(
                        label="Description",
                        placeholder="Describe the model's purpose"
                    )
                    with gr.Row():
                        btn_submit = gr.Button("Add Model", variant="primary")
                        btn_delete = gr.Button("Delete Model", variant="stop", visible=False)
                        btn_cancel = gr.Button("Cancel", variant="secondary", visible=False)

        # Handle model selection for editing
        def handle_model_select(evt: gr.SelectData, models):
            if evt.value:
                if evt.value:
                    row = models.iloc[evt.index[0]]
                return {
                    form_title: gr.Markdown("| **Edit Model**"),
                    model_name: row.iloc[0],
                    model_id: gr.Textbox(value=row.iloc[1], interactive=False),
                    model_provider: row.iloc[2],
                    model_vendor: row.iloc[3],
                    model_modality: row.iloc[4],
                    model_desc: row.iloc[5],
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
                model_modality: "text",
                model_desc: "",
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
                model_modality,
                model_desc,
                btn_submit,
                btn_delete,
                btn_cancel
            ]
        )

        # Submit button handler
        btn_submit.click(
            fn=lambda name, id, provider, vendor, modality, desc, btn_text: (
                update_model(name, id, provider, vendor, modality, desc) 
                if btn_text == "Update Model" 
                else add_model(name, id, provider, vendor, modality, desc)
            ),
            inputs=[
                model_name,
                model_id,
                model_provider,
                model_vendor,
                model_modality,
                model_desc,
                btn_submit  # Pass button text to determine action
            ],
            outputs=[models_list]
        ).then(
            # Update model choices state after adding/updating model
            fn=get_model_choices,
            inputs=[],
            outputs=[model_choices_state]
        ).then(
            # Update module dropdowns with new choices
            fn=lambda choices: [gr.Dropdown(choices=choices) for _ in MODULE_LIST],
            inputs=[model_choices_state],
            outputs=[module_models[m] for m in MODULE_LIST]
        )

        # Delete button handler
        btn_delete.click(
            fn=lambda id: delete_model(id),
            inputs=[model_id],
            outputs=[models_list]
        ).then(
            # Update model choices state after deleting model
            fn=get_model_choices,
            inputs=[],
            outputs=[model_choices_state]
        ).then(
            # Update module dropdowns with new choices
            fn=lambda choices: [gr.Dropdown(choices=choices) for _ in MODULE_LIST],
            inputs=[model_choices_state],
            outputs=[module_models[m] for m in MODULE_LIST]
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
                model_modality,
                model_desc,
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
                model_modality,
                model_desc,
                btn_submit,
                btn_delete,
                btn_cancel
            ]
        )

        # Refresh models button handler
        btn_refresh_models.click(
            fn=refresh_models,
            inputs=[],
            outputs=[models_list]
        )

    # Initial load with request context
    tab_setting.load(
        fn=account.get_display_username,  # This will receive the request automatically
        inputs=[],
        outputs=[user_name]
    ).success(
        fn=account.list_active_sessions,
        inputs=[user_name],
        outputs=[sessions_list]
    ).success(
        # Initialize model choices state
        fn=get_model_choices,
        inputs=[],
        outputs=[model_choices_state]
    ).success(
        # Initialize module dropdowns with choices
        fn=lambda choices: [gr.Dropdown(choices=choices) for _ in MODULE_LIST],
        inputs=[model_choices_state],
        outputs=[module_models[m] for m in MODULE_LIST]
    ).success(
        # Initialize module configs
        fn=refresh_module_configs,
        inputs=[],
        outputs=[
            *[module_models[m] for m in MODULE_LIST],        # Models
            *[module_params[m] for m in MODULE_LIST],        # Parameters
            *[module_tools[m] for m in MODULE_LIST]          # Tools
        ]
    ).success(
        fn=refresh_models,
        inputs=[],
        outputs=[models_list]
    )
