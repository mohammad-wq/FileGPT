"""
File Watcher Service for FileGPT
Real-time file system monitoring with automatic indexing.
"""

import os
import time
import subprocess
import sys
import platform
import threading
from typing import List, Set, Optional
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from services import searchEngine, fileParser
from config import get_logger

logger = get_logger("file_watcher")


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
        if not fileParser.is_supported_file(file_path):
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
            logger.info(f"New file detected: {file_path}")
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
            logger.info(f"File modified: {file_path}")
            searchEngine.index_file_pipeline(file_path)
        finally:
            self._processing.discard(file_path)
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        logger.info(f"File deleted: {file_path}")
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
            logger.info(f"Now watching: {path}")
            return True
        except Exception as e:
            logger.error(f"Error adding watch path {path}: {e}")
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


class RustMonitorManager:
    """Manages the external Rust-based Linux monitor."""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.binary_path = self._find_binary()
        
    def _find_binary(self) -> str:
        """Locate the linux_monitor binary."""
        # Try absolute path first
        base_dir = Path("/home/zakwanalam07/FileGPT")
        
        paths = [
            base_dir / "linux_monitor" / "target" / "release" / "linux_monitor",
            Path(__file__).parent.parent.parent / "linux_monitor" / "target" / "release" / "linux_monitor",
            Path("/usr/local/bin/linux_monitor")
        ]
        
        for p in paths:
            if p.exists() and os.access(p, os.X_OK):
                return str(p)
        return ""

    def start(self, watch_paths: List[str], backend_url: str = "http://127.0.0.1:8000"):
        """Start the Rust monitor subprocess."""
        if not self.binary_path:
            logger.warning("Rust monitor binary not found. Skipping.")
            return False
            
        if self.is_running:
            return True

        if not watch_paths:
            logger.warning("No watch paths provided for Rust monitor.")
            return False

        # Prepare arguments
        cmd = [self.binary_path, "--backend-url", backend_url]
        for p in watch_paths:
            cmd.extend(["--watch", p])
            
        try:
            logger.info(f"🚀 Starting Rust monitor: {self.binary_path}")
            # Use PIPE to capture output if needed, but for now just let it run
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Start a thread to log output
            def log_output():
                if not self.process or not self.process.stdout:
                    return
                for line in self.process.stdout:
                    logger.info(f"[Rust] {line.strip()}")
            
            self.monitor_thread = threading.Thread(target=log_output, daemon=True)
            self.monitor_thread.start()
            
            self.is_running = True
            return True
        except Exception as e:
            logger.error(f"Failed to start Rust monitor: {e}")
            return False

    def stop(self):
        """Stop the Rust monitor subprocess."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.is_running = False
            print("Rust monitor stopped")


# Global watcher instances
_watcher: FileWatcher = None
_rust_manager: RustMonitorManager = None


def get_watcher() -> FileWatcher:
    """Get or create the global file watcher instance."""
    global _watcher
    if _watcher is None:
        _watcher = FileWatcher()
    return _watcher


def get_rust_manager() -> RustMonitorManager:
    """Get or create the global Rust monitor manager."""
    global _rust_manager
    if _rust_manager is None:
        _rust_manager = RustMonitorManager()
    return _rust_manager


def start_watcher(paths: List[str] = None, backend_url: str = "http://127.0.0.1:8000"):
    """
    Start the file watcher with optional initial paths.
    Uses Rust monitor on Linux for better performance.
    
    Args:
        paths: List of directory paths to watch
        backend_url: URL of this backend for the Rust monitor to POST to
    """
    # 1. Start Rust monitor on Linux
    if platform.system() == "Linux":
        rust_mgr = get_rust_manager()
        # Fallback to current directory or home if no paths
        watch_paths = paths if paths else [os.path.expanduser("~")]
        if rust_mgr.start(watch_paths, backend_url):
            print("✓ High-performance Rust monitor active")
            # We still might want the Python watcher for specific cases or as fallback,
            # but let's stick to Rust on Linux for these paths.
            return

    # 2. Fallback to Python Watchdog (standard or non-Linux)
    watcher = get_watcher()
    if paths:
        for path in paths:
            watcher.add_path(path)
    watcher.start()


def stop_watcher():
    """Stop both Python and Rust file watchers."""
    watcher = get_watcher()
    watcher.stop()
    
    rust_mgr = get_rust_manager()
    rust_mgr.stop()


def scan_directory(directory: str) -> int:
    """
    Perform initial scan of a directory to index all existing files.
    
    Args:
        directory: Absolute path to directory
        
    Returns:
        Number of files indexed
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        logger.error(f"Invalid directory: {directory}")
        return 0
    
    indexed_count = 0
    
    logger.info(f"Scanning directory: {directory}")
    
    for root, dirs, files in os.walk(directory):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        for filename in files:
            # Skip hidden and ignored files
            if filename.startswith('.') or filename in IGNORE_FILES:
                continue
            
            file_path = os.path.join(root, filename)
            
            # Check if supported file type
            if not fileParser.is_supported_file(file_path):
                continue
            
            # Index the file
            try:
                if searchEngine.index_file_pipeline(file_path):
                    indexed_count += 1
            except Exception as e:
                logger.error(f"Error indexing {file_path}: {e}")
    
    logger.info(f"Scan complete: {indexed_count} files indexed")
    return indexed_count
