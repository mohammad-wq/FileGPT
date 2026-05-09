"""
Background Worker for Asynchronous Processing
Handles embedding generation and summarization in background queues with priority.
"""

import threading
import queue
import time
from typing import List, Dict, Optional
import ollama

from services import metadata_db, embeddingGeneration, summary_service, fileParser
from config import get_logger

logger = get_logger("background_worker")


class BackgroundWorker:
    """
    Background processing worker with priority queues.
    
    Features:
    - Batch embedding processing (10-20 chunks at once)
    - Background summarization queue
    - Pause/resume for chat priority
    - Thread-safe operations
    """
    
    def __init__(self, batch_size: int = 20):
        """
        Initialize background worker.
        
        Args:
            batch_size: Number of chunks to process in one embedding batch
        """
        self.batch_size = batch_size
        
        # Priority queues (smaller files processed first)
        self.embedding_queue = queue.PriorityQueue()
        self.summary_queue = queue.PriorityQueue()
        
        # Worker control
        self.running = False
        self.paused = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # Thread lock for pause/resume
        self.pause_lock = threading.Lock()
        self.pause_condition = threading.Condition(self.pause_lock)
        
        # Sequence counter for priority queue tiebreaking
        self._embedding_seq = 0
        self._summary_seq = 0
        self._seq_lock = threading.Lock()
        
        logger.info("Background worker initialized")
    
    def load_pending_from_db(self):
        """
        Load pending embedding and summary tasks from the database.
        Ensures work persistence across restarts.
        """
        logger.info("Loading pending tasks from database...")
        
        # 1. Load pending embeddings
        pending_embeddings = metadata_db.get_pending_embeddings(limit=10000)
        for item in pending_embeddings:
            file_path = item['path']
            try:
                # Extract content to generate chunks
                content = metadata_db.get_file_content(file_path)
                if not content:
                    # If content missing from DB, try to read from file
                    content = fileParser.get_file_content(file_path)
                    if content:
                        metadata_db.store_file_content(file_path, content, metadata_db.calculate_hash(content))
                
                if content:
                    # Same chunking logic as searchEngine.py
                    from langchain_text_splitters import RecursiveCharacterTextSplitter
                    splitter = RecursiveCharacterTextSplitter(
                        chunk_size=600,
                        chunk_overlap=100,
                        length_function=len,
                        separators=["\n\n", "\n", ". ", " ", ""]
                    )
                    chunks = splitter.split_text(content)
                    if chunks:
                        self.add_to_embedding_queue(file_path, chunks)
                else:
                    logger.warning(f"Could not load content for pending embedding: {file_path}")
            except Exception as e:
                logger.error(f"Error re-queuing pending embedding for {file_path}: {e}")
        
        # 2. Load pending summaries
        pending_summaries = metadata_db.get_pending_summaries(limit=10000)
        for item in pending_summaries:
            self.add_to_summary_queue(item['path'])
            
        logger.info(f"Re-queued {len(pending_embeddings)} embeddings and {len(pending_summaries)} summaries from DB")
    
    def start(self):
        """Start the background worker thread."""
        if self.running:
            logger.warning("Worker already running")
            return
        
        self.running = True
        self.paused = False
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("✓ Background worker started")
    
    def stop(self):
        """Stop the background worker thread."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("✓ Background worker stopped")
    
    def pause(self):
        """Pause background processing (e.g., when user is chatting)."""
        with self.pause_lock:
            self.paused = True
            logger.info("⏸️  Background worker paused")
    
    def resume(self):
        """Resume background processing."""
        with self.pause_lock:
            self.paused = False
            self.pause_condition.notify_all()
            logger.info("▶️  Background worker resumed")
    
    def add_to_embedding_queue(self, file_path: str, chunks: List[str]):
        """
        Add file chunks to embedding queue with priority.
        Smaller files (fewer chunks) get higher priority for better UX.
        
        Args:
            file_path: Absolute path to file
            chunks: List of text chunks to embed
        """
        # Priority: smaller chunk count = higher priority (lower number)
        priority = len(chunks)
        
        # Get sequence number for tiebreaking (prevents dict comparison error)
        with self._seq_lock:
            seq = self._embedding_seq
            self._embedding_seq += 1
        
        self.embedding_queue.put((priority, seq, {
            'file_path': file_path,
            'chunks': chunks,
            'timestamp': time.time()
        }))
    
    def add_to_summary_queue(self, file_path: str):
        """
        Add file to summarization queue.
        
        Args:
            file_path: Absolute path to file
        """
        # Default priority (all summaries have same priority for now)
        priority = 100
        
        # Get sequence number for tiebreaking
        with self._seq_lock:
            seq = self._summary_seq
            self._summary_seq += 1
        
        self.summary_queue.put((priority, seq, {
            'file_path': file_path,
            'timestamp': time.time()
        }))
    
    def get_queue_stats(self) -> Dict:
        """
        Get current queue statistics.
        
        Returns:
            Dictionary with queue sizes and worker status
        """
        return {
            'embedding_queue_size': self.embedding_queue.qsize(),
            'summary_queue_size': self.summary_queue.qsize(),
            'running': self.running,
            'paused': self.paused
        }
    
    def _check_pause(self):
        """Check if worker should pause and wait."""
        with self.pause_condition:
            while self.paused and self.running:
                self.pause_condition.wait()
    
    def _worker_loop(self):
        """Main worker loop that processes queues."""
        logger.info("Worker loop started")
        
        while self.running:
            try:
                # Check if paused
                self._check_pause()
                
                # Priority 1: Process embedding queue (critical for search)
                if not self.embedding_queue.empty():
                    self._process_embedding_batch()
                
                # Priority 2: Process summary queue (nice to have)
                elif not self.summary_queue.empty():
                    self._process_summary()
                
                else:
                    # No work, sleep for a bit
                    time.sleep(1)
            
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                time.sleep(1)
        
        logger.info("Worker loop stopped")
    
    def _process_embedding_batch(self):
        """
        Process multiple embedding tasks in one batch for efficiency.
        Batches up to self.batch_size chunks at once.
        """
        batch_items = []
        
        # Collect batch
        while len(batch_items) < self.batch_size and not self.embedding_queue.empty():
            try:
                # PriorityQueue returns (priority, seq, item) tuple
                priority, seq, item = self.embedding_queue.get_nowait()
                batch_items.append(item)
            except queue.Empty:
                break
        
        if not batch_items:
            return
        
        logger.info(f"📦 Processing embedding batch: {len(batch_items)} files")
        
        # Process each file's chunks
        for item in batch_items:
            try:
                file_path = item['file_path']
                chunks = item['chunks']
                
                # Generate embeddings and add to ChromaDB
                embeddingGeneration.index_chunks(file_path, chunks)
                
                # Update status
                metadata_db.update_processing_status(file_path, 'pending_summary')
                
                # Add to summary queue
                self.add_to_summary_queue(file_path)
                
                logger.info(f"  ✓ Embedded: {file_path}")
            
            except Exception as e:
                logger.error(f"  ✗ Error embedding {item.get('file_path', 'unknown')}: {e}")
    
    def _process_summary(self):
        """Process one summarization task."""
        try:
            # PriorityQueue returns (priority, seq, item) tuple
            priority, seq, item = self.summary_queue.get(timeout=1)
        except queue.Empty:
            return
        
        file_path = item['file_path']
        
        try:
            # Get content from database (compressed storage)
            content = metadata_db.get_file_content(file_path)
            
            if not content:
                logger.warning(f"  ✗ No content found for {file_path}")
                return
            
            # Generate summary using LLM
            summary = summary_service.generate_summary(content, file_path)
            
            # Update database with summary
            metadata_db.update_summary(file_path, summary)
            
            logger.info(f"  ✓ Summarized: {file_path}")
        
        except Exception as e:
            logger.error(f"  ✗ Error summarizing {file_path}: {e}")


# Global worker instance
_background_worker: Optional[BackgroundWorker] = None


def get_background_worker() -> BackgroundWorker:
    """
    Get or create the global background worker instance.
    
    Returns:
        BackgroundWorker instance
    """
    global _background_worker
    if _background_worker is None:
        _background_worker = BackgroundWorker(batch_size=20)
    return _background_worker


def start_worker():
    """Start the global background worker."""
    worker = get_background_worker()
    worker.start()


def stop_worker():
    """Stop the global background worker."""
    worker = get_background_worker()
    worker.stop()


def pause_worker():
    """Pause the global background worker."""
    worker = get_background_worker()
    worker.pause()


def resume_worker():
    """Resume the global background worker."""
    worker = get_background_worker()
    worker.resume()
