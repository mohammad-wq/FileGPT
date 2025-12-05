"""
Lightweight Session Management for Conversation History
Stores last N messages per session with auto-expiration.
"""

import time
import uuid
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Message:
    """Single conversation message."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float


class SessionManager:
    """
    Manages conversation sessions with automatic cleanup.
    
    Features:
    - In-memory storage (fast, no DB overhead)
    - Auto-expiration (1 hour TTL)
    - Max 5 messages per session
    - Thread-safe operations
    """
    
    def __init__(self, max_messages: int = 5, ttl_seconds: int = 3600):
        """
        Initialize session manager.
        
        Args:
            max_messages: Maximum messages to store per session
            ttl_seconds: Time-to-live for sessions (default: 1 hour)
        """
        self.max_messages = max_messages
        self.ttl_seconds = ttl_seconds
        
        # Storage: {session_id: {"messages": [], "last_access": timestamp}}
        self._sessions: Dict[str, dict] = {}
        self._lock = threading.Lock()
    
    def create_session(self) -> str:
        """
        Create a new session and return its ID.
        
        Returns:
            New session ID (UUID)
        """
        session_id = str(uuid.uuid4())
        
        with self._lock:
            self._sessions[session_id] = {
                "messages": [],
                "last_access": time.time()
            }
        
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        Add a message to a session.
        
        Args:
            session_id: Session identifier
            role: 'user' or 'assistant'
            content: Message content
        """
        with self._lock:
            # Create session if doesn't exist
            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    "messages": [],
                    "last_access": time.time()
                }
            
            session = self._sessions[session_id]
            
            # Add message
            message = Message(
                role=role,
                content=content,
                timestamp=time.time()
            )
            session["messages"].append(message)
            
            # Keep only last N messages
            if len(session["messages"]) > self.max_messages:
                session["messages"] = session["messages"][-self.max_messages:]
            
            # Update last access time
            session["last_access"] = time.time()
    
    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of message dicts with 'role' and 'content'
        """
        with self._lock:
            if session_id not in self._sessions:
                return []
            
            session = self._sessions[session_id]
            session["last_access"] = time.time()
            
            # Convert to dict format
            return [
                {"role": msg.role, "content": msg.content}
                for msg in session["messages"]
            ]
    
    def clear_session(self, session_id: str):
        """
        Clear conversation history for a session.
        
        Args:
            session_id: Session identifier
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
    
    def cleanup_expired(self):
        """Remove sessions that haven't been accessed in TTL period."""
        current_time = time.time()
        
        with self._lock:
            expired_sessions = [
                sid for sid, session in self._sessions.items()
                if current_time - session["last_access"] > self.ttl_seconds
            ]
            
            for sid in expired_sessions:
                del self._sessions[sid]
            
            if expired_sessions:
                print(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_stats(self) -> Dict:
        """Get session statistics."""
        with self._lock:
            total_sessions = len(self._sessions)
            total_messages = sum(
                len(session["messages"])
                for session in self._sessions.values()
            )
            
            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "max_messages_per_session": self.max_messages,
                "ttl_seconds": self.ttl_seconds
            }


# Global session manager instance
_session_manager: Optional[SessionManager] = None
_cleanup_thread: Optional[threading.Thread] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager."""
    global _session_manager, _cleanup_thread
    
    if _session_manager is None:
        _session_manager = SessionManager(max_messages=5, ttl_seconds=3600)
        
        # Start cleanup thread (runs every 5 minutes)
        def cleanup_loop():
            while True:
                time.sleep(300)  # 5 minutes
                _session_manager.cleanup_expired()
        
        _cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        _cleanup_thread.start()
        
        print("✓ Session manager initialized")
    
    return _session_manager
