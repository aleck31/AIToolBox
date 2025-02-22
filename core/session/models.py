"""
Simplified session data models with serialization support
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class SessionMetadata:
    """Metadata for a module session"""
    module_name: str
    model_id: Optional[str] = None # Reserved for session model override

    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}

class Session:
    """Session data container with serialization support"""
    
    def __init__(
        self,
        session_id: str,
        session_name: str,
        created_time: datetime,
        updated_time: datetime,
        user_name: str,
        metadata: SessionMetadata,
        history: Optional[List[Dict]] = None
    ):
        self.session_id = session_id
        self.session_name = session_name
        self.created_time = created_time
        self.updated_time = updated_time
        self.user_name = user_name
        self.metadata = metadata
        self.history = history or []
        # Initialize context with standard fields
        self.context: Dict[str, Any] = {
            'start_time': created_time.isoformat(),
            'total_interactions': 0,
            'system_prompt': None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Session':
        """Create session from dictionary"""
        session = cls(
            session_id=data['session_id'],
            session_name=data['session_name'],
            created_time=datetime.fromisoformat(data['created_time']),
            updated_time=datetime.fromisoformat(data['updated_time']),
            user_name=data['user_name'],
            metadata=SessionMetadata(**data['metadata']),
            history=data.get('history', [])
        )
        # Load saved context if available
        if 'context' in data:
            session.context.update(data['context'])
        return session

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'session_id': self.session_id,
            'session_name': self.session_name,
            'created_time': self.created_time.isoformat(),
            'updated_time': self.updated_time.isoformat(),
            'user_name': self.user_name,
            'metadata': self.metadata.to_dict(),
            'history': self.history,
            'context': self.context
        }

    def add_interaction(self, message: Dict[str, Any]) -> None:
        """Add an interaction to session history
        
        Args:
            message: Message dictionary containing role and content
            
        Notes:
            - Normalizes content format for consistency
            - Updates session metadata and context
            - Handles both text and multimodal content
        """
        
        # Normalize content to dictionary format
        if isinstance(message.get('content'), str):
            message['content'] = {'text': message['content']}
            
        # Add timestamp if not present
        if 'timestamp' not in message:
            message['timestamp'] = datetime.now().isoformat()
            
        # Update session state
        self.history.append(message)
        self.updated_time = datetime.now()  # Store as datetime object
        self.context['total_interactions'] += 1
