# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from common import USER_CONF
from common.llm_config import get_llm_models, get_module_config, VALID_MODEL_TYPES
from . import update_module_settings, delete_model, add_model, format_config_text


MODULE_LIST = ['chatbot', 'chatbot-gemini','text', 'vision', 'coding', 'oneshot', 'draw']

with gr.Blocks() as tab_setting:

    with gr.Tab("Module Configurations"):
        gr.Markdown("""
        ## Module Configurations
        Configure settings for each module including default models, system prompts and parameters.
        """)
        
        with gr.Row():
            with gr.Column(scale=14):
                # Chatbot module settings
                with gr.Group():
                    chatbot_config = gr.TextArea(
                        label="Chatbot Settings",
                        lines=8
                    )
                    btn_save_chatbot = gr.Button("💾 Save", variant="primary")
                    btn_save_chatbot.click(
                        fn=lambda x: update_module_settings("chatbot", x),
                        inputs=[chatbot_config],
                        outputs=[chatbot_config]
                    )

                with gr.Group():
                    chatbot_g_config = gr.TextArea(
                        label="Chatbot(Genimi) Settings",                        
                        lines=8
                    )
                    btn_save_chatbot = gr.Button("💾 Save", variant="primary")
                    btn_save_chatbot.click(
                        fn=lambda x: update_module_settings("chatbot-gemini", x),
                        inputs=[chatbot_g_config],
                        outputs=[chatbot_g_config]
                    )

                # Text module settings
                with gr.Group():
                    text_config = gr.TextArea(
                        label="Text Module Settings",
                        lines=8
                    )
                    btn_save_text = gr.Button("💾 Save", variant="primary")
                    btn_save_text.click(
                        fn=lambda x: update_module_settings("text", x),
                        inputs=[text_config],
                        outputs=[text_config]
                    )

                # Vision module settings
                with gr.Group():
                    vision_config = gr.TextArea(
                        label="Vision Settings",
                        lines=8
                    )
                    btn_save_vision = gr.Button("💾 Save", variant="primary")
                    btn_save_vision.click(
                        fn=lambda x: update_module_settings("vision", x),
                        inputs=[vision_config],
                        outputs=[vision_config]
                    )

                # Coding module settings
                with gr.Group():
                    coding_config = gr.TextArea(
                        label="Coding module Settings",
                        lines=8
                    )
                    btn_save_code = gr.Button("💾 Save", variant="primary")
                    btn_save_code.click(
                        fn=lambda x: update_module_settings("coding", x),
                        inputs=[coding_config],
                        outputs=[coding_config]
                    )

                # Oneshot module settings
                with gr.Group():
                    oneshot_config = gr.TextArea(
                        label="Oneshop Settings",
                        lines=8
                    )
                    btn_save_oneshot = gr.Button("💾 Save", variant="primary")
                    btn_save_oneshot.click(
                        fn=lambda x: update_module_settings("oneshot", x),
                        inputs=[oneshot_config],
                        outputs=[oneshot_config]
                    )

                # Draw module settings
                with gr.Group():
                    draw_config = gr.TextArea(
                        label="Draw Settings",
                        lines=8
                    )
                    btn_save_draw = gr.Button("💾 Save", variant="primary")
                    btn_save_draw.click(
                        fn=lambda x: update_module_settings("draw", x),
                        inputs=[draw_config],
                        outputs=[draw_config]
                    )

            with gr.Column(scale=2):
                with gr.Row():
                    user_name = gr.Textbox(label='User', max_lines=1, interactive=False, scale=6)
                    btn_logout = gr.Button(value='🚪', link="/logout", min_width=16, scale=1)

                with gr.Row():
                    btn_refresh_all = gr.Button(value='🔃 Refresh', min_width=48)

        # Refresh button handler
        btn_refresh_all.click(
            lambda: ([USER_CONF.username] +
                    [format_config_text(get_module_config(m)) for m in MODULE_LIST] +
                    [[[m['name'], m['model_id'], m.get('provider', ''), m.get('model_type', 'text'), m.get('description', '')] 
                    for m in get_llm_models()]]),
            None,
            [user_name, chatbot_config, chatbot_g_config, vision_config, coding_config, oneshot_config, draw_config]
        )

    with gr.Tab("LLM Models"):
        gr.Markdown("""
        ## Manage LLM Models
        Add, view, and delete LLM models that can be used across different modules.
        """)

        with gr.Row():
            with gr.Column(scale=12):
                models_display = gr.Dataframe(
                    headers=["Name", "Model ID", "Provider", "Type", "Description"],
                    datatype=["str", "str", "str", "str", "str"],
                    label="Available Models",
                    interactive=False,
                )
        with gr.Row():    
            with gr.Column(scale=4):
                with gr.Group():
                    gr.Label("Add New Model")
                    new_model_name = gr.Textbox(label="Model Name", placeholder="e.g., my-claude3")
                    new_model_id = gr.Textbox(label="Model ID", placeholder="e.g., anthropic.claude-3-sonnet-20240229-v1:0")
                    new_model_provider = gr.Dropdown(
                        label="Provider",
                        choices=["anthropic", "google", "stability", "other"],
                        allow_custom_value=True
                    )
                    new_model_type = gr.Dropdown(
                        label="Model Type",
                        choices=VALID_MODEL_TYPES,
                        value="text"
                    )
                    new_model_desc = gr.Textbox(label="Description", placeholder="Describe the model's purpose")
                    btn_add = gr.Button("Add Model", variant="primary")
            with gr.Column(scale=4):
                with gr.Group():
                    gr.Label("Delete Model")
                    delete_model_name = gr.Dropdown(
                        label="Select Model",
                        choices=[m["name"] for m in get_llm_models()],
                        allow_custom_value=True
                    )
                    btn_delete = gr.Button("Delete Model", variant="stop")

        # Event handlers for LLM Models tab
        btn_add.click(
            add_model,
            inputs=[new_model_name, new_model_id, new_model_provider, new_model_type, new_model_desc],
            outputs=[new_model_name, new_model_id, new_model_provider, new_model_type, new_model_desc, models_display]
        )
        
        btn_delete.click(
            delete_model,
            inputs=[delete_model_name],
            outputs=[delete_model_name, models_display]
        )

    # Update all settings on page load
    tab_setting.load(
        lambda: ([USER_CONF.username] +
                [format_config_text(get_module_config(m)) for m in MODULE_LIST] +
                [[[m['name'], m['model_id'], m.get('provider', ''), m.get('model_type', 'text'), m.get('description', '')] 
                  for m in get_llm_models()]]),
        None,
        [user_name, chatbot_config, chatbot_g_config, text_config, coding_config, vision_config, oneshot_config, draw_config, models_display]
    )
