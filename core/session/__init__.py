from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import uuid

@dataclass
class ModuleMetadata:
    """Metadata for a module session"""
    module_name: str                    # e.g., 'chatbot', 'vision', etc.
    user_id: str                       # User identifier from auth session
    start_time: datetime               # Session start time
    last_interaction: datetime         # Last interaction time
    total_interactions: int            # Number of interactions
    model_id: Optional[str] = None     # AI model identifier if applicable
    session_name: Optional[str] = None # User-friendly session name
    tags: List[str] = None            # Optional tags for filtering

class ModuleSession:
    """Container for module-specific session data"""
    def __init__(
        self,
        session_id: str,
        metadata: ModuleMetadata,
        history: List[Dict] = None,    # Module-specific interaction history
        context: Dict[str, Any] = None # Module-specific context data
    ):
        self.session_id = session_id
        self.metadata = metadata
        self.history = history or []
        self.context = context or {}
        
    def add_interaction(self, data: Dict[str, Any]) -> None:
        """Add an interaction to session history"""
        self.history.append({
            **data,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.metadata.last_interaction = datetime.utcnow()
        self.metadata.total_interactions += 1
        
    def update_context(self, key: str, value: Any) -> None:
        """Update session context"""
        self.context[key] = value
        self.metadata.last_interaction = datetime.utcnow()

class ModuleSessionManager(ABC):
    """Abstract base class for module session management"""
    
    @abstractmethod
    async def create_session(
        self,
        user_id: str,           # From FastAPI session
        module_name: str,       # Module identifier
        model_id: Optional[str] = None,
        session_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> ModuleSession:
        """Create a new module session"""
        pass
    
    @abstractmethod
    async def get_session(
        self,
        session_id: str,
        user_id: str  # For validation
    ) -> ModuleSession:
        """Get module session with user validation"""
        pass
    
    @abstractmethod
    async def update_session(
        self,
        session: ModuleSession,
        user_id: str  # For validation
    ) -> None:
        """Update module session with user validation"""
        pass
    
    @abstractmethod
    async def delete_session(
        self,
        session_id: str,
        user_id: str  # For validation
    ) -> bool:
        """Delete module session with user validation"""
        pass
    
    @abstractmethod
    async def list_sessions(
        self,
        user_id: str,
        module_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ModuleSession]:
        """List sessions for a user with optional filters"""
        pass

# Exception classes
class SessionException(Exception):
    """Base exception for session-related errors"""
    pass

class SessionNotFoundError(SessionException):
    """Raised when a session is not found"""
    pass

class SessionAccessError(SessionException):
    """Raised when attempting to access another user's session"""
    pass

class SessionStorageError(SessionException):
    """Raised when there's an error with session storage"""
    pass
