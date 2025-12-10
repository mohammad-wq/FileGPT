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
from services import fileParser, metadata_db, summary_service, background_worker


def _resolve_summary_for_file(file_path: str, current_summary: str) -> str:
    """
    Ensure we return the best available summary for a file.
    Priority:
      1. current_summary (from Chroma/BM25 metadata) if non-empty and not a placeholder
      2. summary stored in `metadata_db`
      3. generate a summary synchronously (best-effort) and update DB
      4. fallback to empty string
    """
    placeholder_markers = ["generating summary", "summary unavailable", "summary generation returned empty"]

    def looks_like_placeholder(s: str) -> bool:
        if not s:
            return True
        lower = s.lower()
        for p in placeholder_markers:
            if p in lower:
                return True
        # bracket-style placeholders like "[Generating summary...]"
        if lower.startswith('[') and lower.endswith(']'):
            return True
        return False

    # 1. Use current_summary if it seems valid
    if current_summary and not looks_like_placeholder(current_summary):
        return current_summary

    # 2. Try DB-stored summary
    try:
        db_summary = metadata_db.get_summary(file_path)
        if db_summary and not looks_like_placeholder(db_summary):
            return db_summary
    except Exception:
        db_summary = None

        # 3. Do NOT generate summaries synchronously here (avoid blocking /search).
        #    Instead: mark as pending and enqueue for background summarization, then
        #    return a clear pending placeholder so the caller knows it's in progress.
        try:
            # If DB has no summary, mark as pending and enqueue
            metadata_db.update_processing_status(file_path, 'pending_summary')
            try:
                bg = background_worker.get_background_worker()
                bg.add_to_summary_queue(file_path)
            except Exception:
                # If enqueuing fails, just continue — don't block search
                pass
        except Exception:
            pass

        return "[Summary pending]"


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
        content = fileParser.get_file_content(file_path)
        if not content:
            print(f"Skipping {file_path}: No content extracted")
            return False
        
        # Check if file needs reindexing
        if not metadata_db.file_needs_reindex(file_path, content):
            print(f"Skipping {file_path}: Already indexed with same content")
            return False
        
        print(f"Indexing: {file_path}")

        # Step 2: Store file content in metadata DB and mark for background embedding
        # Use store_file_content to avoid generating summary synchronously and
        # mark processing_status='pending_embedding'
        content_hash = metadata_db.calculate_hash(content) if hasattr(metadata_db, 'calculate_hash') else None
        try:
            if content_hash:
                metadata_db.store_file_content(file_path, content, content_hash)
            else:
                # Fallback: calculate hash inline if function missing
                metadata_db.store_file_content(file_path, content, metadata_db.calculate_hash(content))
        except Exception:
            # Best-effort: if storing fails, continue but warn
            print(f"Warning: could not store content for {file_path} in metadata DB")

        # Step 3: Chunk the content
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
        
        # Step 4: Prepare BM25 metadata for this file's chunks (fast keyword index)
        try:
            existing_summary = metadata_db.get_summary(file_path) or ''
        except Exception:
            existing_summary = ''

        metadatas = [{"source": file_path, "summary": existing_summary, "chunk_index": i} for i in range(len(chunks))]

        # Step 5: Update BM25 index (Keyword)
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
        # Step 6: Enqueue embedding work to background worker (non-blocking)
        try:
            bg = background_worker.get_background_worker()
            bg.add_to_embedding_queue(file_path, chunks)
        except Exception as e:
            print(f"Warning: could not enqueue embedding job for {file_path}: {e}")

        print(f"✓ Indexed (metadata+bm25) {file_path}: {len(chunks)} chunks (embedding queued)")
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

    # Preprocess query: remove generic words for BM25
    generic_words = {"find", "search", "show", "get", "look", "for", "all", "the", "a", "an", "my"}
    main_keywords = [w for w in query.lower().split() if w not in generic_words]
    bm25_query = " ".join(main_keywords) if main_keywords else query

    # Semantic search with ChromaDB
    try:
        query_embedding = _embedding_model.encode([query], show_progress_bar=False).tolist()
        chroma_results = _chroma_collection.query(
            query_embeddings=query_embedding,
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

    # Keyword search with BM25 (normalized)
    if _bm25_index and _bm25_corpus:
        try:
            tokenized_query = bm25_query.lower().split()
            bm25_scores = _bm25_index.get_scores(tokenized_query)
            max_bm25 = max(bm25_scores) if bm25_scores else 1.0
            # Normalize scores to 0-1
            norm_bm25_scores = [score / max_bm25 if max_bm25 > 0 else 0 for score in bm25_scores]
            top_indices = sorted(range(len(norm_bm25_scores)), key=lambda i: norm_bm25_scores[i], reverse=True)[:k]
            for idx in top_indices:
                if norm_bm25_scores[idx] > 0:
                    results.append({
                        'content': _bm25_corpus[idx],
                        'source': _bm25_metadata[idx]['source'],
                        'summary': _bm25_metadata[idx].get('summary', ''),
                        'score': norm_bm25_scores[idx],
                        'method': 'keyword'
                    })
        except Exception as e:
            print(f"BM25 search error: {e}")
    
    # Deduplicate by file path (keep highest scoring chunk per file)
    seen_files = {}
    for result in results:
        file_path = result['source']
        # Boost score if filename or summary matches main keyword
        filename = os.path.basename(file_path).lower() if file_path else ""
        summary = result.get('summary', '').lower()
        boost = 0.0
        for kw in main_keywords:
            if kw in filename or kw in summary:
                boost = max(boost, 0.3)  # Boost by 0.3 if match
        score = result['score'] + boost
        if file_path not in seen_files or score > seen_files[file_path]['score']:
            result['score'] = score
            seen_files[file_path] = result

    # Convert back to list and sort by score
    unique_results = list(seen_files.values())
    unique_results.sort(key=lambda x: x['score'], reverse=True)
    # Resolve summaries (check DB / generate if missing) to avoid returning placeholders
    for res in unique_results:
        try:
            res['summary'] = _resolve_summary_for_file(res.get('source', ''), res.get('summary', ''))
        except Exception:
            pass
    # Attach processing status from metadata DB so frontend can show pending/completed
    for res in unique_results:
        try:
            md = metadata_db.get_metadata(res.get('source', ''))
            res['processing_status'] = md.get('processing_status') if md else 'unknown'
        except Exception:
            res['processing_status'] = 'unknown'
    return unique_results[:k]



def index_chunks_to_chroma(file_path: str, chunks: List[str]):
    """
    Generate embeddings for chunks and add them to ChromaDB. This is intended
    to be called from the background worker to avoid blocking indexing.
    """
    global _chroma_collection, _embedding_model

    if not chunks:
        return

    # Ensure embedding model is loaded
    if _embedding_model is None:
        try:
            print("Loading embedding model on-demand...")
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        except Exception as e:
            print(f"Error loading embedding model for chroma indexing: {e}")
            return

    try:
        # Remove old entries for this file
        try:
            _chroma_collection.delete(where={"source": file_path})
        except Exception:
            pass

        chunk_ids = [f"{file_path}:chunk:{i}" for i in range(len(chunks))]

        # Try to get summary from DB (may still be None)
        try:
            summary = metadata_db.get_summary(file_path) or ''
        except Exception:
            summary = ''

        metadatas = [{"source": file_path, "summary": summary, "chunk_index": i} for i in range(len(chunks))]

        # Generate embeddings
        embeddings = _embedding_model.encode(chunks, show_progress_bar=False).tolist()

        _chroma_collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=chunk_ids
        )
    except Exception as e:
        print(f"Error indexing chunks to ChromaDB for {file_path}: {e}")

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
