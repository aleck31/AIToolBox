import gradio as gr
from .tab_account import create_account_tab
from .tab_module import create_module_tab
from .tab_model import create_model_tab
from .modules import ModuleHandlers
from .account import AccountHandlers
from .models import ModelHandlers

with gr.Blocks() as tab_setting:
    # State to store current model choices
    model_choices_state = gr.State()

    # Create tabs using the component functions
    user_name, sessions_list = create_account_tab()
    module_components = create_module_tab()
    models_list, _ = create_model_tab(model_choices_state)  # Properly unpack tuple

    # Initial load with request context
    tab_setting.load(
        # First get username
        fn=AccountHandlers.get_display_username,  # This will receive gr.Request automatically
        inputs=[],
        outputs=[user_name]
    ).success(
        # Then list sessions
        fn=AccountHandlers.list_active_sessions,
        inputs=[user_name],
        outputs=[sessions_list]
    ).success(
        # Initialize model choices state
        fn=ModelHandlers.get_model_choices,
        inputs=[],
        outputs=[model_choices_state]
    ).success(
        # Initialize/update module dropdowns with choices
        fn=lambda choices: [gr.update(choices=choices) for _ in module_components['models'].values()],
        inputs=[model_choices_state],
        outputs=[*module_components['models'].values()]
    ).success(
        # Initialize/refresh module configurations
        fn=ModuleHandlers.refresh_module_configs,
        inputs=[],
        outputs=[
            *module_components['models'].values(),
            *module_components['params'].values(),
            *module_components['tools'].values()
        ]
    ).then(
        # Then refresh models list
        fn=ModelHandlers.refresh_models,
        inputs=[],
        outputs=[models_list]
    )

    # Update model choices state when models list changes
    models_list.change(
        fn=ModelHandlers.get_model_choices,
        outputs=[model_choices_state]
    ).success(
        # Then update module dropdowns with new choices
        fn=lambda choices: [gr.update(choices=choices) for _ in module_components['models'].values()],
        inputs=[model_choices_state],
        outputs=[*module_components['models'].values()]
    )
