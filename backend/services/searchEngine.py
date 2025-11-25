"""
Hybrid RAG Search Engine for FileGPT
Combines semantic (ChromaDB) and keyword (BM25) search with intelligent fusion.
"""

import os
import pickle
from typing import List, Dict, Optional
from pathlib import Path

# Core ML libraries
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

# Text processing
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Local services
from services import doclingDocumentParser, metadata_db, summary_service


# Global state
_chroma_client: Optional[chromadb.PersistentClient] = None
_chroma_collection = None
_embedding_model: Optional[SentenceTransformer] = None
_bm25_index: Optional[BM25Okapi] = None
_bm25_corpus: List[str] = []
_bm25_metadata: List[Dict] = []

# Configuration
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chroma_db')
BM25_PERSIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bm25_index.pkl')
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100


def initialize_indexes():
    """Initialize ChromaDB, embedding model, and BM25 index."""
    global _chroma_client, _chroma_collection, _embedding_model, _bm25_index, _bm25_corpus, _bm25_metadata
    
    # Initialize ChromaDB
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    
    # Get or create collection
    _chroma_collection = _chroma_client.get_or_create_collection(
        name="file_chunks",
        metadata={"hnsw:space": "cosine"}
    )
    
    # Initialize embedding model
    print("Loading embedding model...")
    _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    # Load BM25 index from disk if exists
    _load_bm25_index()
    
    print(f"Search engine initialized. ChromaDB: {_chroma_collection.count()} chunks, BM25: {len(_bm25_corpus)} chunks")


def _load_bm25_index():
    """Load BM25 index from pickle file."""
    global _bm25_index, _bm25_corpus, _bm25_metadata
    
    if os.path.exists(BM25_PERSIST_PATH):
        try:
            with open(BM25_PERSIST_PATH, 'rb') as f:
                data = pickle.load(f)
                _bm25_corpus = data['corpus']
                _bm25_metadata = data['metadata']
                
                # Tokenize corpus for BM25
                tokenized_corpus = [doc.lower().split() for doc in _bm25_corpus]
                _bm25_index = BM25Okapi(tokenized_corpus)
                
                print(f"Loaded BM25 index with {len(_bm25_corpus)} documents")
        except Exception as e:
            print(f"Error loading BM25 index: {e}. Starting fresh.")
            _bm25_corpus = []
            _bm25_metadata = []
            _bm25_index = None
    else:
        _bm25_corpus = []
        _bm25_metadata = []
        _bm25_index = None


def _save_bm25_index():
    """Save BM25 index to pickle file."""
    try:
        with open(BM25_PERSIST_PATH, 'wb') as f:
            pickle.dump({
                'corpus': _bm25_corpus,
                'metadata': _bm25_metadata
            }, f)
    except Exception as e:
        print(f"Error saving BM25 index: {e}")


def index_file_pipeline(file_path: str) -> bool:
    """
    Complete indexing pipeline for a single file.
    
    Args:
        file_path: Absolute path to file
        
    Returns:
        True if indexing succeeded, False otherwise
    """
    global _bm25_index, _bm25_corpus, _bm25_metadata
    
    try:
        # Step 1: Parse file content
        content = doclingDocumentParser.get_file_content(file_path)
        if not content:
            print(f"Skipping {file_path}: No content extracted")
            return False
        
        # Check if file needs reindexing
        if not metadata_db.file_needs_reindex(file_path, content):
            print(f"Skipping {file_path}: Already indexed with same content")
            return False
        
        print(f"Indexing: {file_path}")
        
        # Step 2: Generate summary
        summary = summary_service.generate_summary(content, file_path)
        
        # Step 3: Update metadata database
        metadata_db.upsert_metadata(file_path, content, summary)
        
        # Step 4: Chunk the content
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = splitter.split_text(content)
        
        if not chunks:
            print(f"No chunks created for {file_path}")
            return False
        
        # Step 5: Delete old entries from ChromaDB
        try:
            _chroma_collection.delete(where={"source": file_path})
        except Exception as e:
            print(f"Note: Could not delete old chunks for {file_path}: {e}")
        
        # Step 6: Index in ChromaDB (Vector)
        chunk_ids = [f"{file_path}:chunk:{i}" for i in range(len(chunks))]
        metadatas = [{"source": file_path, "summary": summary, "chunk_index": i} for i in range(len(chunks))]
        
        _chroma_collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=chunk_ids
        )
        
        # Step 7: Update BM25 index (Keyword)
        # Remove old chunks for this file from BM25
        indices_to_remove = [i for i, meta in enumerate(_bm25_metadata) if meta.get('source') == file_path]
        for idx in sorted(indices_to_remove, reverse=True):
            del _bm25_corpus[idx]
            del _bm25_metadata[idx]
        
        # Add new chunks to BM25
        _bm25_corpus.extend(chunks)
        _bm25_metadata.extend(metadatas)
        
        # Re-initialize BM25 with updated corpus
        tokenized_corpus = [doc.lower().split() for doc in _bm25_corpus]
        _bm25_index = BM25Okapi(tokenized_corpus)
        
        # Persist BM25 index
        _save_bm25_index()
        
        print(f"✓ Indexed {file_path}: {len(chunks)} chunks")
        return True
        
    except Exception as e:
        print(f"Error indexing {file_path}: {e}")
        return False


def delete_file_from_index(file_path: str):
    """
    Remove file from all indexes.
    
    Args:
        file_path: Absolute path to file
    """
    global _bm25_index, _bm25_corpus, _bm25_metadata
    
    try:
        # Remove from ChromaDB
        _chroma_collection.delete(where={"source": file_path})
        
        # Remove from BM25
        indices_to_remove = [i for i, meta in enumerate(_bm25_metadata) if meta.get('source') == file_path]
        for idx in sorted(indices_to_remove, reverse=True):
            del _bm25_corpus[idx]
            del _bm25_metadata[idx]
        
        # Re-initialize BM25
        if _bm25_corpus:
            tokenized_corpus = [doc.lower().split() for doc in _bm25_corpus]
            _bm25_index = BM25Okapi(tokenized_corpus)
        else:
            _bm25_index = None
        
        _save_bm25_index()
        
        # Remove from metadata DB
        metadata_db.delete_metadata(file_path)
        
        print(f"Deleted {file_path} from indexes")
        
    except Exception as e:
        print(f"Error deleting {file_path} from indexes: {e}")


def hybrid_search(query: str, k: int = 5) -> List[Dict]:
    """
    Hybrid search combining semantic (ChromaDB) and keyword (BM25) retrieval.
    
    Args:
        query: Search query
        k: Number of results to return from each method
        
    Returns:
        List of result dictionaries with 'content', 'source', 'summary', 'score'
    """
    results = []
    
    # Semantic search with ChromaDB
    try:
        chroma_results = _chroma_collection.query(
            query_texts=[query],
            n_results=min(k, _chroma_collection.count())
        )
        
        if chroma_results and chroma_results['documents'] and chroma_results['documents'][0]:
            for i, doc in enumerate(chroma_results['documents'][0]):
                results.append({
                    'content': doc,
                    'source': chroma_results['metadatas'][0][i]['source'],
                    'summary': chroma_results['metadatas'][0][i].get('summary', ''),
                    'score': 1.0 - chroma_results['distances'][0][i] if chroma_results['distances'] else 0.5,
                    'method': 'semantic'
                })
    except Exception as e:
        print(f"ChromaDB search error: {e}")
    
    # Keyword search with BM25
    if _bm25_index and _bm25_corpus:
        try:
            tokenized_query = query.lower().split()
            bm25_scores = _bm25_index.get_scores(tokenized_query)
            
            # Get top k indices
            top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:k]
            
            for idx in top_indices:
                if bm25_scores[idx] > 0:  # Only include results with non-zero scores
                    results.append({
                        'content': _bm25_corpus[idx],
                        'source': _bm25_metadata[idx]['source'],
                        'summary': _bm25_metadata[idx].get('summary', ''),
                        'score': bm25_scores[idx],
                        'method': 'keyword'
                    })
        except Exception as e:
            print(f"BM25 search error: {e}")
    
    # Deduplicate and merge results
    seen_content = set()
    unique_results = []
    
    for result in results:
        content_key = (result['content'][:100], result['source'])  # Use first 100 chars + source as key
        if content_key not in seen_content:
            seen_content.add(content_key)
            unique_results.append(result)
    
    # Sort by score
    unique_results.sort(key=lambda x: x['score'], reverse=True)
    
    return unique_results[:k]


def get_index_stats() -> Dict:
    """
    Get statistics about the search indexes.
    
    Returns:
        Dictionary with index statistics
    """
    return {
        'chroma_chunks': _chroma_collection.count() if _chroma_collection else 0,
        'bm25_chunks': len(_bm25_corpus),
        'embedding_model': EMBEDDING_MODEL_NAME,
        'db_stats': metadata_db.get_stats()
    }
