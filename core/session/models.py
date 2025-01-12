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
    model_id: Optional[str] = None

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
        user_id: str,   # The user_id is equivalent to username
        metadata: SessionMetadata,
        history: Optional[List[Dict]] = None
    ):
        self.session_id = session_id
        self.session_name = session_name
        self.created_time = created_time
        self.updated_time = updated_time
        self.user_id = user_id
        self.metadata = metadata
        self.history = history or []
        self.context = {
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
            user_id=data['user_id'],
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
            'user_id': self.user_id,
            'metadata': self.metadata.to_dict(),
            'history': self.history,
            'context': self.context
        }

    def add_interaction(self, message: Dict[str, Any]) -> None:
        """
            Add an interaction to session history,
            For multimodal content just add as file path
        """
        # Normalize content format
        if isinstance(message.get('content'), str):
            message['content'] = {'text': message['content']}
            
        # Ensure timestamp
        if 'timestamp' not in message:
            message['timestamp'] = datetime.now().isoformat()
            
        self.history.append(message)
        self.updated_time = datetime.now()  # Store as datetime object
        self.context['total_interactions'] += 1
