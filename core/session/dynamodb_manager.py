"""
DynamoDB implementation of module session management
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import json
from core.config import env_config
from core.logger import logger
from utils.aws import get_aws_resource
from . import (
    ModuleSession,
    ModuleMetadata,
    ModuleSessionManager,
    SessionNotFoundError,
    SessionAccessError,
    SessionStorageError
)

class DynamoDBSessionManager(ModuleSessionManager):
    """Session manager using DynamoDB as backend"""

    def __init__(
        self,
        table_name: str = env_config.database_config['session_table'],
        ttl_days: int = 30,  # Sessions expire after 30 days by default
        region_name: str = None
    ):
        """Initialize DynamoDB session manager"""
        try:
            # Get DynamoDB resource using centralized AWS configuration
            self.dynamodb = get_aws_resource('dynamodb', region_name=region_name)
            self.table = self.dynamodb.Table(table_name)
            self.ttl_days = ttl_days
            logger.debug(f"Initialized DynamoDB session manager with table: {table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB session manager: {str(e)}")
            raise SessionStorageError(str(e))

    def _serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format string"""
        return dt.isoformat()

    def _deserialize_datetime(self, dt_str: str) -> datetime:
        """Deserialize ISO format string to datetime"""
        return datetime.fromisoformat(dt_str)

    def _serialize_session(self, session: ModuleSession) -> Dict:
        """Convert ModuleSession to DynamoDB item"""
        return {
            'session_id': session.session_id,
            'user_id': session.metadata.user_id,
            'module_name': session.metadata.module_name,
            'metadata': {
                'start_time': self._serialize_datetime(session.metadata.start_time),
                'last_interaction': self._serialize_datetime(session.metadata.last_interaction),
                'total_interactions': session.metadata.total_interactions,
                'model_id': session.metadata.model_id,
                'session_name': session.metadata.session_name,
                'tags': session.metadata.tags or []
            },
            'history': session.history,
            'context': session.context,
            'ttl': int((datetime.utcnow().timestamp() + (self.ttl_days * 86400)))  # TTL in seconds
        }

    def _deserialize_session(self, item: Dict) -> ModuleSession:
        """Convert DynamoDB item to ModuleSession"""
        metadata = ModuleMetadata(
            module_name=item['module_name'],
            user_id=item['user_id'],
            start_time=self._deserialize_datetime(item['metadata']['start_time']),
            last_interaction=self._deserialize_datetime(item['metadata']['last_interaction']),
            total_interactions=item['metadata']['total_interactions'],
            model_id=item['metadata']['model_id'],
            session_name=item['metadata']['session_name'],
            tags=item['metadata']['tags']
        )
        
        return ModuleSession(
            session_id=item['session_id'],
            metadata=metadata,
            history=item.get('history', []),
            context=item.get('context', {})
        )

    async def create_session(
        self,
        user_id: str,
        module_name: str,
        model_id: Optional[str] = None,
        session_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> ModuleSession:
        """Create a new module session"""
        try:
            session_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            metadata = ModuleMetadata(
                module_name=module_name,
                user_id=user_id,
                start_time=now,
                last_interaction=now,
                total_interactions=0,
                model_id=model_id,
                session_name=session_name,
                tags=tags or []
            )
            
            session = ModuleSession(
                session_id=session_id,
                metadata=metadata,
                context=initial_context or {}
            )
            
            # Store in DynamoDB
            item = self._serialize_session(session)
            self.table.put_item(Item=item)
            
            logger.info(f"Created new {module_name} session {session_id} for user {user_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise SessionStorageError(f"Failed to create session: {str(e)}")

    async def get_session(
        self,
        session_id: str,
        user_id: str
    ) -> ModuleSession:
        """Get module session with user validation"""
        try:
            response = self.table.get_item(Key={'session_id': session_id})
            
            if 'Item' not in response:
                raise SessionNotFoundError(f"Session {session_id} not found")
                
            item = response['Item']
            
            # Validate user ownership
            if item['user_id'] != user_id:
                raise SessionAccessError(f"User {user_id} cannot access session {session_id}")
                
            # Check TTL
            if 'ttl' in item and item['ttl'] < datetime.utcnow().timestamp():
                raise SessionNotFoundError(f"Session {session_id} has expired")
                
            return self._deserialize_session(item)
            
        except (SessionNotFoundError, SessionAccessError):
            raise
        except Exception as e:
            logger.error(f"Failed to get session: {str(e)}")
            raise SessionStorageError(f"Failed to get session: {str(e)}")

    async def update_session(
        self,
        session: ModuleSession,
        user_id: str
    ) -> None:
        """Update module session with user validation"""
        try:
            # Validate user ownership
            if session.metadata.user_id != user_id:
                raise SessionAccessError(f"User {user_id} cannot update session {session.session_id}")
                
            # Update in DynamoDB
            item = self._serialize_session(session)
            self.table.put_item(Item=item)
            
            logger.debug(f"Updated session {session.session_id}")
            
        except SessionAccessError:
            raise
        except Exception as e:
            logger.error(f"Failed to update session: {str(e)}")
            raise SessionStorageError(f"Failed to update session: {str(e)}")

    async def delete_session(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """Delete module session with user validation"""
        try:
            # Get session first to validate ownership
            session = await self.get_session(session_id, user_id)
            
            # Delete from DynamoDB
            self.table.delete_item(Key={'session_id': session_id})
            
            logger.info(f"Deleted session {session_id}")
            return True
            
        except (SessionNotFoundError, SessionAccessError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete session: {str(e)}")
            raise SessionStorageError(f"Failed to delete session: {str(e)}")

    async def list_sessions(
        self,
        user_id: str,
        module_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ModuleSession]:
        """List sessions for a user with optional filters"""
        # Note: This is a basic implementation. For production, you'd want to:
        # 1. Use GSIs for efficient querying
        # 2. Implement pagination
        # 3. Add more sophisticated filtering
        try:
            # Scan for user's sessions
            filter_expr = "user_id = :uid"
            expr_values = {":uid": user_id}
            
            if module_name:
                filter_expr += " AND module_name = :mod"
                expr_values[":mod"] = module_name
                
            response = self.table.scan(
                FilterExpression=filter_expr,
                ExpressionAttributeValues=expr_values
            )
            
            sessions = []
            for item in response.get('Items', []):
                session = self._deserialize_session(item)
                
                # Apply additional filters
                if tags and not any(tag in session.metadata.tags for tag in tags):
                    continue
                    
                if start_date and session.metadata.start_time < start_date:
                    continue
                    
                if end_date and session.metadata.start_time > end_date:
                    continue
                    
                sessions.append(session)
                
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {str(e)}")
            raise SessionStorageError(f"Failed to list sessions: {str(e)}")
