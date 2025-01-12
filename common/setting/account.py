"""Account settings tab implementation"""
import gradio as gr
from datetime import datetime
from typing import Dict, List
from core.session.store import SessionStore
from core.logger import logger

class AccountSetting:
    """Account settings and session management"""
    
    def __init__(self):
        self.session_store = SessionStore.get_instance()

    def get_display_username(self, request: gr.Request=None) -> str:
        """Get current logged in username for display in settings UI"""
        try:              
            user = request.session.get('user')
            username = user.get('username')
            logger.debug(f"Current username from session: {username}")
            return username or "Not authenticated"
            
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            return "Error getting user"

    async def list_active_sessions(self, username: str) -> List[List]:
        """List active sessions for current user"""
        try:
            if not username or username == "Not authenticated":
                return []
            
            # Use username directly to list sessions
            sessions = await self.session_store.list_sessions(username)
            
            # Convert to list format for dataframe display with history length
            return [
                [
                    s.metadata.module_name.title(),
                    s.session_id,
                    len(s.history),  # Number of records
                    s.created_time.strftime("%Y-%m-%d %H:%M:%S"),
                    s.updated_time.strftime("%Y-%m-%d %H:%M:%S")
                ]
                for s in sessions
            ]
        except Exception as e:
            logger.error(f"Failed to list sessions: {str(e)}")
            gr.Error(f"Failed to list sessions: {str(e)}")
            return []

    async def delete_session(self, session_id: str, username: str) -> List[List]:
        """Delete a specific session"""
        try:
            # Delete session
            await self.session_store.delete_session(session_id, username)
            gr.Info(f"Deleted session {session_id}")
            
            # Return updated sessions list
            return await self.list_active_sessions(username)
            
        except Exception as e:
            logger.error(f"Failed to delete session: {str(e)}")
            gr.Error(f"Failed to delete session: {str(e)}")
            return []

    async def clear_session_history(self, session_id: str, username: str) -> List[List]:
        """Clear history for a specific session"""
        try:

            session = await self.session_store.get_session(session_id, username)
            
            # Clear session history
            if hasattr(session, 'history'):
                session.history = []
            
            # Update session
            await self.session_store.update_session(session, username)
            gr.Info(f"Cleared history for session {session.session_name}")
            
            # Return updated sessions list
            return await self.list_active_sessions(username)
            
        except Exception as e:
            logger.error(f"Failed to clear session history: {str(e)}")
            gr.Error(f"Failed to clear session history: {str(e)}")
            return []

# Create singleton instance
account = AccountSetting()
