"""
Simplified session management system
"""
from .models import Session, SessionMetadata
from .store import SessionStore

# Export main classes
__all__ = ['Session', 'SessionMetadata', 'SessionStore']
