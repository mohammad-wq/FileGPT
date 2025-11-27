"""
Index Manager for FileGPT
Handles intelligent indexing: full scan on first run, incremental updates on subsequent runs.
"""

import os
import json
from pathlib import Path
from typing import Set, Dict
from datetime import datetime

from services import searchEngine, doclingDocumentParser


class IndexManager:
    """Manages file indexing state and performs intelligent scans."""
    
    def __init__(self, state_file: str = "index_state.json"):
        """
        Initialize index manager.
        
        Args:
            state_file: Path to store index state
        """
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load index state from disk."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading index state: {e}")
                return self._create_new_state()
        return self._create_new_state()
    
    def _create_new_state(self) -> Dict:
        """Create new index state."""
        return {
            "indexed_files": {},  # {file_path: last_modified_timestamp}
            "monitored_paths": [],
            "last_full_scan": None,
            "version": "1.0"
        }
    
    def _save_state(self):
        """Save index state to disk."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Error saving index state: {e}")
    
    def is_first_run(self) -> bool:
        """Check if this is the first run (no previous state)."""
        return self.state.get("last_full_scan") is None
    
    def should_index_file(self, file_path: str) -> bool:
        """
        Determine if a file should be indexed.
        
        Args:
            file_path: Absolute path to file
            
        Returns:
            True if file is new or modified since last index
        """
        if not os.path.exists(file_path):
            return False
        
        # Get current modification time
        try:
            current_mtime = os.path.getmtime(file_path)
        except Exception:
            return False
        
        # Check if file is in state
        indexed_files = self.state.get("indexed_files", {})
        
        if file_path not in indexed_files:
            # New file - should index
            return True
        
        # File exists in state - check if modified
        last_mtime = indexed_files[file_path]
        return current_mtime > last_mtime
    
    def mark_file_indexed(self, file_path: str):
        """
        Mark a file as indexed with current modification time.
        
        Args:
            file_path: Absolute path to file
        """
        try:
            mtime = os.path.getmtime(file_path)
            self.state["indexed_files"][file_path] = mtime
            self._save_state()
        except Exception as e:
            print(f"Error marking file indexed {file_path}: {e}")
    
    def remove_file_from_state(self, file_path: str):
        """
        Remove a file from indexed state.
        
        Args:
            file_path: Absolute path to file
        """
        if file_path in self.state["indexed_files"]:
            del self.state["indexed_files"][file_path]
            self._save_state()
    
    def smart_scan_directory(self, directory: str) -> Dict[str, int]:
        """
        Perform smart directory scan.
        - On first run: index all files
        - On subsequent runs: only index new/modified files
        
        Args:
            directory: Absolute path to directory
            
        Returns:
            Dict with stats: {"indexed": int, "skipped": int, "errors": int}
        """
        if not os.path.exists(directory) or not os.path.isdir(directory):
            print(f"Invalid directory: {directory}")
            return {"indexed": 0, "skipped": 0, "errors": 0}
        
        stats = {"indexed": 0, "skipped": 0, "errors": 0}
        is_first_run = self.is_first_run()
        
        if is_first_run:
            print(f"🔍 First run detected - performing full scan of: {directory}")
        else:
            print(f"🔄 Incremental scan of: {directory}")
        
        # Ignore patterns
        IGNORE_DIRS = {
            '.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env',
            'dist', 'build', '.cache', '.pytest_cache', '.mypy_cache',
            '.idea', '.vscode', '.vs', 'bin', 'obj', 'target'
        }
        
        IGNORE_FILES = {
            '.DS_Store', 'Thumbs.db', '.gitignore', '.gitattributes'
        }
        
        for root, dirs, files in os.walk(directory):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
            
            for filename in files:
                # Skip hidden and ignored files
                if filename.startswith('.') or filename in IGNORE_FILES:
                    stats["skipped"] += 1
                    continue
                
                file_path = os.path.join(root, filename)
                
                # Check if supported file type
                if not doclingDocumentParser.is_supported_file(file_path):
                    stats["skipped"] += 1
                    continue
                
                # Smart decision: should we index this file?
                if not is_first_run and not self.should_index_file(file_path):
                    stats["skipped"] += 1
                    print(f"⏭️  Skipping (already indexed): {filename}")
                    continue
                
                # Index the file
                try:
                    print(f"📄 Indexing: {filename}")
                    if searchEngine.index_file_pipeline(file_path):
                        self.mark_file_indexed(file_path)
                        stats["indexed"] += 1
                except Exception as e:
                    print(f"❌ Error indexing {file_path}: {e}")
                    stats["errors"] += 1
        
        # Update state
        if directory not in self.state["monitored_paths"]:
            self.state["monitored_paths"].append(directory)
        
        self.state["last_full_scan"] = datetime.now().isoformat()
        self._save_state()
        
        print(f"✅ Scan complete: {stats['indexed']} indexed, {stats['skipped']} skipped, {stats['errors']} errors")
        return stats
    
    def cleanup_deleted_files(self):
        """Remove deleted files from index state."""
        indexed_files = self.state.get("indexed_files", {})
        deleted_files = []
        
        for file_path in list(indexed_files.keys()):
            if not os.path.exists(file_path):
                deleted_files.append(file_path)
                searchEngine.delete_file_from_index(file_path)
                del indexed_files[file_path]
        
        if deleted_files:
            print(f"🗑️  Removed {len(deleted_files)} deleted files from index")
            self._save_state()


# Global index manager instance
_index_manager: IndexManager = None


def get_index_manager() -> IndexManager:
    """Get or create the global index manager instance."""
    global _index_manager
    if _index_manager is None:
        _index_manager = IndexManager()
    return _index_manager
