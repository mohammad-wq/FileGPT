"""
Embedding Generation Service
Handles vector embedding generation and indexing to ChromaDB (called by background worker).
"""

from typing import List
from services import searchEngine


def index_chunks(file_path: str, chunks: List[str]):
    """
    Generate embeddings for chunks and index to ChromaDB.
    Called by background worker for async processing.
    
    Args:
        file_path: Absolute path to file
        chunks: List of text chunks
    """
    searchEngine.index_chunks_to_chroma(file_path, chunks)