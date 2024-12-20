# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from fastapi import HTTPException
from llm.model_manager import model_manager, VALID_MODEL_TYPES, LLMModel
from core.module_config import module_config
from . import update_module_configs, delete_model, add_model, format_config_json
from core.logger import logger
from common.login import get_user


MODULE_LIST = ['chatbot', 'chatbot-gemini', 'text', 'summary', 'vision', 'coding', 'oneshot', 'draw']

def refresh_configs():
    """Refresh module configurations"""
    # Get module configs
    module_configs = [format_config_json(module_config.get_module_config(m)) for m in MODULE_LIST]
    
    # Return all data
    return module_configs


def refresh_models():
    """Refresh models list"""
    # Get models and convert to list format for display
    models = model_manager.get_models()
    models_data = [[m.name, m.model_id, m.api_provider, m.type, m.description] 
                  for m in models]
    return models_data


def get_display_username():
    """Get current logged in username for display in settings UI"""
    try:
        # Get request from Gradio context
        request = gr.Request().request
        logger.debug(f"Gradio request is: {request}")

        if not request:
            return "Not authenticated"

        # Use the get_user function from login module
        try:
            username = get_user(request)
            logger.debug(f"Current username from session: {username}")
            return username
        except HTTPException:
            return "Not authenticated"
            
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return "Error getting user"


def get_model_choices():
    """Get list of available models for dropdown"""
    models = model_manager.get_models()
    # Return list of tuples (label, value) where label is model name and value is model_id
    return [(f"{m.name}, {m.api_provider}", m.model_id) for m in models]


def update_default_model(module_name, model_id, config_text):
    """Update default model for a module"""
    try:
        # Get current config
        config = module_config.get_module_config(module_name)
        if not config:
            raise ValueError(f"Failed to get config for module: {module_name}")
        
        # Update default model
        config['default_model'] = model_id
        
        # Update module config
        return update_module_configs(module_name, format_config_json(config))
    except Exception as e:
        gr.Error(f"Failed to update default model: {str(e)}")
        return config_text


with gr.Blocks() as tab_setting:

    with gr.Tab("Module Configurations"):
        gr.Markdown("""
        ## Module Configurations
        Configure settings for each module including default models, system prompts and parameters.
        """)
        
        with gr.Row():
            with gr.Column(scale=13):
                # Chatbot module settings
                with gr.Group():
                    with gr.Row():
                        with gr.Column(scale=7):
                            chatbot_config = gr.Code(
                                label="Chatbot Configs",
                                language="json",
                                lines=9
                            )
                        with gr.Column(scale=3):
                            chatbot_model = gr.Dropdown(
                                label="Set default model to:",
                                choices=get_model_choices(),
                                interactive=True
                            )
                            btn_save_chatbot = gr.Button("💾 Save", scale=2)
                    btn_save_chatbot.click(
                        fn=lambda x: update_module_configs("chatbot", x),
                        inputs=[chatbot_config],
                        outputs=[chatbot_config]
                    )
                    chatbot_model.change(
                        fn=lambda m, c: update_default_model("chatbot", m, c),
                        inputs=[chatbot_model, chatbot_config],
                        outputs=[chatbot_config]
                    )

                # Chatbot(Genimi) module settings
                with gr.Group():
                    with gr.Row():
                        with gr.Column(scale=7):
                            chatbot_g_config = gr.Code(
                                label="Chatbot(Genimi) Configs",
                                language="json",
                                lines=9
                            )
                        with gr.Column(scale=3):
                            chatbot_g_model = gr.Dropdown(
                                label="Set default model to:",
                                choices=get_model_choices(),
                                interactive=True
                            )
                            btn_save_chatbot_g = gr.Button("💾 Save", scale=2)
                    btn_save_chatbot_g.click(
                        fn=lambda x: update_module_configs("chatbot-gemini", x),
                        inputs=[chatbot_g_config],
                        outputs=[chatbot_g_config]
                    )
                    chatbot_g_model.change(
                        fn=lambda m, c: update_default_model("chatbot-gemini", m, c),
                        inputs=[chatbot_g_model, chatbot_g_config],
                        outputs=[chatbot_g_config]
                    )

                # Text module settings
                with gr.Group():
                    with gr.Row():
                        with gr.Column(scale=7):
                            text_config = gr.Code(
                                label="Text Module Configs",
                                language="json",
                                lines=9
                            )
                        with gr.Column(scale=3):
                            text_model = gr.Dropdown(
                                label="Set default model to:",
                                choices=get_model_choices(),
                                interactive=True
                            )
                            btn_save_text = gr.Button("💾 Save", scale=2)
                    btn_save_text.click(
                        fn=lambda x: update_module_configs("text", x),
                        inputs=[text_config],
                        outputs=[text_config]
                    )
                    text_model.change(
                        fn=lambda m, c: update_default_model("text", m, c),
                        inputs=[text_model, text_config],
                        outputs=[text_config]
                    )

                # Summary module settings
                with gr.Group():
                    with gr.Row():
                        with gr.Column(scale=7):
                            summary_config = gr.Code(
                                label="Summary Module Configs",
                                language="json",
                                lines=9
                            )
                        with gr.Column(scale=3):
                            summary_model = gr.Dropdown(
                                label="Set default model to:",
                                choices=get_model_choices(),
                                interactive=True
                            )
                            btn_save_summary = gr.Button("💾 Save", scale=2)
                    btn_save_summary.click(
                        fn=lambda x: update_module_configs("summary", x),
                        inputs=[summary_config],
                        outputs=[summary_config]
                    )
                    summary_model.change(
                        fn=lambda m, c: update_default_model("summary", m, c),
                        inputs=[summary_model, summary_config],
                        outputs=[summary_config]
                    )

                # Vision module settings
                with gr.Group():
                    with gr.Row():
                        with gr.Column(scale=7):
                            vision_config = gr.Code(
                                label="Vision Configs",
                                language="json",
                                lines=9
                            )
                        with gr.Column(scale=3):
                            vision_model = gr.Dropdown(
                                label="Set default model to:",
                                choices=get_model_choices(),
                                interactive=True
                            )
                            btn_save_vision = gr.Button("💾 Save", scale=2)
                    btn_save_vision.click(
                        fn=lambda x: update_module_configs("vision", x),
                        inputs=[vision_config],
                        outputs=[vision_config]
                    )
                    vision_model.change(
                        fn=lambda m, c: update_default_model("vision", m, c),
                        inputs=[vision_model, vision_config],
                        outputs=[vision_config]
                    )

                # Coding module settings
                with gr.Group():
                    with gr.Row():
                        with gr.Column(scale=7):
                            coding_config = gr.Code(
                                label="Coding module Configs",
                                language="json",
                                lines=9
                            )
                        with gr.Column(scale=3):
                            coding_model = gr.Dropdown(
                                label="Set default model to:",
                                choices=get_model_choices(),
                                interactive=True
                            )
                            btn_save_code = gr.Button("💾 Save", scale=2)
                    btn_save_code.click(
                        fn=lambda x: update_module_configs("coding", x),
                        inputs=[coding_config],
                        outputs=[coding_config]
                    )
                    coding_model.change(
                        fn=lambda m, c: update_default_model("coding", m, c),
                        inputs=[coding_model, coding_config],
                        outputs=[coding_config]
                    )

                # Oneshot module settings
                with gr.Group():
                    with gr.Row():
                        with gr.Column(scale=7):
                            oneshot_config = gr.Code(
                                label="Oneshop Configs",
                                language="json",
                                lines=9
                            )
                        with gr.Column(scale=3):
                            oneshot_model = gr.Dropdown(
                                label="Set default model to:",
                                choices=get_model_choices(),
                                interactive=True
                            )
                            btn_save_oneshot = gr.Button("💾 Save", scale=2)
                    btn_save_oneshot.click(
                        fn=lambda x: update_module_configs("oneshot", x),
                        inputs=[oneshot_config],
                        outputs=[oneshot_config]
                    )
                    oneshot_model.change(
                        fn=lambda m, c: update_default_model("oneshot", m, c),
                        inputs=[oneshot_model, oneshot_config],
                        outputs=[oneshot_config]
                    )

                # Draw module settings
                with gr.Group():
                    with gr.Row():
                        with gr.Column(scale=7):
                            draw_config = gr.Code(
                                label="Draw Configs",
                                language="json",
                                lines=9
                            )
                        with gr.Column(scale=3):
                            draw_model = gr.Dropdown(
                                label="Set default model to:",
                                choices=get_model_choices(),
                                interactive=True
                            )
                            btn_save_draw = gr.Button("💾 Save", scale=2)
                    btn_save_draw.click(
                        fn=lambda x: update_module_configs("draw", x),
                        inputs=[draw_config],
                        outputs=[draw_config]
                    )
                    draw_model.change(
                        fn=lambda m, c: update_default_model("draw", m, c),
                        inputs=[draw_model, draw_config],
                        outputs=[draw_config]
                    )

            with gr.Column(scale=3):
                with gr.Row():
                    user_name = gr.Textbox(label='User', max_lines=1, interactive=False, scale=3)

                with gr.Row():
                    btn_refresh_all = gr.Button(value='🔃 Refresh', min_width=36, scale=2)
                    btn_logout = gr.Button(value='🚪 Logout', link="/logout", min_width=12, scale=1)

        # Refresh button handler
        btn_refresh_all.click(
            fn=lambda: [get_display_username()] + refresh_configs(),
            inputs=[],
            outputs=[user_name, chatbot_config, chatbot_g_config, text_config, summary_config, vision_config, coding_config, oneshot_config, draw_config]
        )

    with gr.Tab("LLM Models"):
        gr.Markdown("""
        ## Manage LLM Models
        Add, view, and delete LLM models that can be used across different modules.
        """)

        with gr.Row():
            with gr.Column(scale=12):
                models_list = gr.Dataframe(
                    headers=["Name", "Model ID", "API Provider", "Type", "Description"],
                    datatype=["str", "str", "str", "str", "str"],
                    label="Available Models",
                    interactive=False,
                )
                btn_refresh_models = gr.Button(value='🔃 Refresh Models', min_width=48)

        with gr.Row():    
            with gr.Column(scale=4):
                # Add New Model
                with gr.Group():
                    new_model_name = gr.Textbox(label="Model Name", placeholder="e.g., Claude 3 Sonnet")
                    new_model_id = gr.Textbox(label="Model ID", placeholder="e.g., anthropic.claude-3-sonnet-20240229-v1:0")
                    new_model_provider = gr.Textbox(label="API Provider", placeholder="e.g., Bedrock")
                    new_model_type = gr.Dropdown(
                        label="Model Type",
                        choices=VALID_MODEL_TYPES,
                        value="text"
                    )
                    new_model_desc = gr.Textbox(label="Description", placeholder="Describe the model's purpose")
                    btn_add = gr.Button("Add Model", variant="primary")
            with gr.Column(scale=4):
                # Delete a Model
                with gr.Group():
                    delete_model_name = gr.Dropdown(
                        label="Select a model to be deleted:",
                        choices=get_model_choices(),
                        allow_custom_value=True
                    )
                    btn_delete = gr.Button("Delete Model", variant="stop")

        # Event handlers for LLM Models tab
        btn_add.click(
            add_model,
            inputs=[new_model_name, new_model_id, new_model_provider, new_model_type, new_model_desc],
            outputs=[new_model_name, new_model_id, new_model_provider, new_model_type, new_model_desc, models_list]
        )
        
        btn_delete.click(
            delete_model,
            inputs=[delete_model_name],
            outputs=[delete_model_name, models_list]
        )

        # Refresh models button handler
        btn_refresh_models.click(
            fn=refresh_models,
            inputs=[],
            outputs=[models_list]
        )

    # Initial load
    tab_setting.load(
        fn=lambda: [get_display_username()] + refresh_configs() + [refresh_models()],
        inputs=[],
        outputs=[user_name, chatbot_config, chatbot_g_config, text_config, summary_config, vision_config, coding_config, oneshot_config, draw_config, models_list]
    )
