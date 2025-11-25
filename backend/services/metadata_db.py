"""
Metadata Database Service for FileGPT
SQLite-based storage for file metadata, summaries, and content hashes.
"""

import sqlite3
import hashlib
import time
from typing import Optional, List, Dict
from pathlib import Path
import os


# Database file location
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'filegpt_metadata.db')


def init_db() -> None:
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            hash TEXT NOT NULL,
            summary TEXT,
            last_indexed REAL NOT NULL
        )
    ''')
    
    # Create index on path for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_path ON files(path)
    ''')
    
    conn.commit()
    conn.close()


def _calculate_hash(content: str) -> str:
    """Calculate SHA256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def upsert_metadata(path: str, content: str, summary: str) -> None:
    """
    Insert or update file metadata.
    
    Args:
        path: Absolute file path
        content: File content for hash calculation
        summary: Generated summary of the file
    """
    content_hash = _calculate_hash(content)
    timestamp = time.time()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO files (path, hash, summary, last_indexed)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                hash = excluded.hash,
                summary = excluded.summary,
                last_indexed = excluded.last_indexed
        ''', (path, content_hash, summary, timestamp))
        
        conn.commit()
    except Exception as e:
        print(f"Error upserting metadata for {path}: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_summary(path: str) -> Optional[str]:
    """
    Retrieve the summary for a file.
    
    Args:
        path: Absolute file path
        
    Returns:
        Summary string, or None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT summary FROM files WHERE path = ?', (path,))
    result = cursor.fetchone()
    
    conn.close()
    
    return result[0] if result else None


def get_metadata(path: str) -> Optional[Dict]:
    """
    Retrieve all metadata for a file.
    
    Args:
        path: Absolute file path
        
    Returns:
        Dictionary with metadata, or None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT path, hash, summary, last_indexed FROM files WHERE path = ?', (path,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return {
            'path': result[0],
            'hash': result[1],
            'summary': result[2],
            'last_indexed': result[3]
        }
    return None


def delete_metadata(path: str) -> None:
    """
    Delete metadata for a file.
    
    Args:
        path: Absolute file path
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM files WHERE path = ?', (path,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting metadata for {path}: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_all_indexed_files() -> List[Dict]:
    """
    Get all indexed files with their metadata.
    
    Returns:
        List of dictionaries containing file metadata
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT path, hash, summary, last_indexed FROM files ORDER BY last_indexed DESC')
    results = cursor.fetchall()
    
    conn.close()
    
    return [
        {
            'path': row[0],
            'hash': row[1],
            'summary': row[2],
            'last_indexed': row[3]
        }
        for row in results
    ]


def file_needs_reindex(path: str, content: str) -> bool:
    """
    Check if a file needs to be reindexed based on content hash.
    
    Args:
        path: Absolute file path
        content: Current file content
        
    Returns:
        True if file is new or content has changed
    """
    metadata = get_metadata(path)
    if not metadata:
        return True
    
    current_hash = _calculate_hash(content)
    return current_hash != metadata['hash']


def get_stats() -> Dict:
    """
    Get database statistics.
    
    Returns:
        Dictionary with stats (total files, db size, etc.)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM files')
    total_files = cursor.fetchone()[0]
    
    conn.close()
    
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    
    return {
        'total_files': total_files,
        'db_size_mb': db_size / (1024 * 1024)
    }
