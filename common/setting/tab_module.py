import gradio as gr
from llm.tools.tool_registry import br_registry
from .modules import ModuleHandlers, MODULE_LIST

def set_tools_visible(model_id):
    """Update tools interactivity based on model selection"""
    if model_id and "claude" in model_id.lower():   #Todo: based on the model tool_use capabilities.
        return gr.CheckboxGroup(visible=True)
    else:
        return gr.CheckboxGroup(visible=False)

def create_module_tab():
    """Create module configuration tab UI components"""
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
                                    choices=[],  # Initialize empty, will be populated later
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
                            fn=lambda params, tools, model, m=module_name: ModuleHandlers.update_module_configs(m, params, tools, model),
                            inputs=[
                                module_params[module_name],
                                module_tools[module_name],
                                module_models[module_name]
                            ],
                            outputs=[]
                        )

        # Refresh button handler
        btn_refresh_all.click(
            fn=ModuleHandlers.refresh_module_configs,
            inputs=[],
            outputs=[
                *[module_models[m] for m in MODULE_LIST],        # Models
                *[module_params[m] for m in MODULE_LIST],        # Parameters
                *[module_tools[m] for m in MODULE_LIST]          # Tools
            ]
        )

    return {
        'models': module_models,
        'params': module_params,
        'tools': module_tools
    }
