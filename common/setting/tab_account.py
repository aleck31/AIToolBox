import gradio as gr
from .account import AccountHandlers

def create_account_tab():
    """Create account management tab UI components"""
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
                pass  # Placeholder

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
                fn=AccountHandlers.list_active_sessions,
                inputs=[user_name],
                outputs=[sessions_list],
                api_name="refresh_sessions"
            )

            btn_delete_session.click(
                fn=AccountHandlers.delete_session,
                inputs=[selected_session_id, user_name],
                outputs=[sessions_list]
            )

            btn_clear_history.click(
                fn=AccountHandlers.clear_session_history,
                inputs=[selected_session_id, user_name],
                outputs=[sessions_list]
            )

    return user_name, sessions_list
