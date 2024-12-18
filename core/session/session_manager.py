from typing import Dict, List, Optional
from datetime import datetime
import uuid
from fastapi import HTTPException
from fastapi.security import HTTPBearer

from . import (
    ModuleSession,
    ModuleSessionManager,
    ModuleMetadata,
    SessionNotFoundError,
    SessionAccessError,
    SessionStorageError
)
from .dynamodb_manager import DynamoDBSessionManager
from core.logger import logger

security = HTTPBearer()

class AuthSessionManager(ModuleSessionManager):
    """Session manager with authentication integration"""
    
    def __init__(
        self,
        base_manager: Optional[DynamoDBSessionManager] = None
    ):
        self.base_manager = base_manager or DynamoDBSessionManager()

    async def create_session(
        self,
        user_id: str,
        module_name: str,
        model_id: Optional[str] = None,
        session_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        initial_context: Optional[Dict] = None
    ) -> ModuleSession:
        """Create a new authenticated session"""
        try:
            # Create session with auth metadata
            session = await self.base_manager.create_session(
                user_id=user_id,
                module_name=module_name,
                model_id=model_id,
                session_name=session_name,
                tags=tags,
                initial_context=initial_context
            )
            
            # Add auth metadata to session context
            session.context['auth'] = {
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Update session with auth metadata
            await self.base_manager.update_session(session, user_id)
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to create authenticated session: {str(e)}")
            raise SessionStorageError(str(e))

    async def get_session(
        self,
        session_id: str,
        user_id: str
    ) -> ModuleSession:
        """Get session with authentication check"""
        try:
            # Get session
            session = await self.base_manager.get_session(session_id, user_id)
            
            # Verify session belongs to authenticated user
            session_auth = session.context.get('auth', {})
            if session_auth.get('user_id') != user_id:
                raise SessionAccessError("Unauthorized access to session")
                
            return session
            
        except (SessionNotFoundError, SessionAccessError):
            raise
        except Exception as e:
            logger.error(f"Failed to get session: {str(e)}")
            raise SessionStorageError(str(e))

    async def update_session(
        self,
        session: ModuleSession,
        user_id: str
    ) -> None:
        """Update session with authentication check"""
        try:
            # Verify session belongs to authenticated user
            session_auth = session.context.get('auth', {})
            if session_auth.get('user_id') != user_id:
                raise SessionAccessError("Unauthorized access to session")
                
            await self.base_manager.update_session(session, user_id)
            
        except SessionAccessError:
            raise
        except Exception as e:
            logger.error(f"Failed to update session: {str(e)}")
            raise SessionStorageError(str(e))

    async def delete_session(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """Delete session with authentication check"""
        try:
            # Get session first to verify ownership
            session = await self.get_session(session_id, user_id)
            
            # Delete session
            return await self.base_manager.delete_session(session_id, user_id)
            
        except (SessionNotFoundError, SessionAccessError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete session: {str(e)}")
            raise SessionStorageError(str(e))

    async def list_sessions(
        self,
        user_id: str,
        module_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ModuleSession]:
        """List sessions for a user"""
        try:
            return await self.base_manager.list_sessions(
                user_id=user_id,
                module_name=module_name,
                tags=tags,
                start_date=start_date,
                end_date=end_date
            )
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {str(e)}")
            raise SessionStorageError(str(e))
