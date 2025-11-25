"""
File Watcher Service for FileGPT
Real-time file system monitoring with automatic indexing.
"""

import os
import time
from typing import List, Set
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from services import searchEngine, doclingDocumentParser


# Ignore patterns
IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env',
    'dist', 'build', '.cache', '.pytest_cache', '.mypy_cache',
    '.idea', '.vscode', '.vs', 'bin', 'obj', 'target'
}

IGNORE_FILES = {
    '.DS_Store', 'Thumbs.db', '.gitignore', '.gitattributes'
}

# Debounce delay in seconds
DEBOUNCE_DELAY = 0.5


class FileIndexHandler(FileSystemEventHandler):
    """Handles file system events and triggers indexing."""
    
    def __init__(self):
        super().__init__()
        self._processing: Set[str] = set()
    
    def _should_process(self, file_path: str) -> bool:
        """Check if a file should be processed."""
        # Skip if already processing
        if file_path in self._processing:
            return False
        
        # Skip directories
        if os.path.isdir(file_path):
            return False
        
        # Get filename and directory name
        filename = os.path.basename(file_path)
        
        # Skip hidden files
        if filename.startswith('.'):
            return False
        
        # Skip ignored files
        if filename in IGNORE_FILES:
            return False
        
        # Skip if in ignored directory
        path_parts = Path(file_path).parts
        if any(part in IGNORE_DIRS or part.startswith('.') for part in path_parts):
            return False
        
        # Check if file type is supported
        if not doclingDocumentParser.is_supported_file(file_path):
            return False
        
        return True
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if not self._should_process(file_path):
            return
        
        # Debounce: wait a bit to ensure file is fully written
        time.sleep(DEBOUNCE_DELAY)
        
        # Check if file still exists (might have been a temp file)
        if not os.path.exists(file_path):
            return
        
        self._processing.add(file_path)
        try:
            print(f"New file detected: {file_path}")
            searchEngine.index_file_pipeline(file_path)
        finally:
            self._processing.discard(file_path)
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if not self._should_process(file_path):
            return
        
        # Debounce
        time.sleep(DEBOUNCE_DELAY)
        
        if not os.path.exists(file_path):
            return
        
        self._processing.add(file_path)
        try:
            print(f"File modified: {file_path}")
            searchEngine.index_file_pipeline(file_path)
        finally:
            self._processing.discard(file_path)
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        print(f"File deleted: {file_path}")
        searchEngine.delete_file_from_index(file_path)


class FileWatcher:
    """File system watcher manager."""
    
    def __init__(self):
        self.observer = Observer()
        self.handler = FileIndexHandler()
        self.watched_paths: Set[str] = set()
    
    def add_path(self, path: str):
        """
        Add a directory to watch.
        
        Args:
            path: Absolute path to directory
        """
        if not os.path.exists(path):
            print(f"Path does not exist: {path}")
            return False
        
        if not os.path.isdir(path):
            print(f"Path is not a directory: {path}")
            return False
        
        if path in self.watched_paths:
            print(f"Already watching: {path}")
            return True
        
        try:
            self.observer.schedule(self.handler, path, recursive=True)
            self.watched_paths.add(path)
            print(f"Now watching: {path}")
            return True
        except Exception as e:
            print(f"Error adding watch path {path}: {e}")
            return False
    
    def start(self):
        """Start the file watcher."""
        if not self.observer.is_alive():
            self.observer.start()
            print("File watcher started")
    
    def stop(self):
        """Stop the file watcher."""
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            print("File watcher stopped")
    
    def get_watched_paths(self) -> List[str]:
        """Get list of watched directories."""
        return list(self.watched_paths)


# Global watcher instance
_watcher: FileWatcher = None


def get_watcher() -> FileWatcher:
    """Get or create the global file watcher instance."""
    global _watcher
    if _watcher is None:
        _watcher = FileWatcher()
    return _watcher


def start_watcher(paths: List[str] = None):
    """
    Start the file watcher with optional initial paths.
    
    Args:
        paths: List of directory paths to watch
    """
    watcher = get_watcher()
    
    if paths:
        for path in paths:
            watcher.add_path(path)
    
    watcher.start()


def stop_watcher():
    """Stop the file watcher."""
    watcher = get_watcher()
    watcher.stop()


def scan_directory(directory: str) -> int:
    """
    Perform initial scan of a directory to index all existing files.
    
    Args:
        directory: Absolute path to directory
        
    Returns:
        Number of files indexed
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        print(f"Invalid directory: {directory}")
        return 0
    
    indexed_count = 0
    
    print(f"Scanning directory: {directory}")
    
    for root, dirs, files in os.walk(directory):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        for filename in files:
            # Skip hidden and ignored files
            if filename.startswith('.') or filename in IGNORE_FILES:
                continue
            
            file_path = os.path.join(root, filename)
            
            # Check if supported file type
            if not doclingDocumentParser.is_supported_file(file_path):
                continue
            
            # Index the file
            try:
                if searchEngine.index_file_pipeline(file_path):
                    indexed_count += 1
            except Exception as e:
                print(f"Error indexing {file_path}: {e}")
    
    print(f"Scan complete: {indexed_count} files indexed")
    return indexed_count
