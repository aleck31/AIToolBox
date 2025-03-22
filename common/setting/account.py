"""Handler implementation for Account settings tab"""
import gradio as gr
from typing import Dict, List, Optional
from core.session.store import SessionStore
from core.logger import logger


class AccountHandlers:
    """Handlers for Account settings and session management"""
    
    # Shared session store instance
    _session_store: Optional[SessionStore] = None

    @classmethod
    def _get_session_store(cls) -> SessionStore:
        """Get or initialize shared session store instance"""
        if cls._session_store is None:
            cls._session_store = SessionStore.get_instance()
        return cls._session_store

    @classmethod
    def get_display_username(cls, request: gr.Request=None) -> str:
        """Get current logged in username for display in settings UI"""
        try:              
            user = request.session.get('user')
            username = user.get('username')
            logger.debug(f"Current username from session: {username}")
            return username or "Not authenticated"
            
        except Exception as e:
            logger.error(f"[AccountHandlers] Error getting current user: {str(e)}")
            return "Error getting user"

    @classmethod
    async def list_active_sessions(cls, username: str) -> List[List]:
        """List active sessions for current user"""
        try:
            if not username or username == "Not authenticated":
                return []
            
            # Use username directly to list sessions
            sessions = await cls._get_session_store().list_sessions(username)
            
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
            logger.error(f"[AccountHandlers] Failed to list sessions: {str(e)}")
            gr.Error(f"Failed to list sessions: {str(e)}")
            return []

    @classmethod
    async def delete_session(cls, session_id: str, username: str) -> List[List]:
        """Delete a specific session"""
        try:
            # Delete session
            await cls._get_session_store().delete_session_by_id(session_id)
            gr.Info(f"Deleted session {session_id}")
            
            # Return updated sessions list
            return await cls.list_active_sessions(username)
            
        except Exception as e:
            logger.error(f"[AccountHandlers] Failed to delete session: {str(e)}")
            gr.Error(f"Failed to delete session: {str(e)}")
            return []

    @classmethod
    async def clear_session_history(cls, session_id: str, username: str) -> List[List]:
        """Clear history for a specific session"""
        try:
            session = await cls._get_session_store().get_session_by_id(session_id)
            
            # Clear session history
            if hasattr(session, 'history'):
                session.history = []
            
            # Update session
            await cls._get_session_store().save_session(session)
            gr.Info(f"Cleared history for session {session.session_name}")

            # Return updated sessions list
            return await cls.list_active_sessions(username)

        except Exception as e:
            logger.error(f"[AccountHandlers] Failed to clear session history: {str(e)}")
            gr.Error(f"Failed to clear session history: {str(e)}")
            return []
