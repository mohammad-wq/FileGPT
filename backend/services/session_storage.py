"""
Persistent Session Storage with SQLite
Stores conversation history persistently across server restarts.
"""

import os
import sys
import sqlite3
import json
import time
import threading
from typing import Dict, List, Optional
from pathlib import Path
import uuid

# Add parent directory to path for config import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import SessionConfig, get_logger

logger = get_logger("session_storage")


class PersistentSessionStorage:
    """
    SQLite-backed persistent session storage.
    Stores conversation history that survives server restarts.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize persistent storage.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path or SessionConfig.DB_PATH
        self.lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    messages TEXT NOT NULL DEFAULT '[]'
                )
            """)
            
            # Index for efficient cleanup of expired sessions
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_accessed 
                ON sessions(last_accessed)
            """)
            
            conn.commit()
        
        logger.info(f"✓ Session storage initialized at {self.db_path}")
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """
        Create a new session. If `session_id` is not provided, a UUID will be generated.

        Args:
            session_id: Optional session identifier. If omitted, a new UUID is created.

        Returns:
            The session_id that was created (or existing one if already present).
        """
        now = time.time()

        if session_id is None:
            session_id = str(uuid.uuid4())

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO sessions (session_id, created_at, last_accessed, messages)
                    VALUES (?, ?, ?, '[]')
                """, (session_id, now, now))
                conn.commit()

            logger.debug(f"Created or ensured session {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}")
            # If creation fails, still return the session_id so callers can continue
            return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        Add a message to a session.
        
        Args:
            session_id: Session identifier
            role: 'user' or 'assistant'
            content: Message content
        """
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Get current messages
                    cursor = conn.execute(
                        "SELECT messages FROM sessions WHERE session_id = ?",
                        (session_id,)
                    )
                    row = cursor.fetchone()
                    
                    if not row:
                        # Create session if doesn't exist
                        self.create_session(session_id)
                        messages = []
                    else:
                        messages = json.loads(row[0])
                    
                    # Add new message
                    messages.append({
                        "role": role,
                        "content": content,
                        "timestamp": time.time()
                    })
                    
                    # Keep only last N messages
                    if len(messages) > SessionConfig.MAX_MESSAGES_PER_SESSION:
                        messages = messages[-SessionConfig.MAX_MESSAGES_PER_SESSION:]
                    
                    # Update session
                    conn.execute(
                        "UPDATE sessions SET messages = ?, last_accessed = ? WHERE session_id = ?",
                        (json.dumps(messages), time.time(), session_id)
                    )
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"Error adding message: {e}")
    
    def get_history(self, session_id: str) -> List[Dict]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of messages
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT messages FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    # Update last access
                    conn.execute(
                        "UPDATE sessions SET last_accessed = ? WHERE session_id = ?",
                        (time.time(), session_id)
                    )
                    conn.commit()
                    
                    return json.loads(row[0])
        except Exception as e:
            logger.error(f"Error getting history: {e}")
        
        return []
    
    def clear_session(self, session_id: str):
        """
        Clear message history for a session.
        
        Args:
            session_id: Session identifier
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE sessions SET messages = '[]', last_accessed = ? WHERE session_id = ?",
                    (time.time(), session_id)
                )
                conn.commit()
            logger.debug(f"Cleared session {session_id}")
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
    
    def cleanup_expired_sessions(self):
        """Delete sessions that haven't been accessed in TTL seconds."""
        cutoff_time = time.time() - SessionConfig.SESSION_TTL_SECONDS
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE last_accessed < ?",
                    (cutoff_time,)
                )
                deleted = cursor.rowcount
                conn.commit()
            
            if deleted > 0:
                logger.info(f"🧹 Cleaned up {deleted} expired sessions")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_stats(self) -> Dict:
        """Get storage statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM sessions")
                total_sessions = cursor.fetchone()[0]
                
                cursor = conn.execute(
                    "SELECT SUM(LENGTH(messages)) FROM sessions"
                )
                total_size = cursor.fetchone()[0] or 0
                
                return {
                    "total_sessions": total_sessions,
                    "storage_size_bytes": total_size,
                    "db_path": self.db_path
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}


# Global persistent storage instance
_storage = None


def get_persistent_storage() -> PersistentSessionStorage:
    """Get or create global persistent storage instance."""
    global _storage
    if _storage is None:
        _storage = PersistentSessionStorage()
    return _storage


class CleanupScheduler:
    """Schedules periodic cleanup of expired sessions."""
    
    def __init__(self, storage: PersistentSessionStorage):
        self.storage = storage
        self.running = False
        self.thread = None
    
    def start(self):
        """Start cleanup scheduler."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.thread.start()
        logger.info("✓ Session cleanup scheduler started")
    
    def stop(self):
        """Stop cleanup scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("✓ Session cleanup scheduler stopped")
    
    def _cleanup_loop(self):
        """Background cleanup loop."""
        while self.running:
            try:
                self.storage.cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            
            time.sleep(SessionConfig.CLEANUP_INTERVAL_SECONDS)


# Global scheduler instance
_scheduler = None


def start_cleanup_scheduler():
    """Start the background session cleanup."""
    global _scheduler
    if _scheduler is None:
        storage = get_persistent_storage()
        _scheduler = CleanupScheduler(storage)
        _scheduler.start()


def stop_cleanup_scheduler():
    """Stop the background session cleanup."""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None
