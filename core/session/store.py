"""
Simplified session storage implementation
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from core.config import env_config
from core.logger import logger
from utils.aws import get_aws_resource
from fastapi import HTTPException
from .models import Session, SessionMetadata

class SessionStore:
    """Simplified session management with DynamoDB storage"""
    
    # Singleton instance
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'SessionStore':
        """Get or create singleton instance"""
        if cls._instance is None:
            try:
                cls._instance = cls()
            except Exception as e:
                logger.error(f"Failed to create session store: {str(e)}")
                raise
        return cls._instance
    
    def __init__(
        self,
        table_name: str = env_config.database_config['session_table'],
        region_name: str = env_config.default_region,
        ttl_days: int = env_config.database_config['retention_days']
    ):
        """Initialize DynamoDB session store"""
        try:
            self.table = get_aws_resource('dynamodb', region_name=region_name).Table(table_name)
            self.ttl_days = ttl_days
            logger.debug(f"Initialized session store with table: {table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize session store: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Store initialization failed: {str(e)}"
            )

    async def create_session(
        self,
        user_name: str,
        module_name: str,
        session_name: Optional[str] = None,
        metadata: Optional[SessionMetadata] = None
    ) -> Session:
        """Create a new session"""
        try:
            creation_time = datetime.now()
            session = Session(
                session_id=str(uuid.uuid4()),
                session_name=session_name or f"{module_name.title()} Session",
                created_time=creation_time,
                updated_time=creation_time,  # Initially same as created_time
                user_name=user_name,
                metadata=metadata or SessionMetadata(module_name=module_name)
            )
            
            # Store session with TTL
            item = {
                **session.to_dict(),
                'ttl': int(datetime.now().timestamp() + (self.ttl_days * 86400))
            }
            self.table.put_item(Item=item)
            
            logger.debug(f"Created session {session.session_id} for user {user_name}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Session creation failed: {str(e)}"
            )

    async def update_session(
            self, 
            session: Session
        ) -> None:
        """Persist the current session data to database and refresh TTL value."""
        try:                
            item = {
                **session.to_dict(),
                'ttl': int(datetime.now().timestamp() + (self.ttl_days * 86400))
            }
            self.table.put_item(Item=item)
            logger.debug(f"Updated session {session.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to update session: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_sessions(
        self,
        user_name: str,
        module_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Session]:
        """List sessions for a user with optional filters"""
        try:
            # Build filter expression
            conditions = ["user_name = :uid"]
            values = {":uid": user_name}
            
            if module_name:
                conditions.append("metadata.module_name = :mod")
                values[":mod"] = module_name
                
            response = self.table.scan(
                FilterExpression=" AND ".join(conditions),
                ExpressionAttributeValues=values
            )
            
            sessions = []
            for item in response.get('Items', []):
                if item.get('ttl', 0) < datetime.now().timestamp():
                    continue
                    
                session = Session.from_dict(item)
                
                # Apply date filters
                if start_date and session.created_time < start_date:
                    continue
                if end_date and session.created_time > end_date:
                    continue
                    
                sessions.append(session)
                
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_session_by_id(self, session_id: str) -> Session:
        """Get session with optional user validation
        
        Args:
            session_id: ID of session to retrieve
            user_name: Optional user ID for ownership validation
            
        Returns:
            Session object if found and valid
            
        Raises:
            HTTPException: If session not found, expired, or access denied
        """
        try:
            response = self.table.get_item(Key={'session_id': session_id})
            
            if 'Item' not in response:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} not found"
                )

            item = response['Item']
            
            # Always validate TTL first
            if item.get('ttl', 0) < datetime.now().timestamp():
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} has expired"
                )
                
            return Session.from_dict(item)
            
        except Exception as e:
            logger.error(f"Failed to get session: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_session_by_id(self, session_id: str) -> bool:
        """Delete session from database by session id"""
        try:
            # Verify ownership first
            await self.get_session_by_id(session_id)
            self.table.delete_item(Key={'session_id': session_id})
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
