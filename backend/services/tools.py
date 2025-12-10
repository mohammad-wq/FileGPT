"""
LangChain Tools for FileGPT Agent
Defines executable tools that the agent can use to interact with the file system.
"""

import os
import shutil
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

# Import existing services
from services import searchEngine, fileParser


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@tool
def search_files(query: str, k: int = 5):
    """
    Search for files using hybrid RAG (semantic + keyword search).

    Important: return raw results from `searchEngine.hybrid_search` without any
    second-pass filtering or LLM-driven re-ranking. This reduces reliance on
    small local models and avoids hallucination in filtering.

    Args:
        query: The search query (what to look for)
        k: Number of results to return (default: 5)

    Returns:
        List[Dict]: Raw result dictionaries coming from the hybrid search engine.
    """
    try:
        results = searchEngine.hybrid_search(query, k=k)
        if not results:
            return []
        return results
    except Exception as e:
        # Return an empty list on error to keep callers simple and avoid
        # forcing them to parse error strings.
        return []





@tool
def read_file(file_path: str) -> str:
    """
    Read the complete content of a specific file.
    
    Use this tool when the user wants to:
    - View the full content of a file
    - Read a specific document or code file
    - Get detailed information from a known file
    
    Args:
        file_path: Absolute path to the file to read
    
    Returns:
        File content as string, limited to 8000 characters to prevent context overflow
    """
    try:
        # Validate path
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"
        
        if not os.path.isfile(file_path):
            return f"Error: Path is not a file: {file_path}"
        
        # Read content using existing parser
        content = fileParser.get_file_content(file_path)
        
        if content is None:
            return f"Error: Unable to read file or unsupported file type: {file_path}"
        
        # Limit content to prevent context overflow
        max_chars = 8000
        if len(content) > max_chars:
            truncated_content = content[:max_chars]
            return f"File: {file_path}\nSize: {len(content)} characters (showing first {max_chars})\n\n{truncated_content}\n\n[Content truncated - file is too large]"
        
        return f"File: {file_path}\nSize: {len(content)} characters\n\n{content}"
        
    except PermissionError:
        return f"Error: Permission denied reading file: {file_path}"
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"


@tool
def list_directory(path: str) -> str:
    """
    List all files and subdirectories in a directory.
    
    Use this tool when the user wants to:
    - See what files are in a folder
    - Browse directory contents
    - Explore the file system structure
    
    Args:
        path: Absolute path to the directory to list
    
    Returns:
        Formatted string with directory contents
    """
    try:
        # Validate path
        if not os.path.exists(path):
            return f"Error: Directory not found: {path}"
        
        if not os.path.isdir(path):
            return f"Error: Path is not a directory: {path}"
        
        # List contents
        items = os.listdir(path)
        
        if not items:
            return f"Directory is empty: {path}"
        
        # Separate files and directories
        files = []
        directories = []
        
        for item in sorted(items):
            item_path = os.path.join(path, item)
            try:
                if os.path.isdir(item_path):
                    directories.append(item)
                else:
                    # Get file size
                    size = os.path.getsize(item_path)
                    size_str = _format_size(size)
                    files.append(f"{item} ({size_str})")
            except (PermissionError, OSError):
                # Skip items we can't access
                continue
        
        # Format output
        output_parts = [f"Contents of: {path}\n"]
        
        if directories:
            output_parts.append(f"\nDirectories ({len(directories)}):")
            for directory in directories:
                output_parts.append(f"  📁 {directory}/")
        
        if files:
            output_parts.append(f"\nFiles ({len(files)}):")
            for file in files:
                output_parts.append(f"  📄 {file}")
        
        output_parts.append(f"\nTotal: {len(directories)} directories, {len(files)} files")
        
        return "\n".join(output_parts)
        
    except PermissionError:
        return f"Error: Permission denied accessing directory: {path}"
    except Exception as e:
        return f"Error listing directory {path}: {str(e)}"


@tool
def move_file(source: str, destination: str) -> str:
    """
    Move or rename a file or directory.
    
    Use this tool when the user wants to:
    - Move files to a different location
    - Rename files or folders
    - Reorganize file system
    
    Args:
        source: Absolute path to the file/directory to move
        destination: Absolute path to the new location
    
    Returns:
        Success or error message
    """
    try:
        # Validate source
        if not os.path.exists(source):
            return f"Error: Source not found: {source}"
        
        # Check if destination already exists
        if os.path.exists(destination):
            return f"Error: Destination already exists: {destination}\nPlease choose a different destination or delete the existing file first."
        
        # Ensure destination directory exists
        dest_dir = os.path.dirname(destination)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        
        # Perform move
        shutil.move(source, destination)
        
        return f"✅ Successfully moved:\n  From: {source}\n  To: {destination}"
        
    except PermissionError:
        return f"Error: Permission denied. Cannot move from {source} to {destination}"
    except Exception as e:
        return f"Error moving file: {str(e)}"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


# ============================================================================
# TOOL REGISTRY AND METADATA
# ============================================================================

# List of all available tools for the agent
AVAILABLE_TOOLS = [
    search_files,
    read_file,
    list_directory,
    move_file
]

# Tool descriptions for system prompt (helps LLM choose the right tool)
TOOL_DESCRIPTIONS = """
You have access to the following tools to help users with their file management tasks:

1. **search_files**: Search for files using semantic and keyword search
   - Use when: User wants to find files by content, name, or topic
   - Examples: "find python files", "search for documents about AI", "locate my resume"

2. **read_file**: Read the complete content of a specific file
   - Use when: User wants to view or analyze a specific file's content
   - Examples: "read example.txt", "show me the content of report.pdf"
   - Note: Requires the exact file path

3. **list_directory**: List all files and folders in a directory
   - Use when: User wants to see what's in a folder
   - Examples: "list files in C:\\Documents", "show me what's in this folder"

4. **move_file**: Move or rename files and directories
   - Use when: User wants to relocate or rename items
   - Examples: "move file.txt to Documents", "rename old.txt to new.txt"
   - ⚠️ Use with caution: This modifies the file system

**Important Guidelines:**
- For general questions not requiring file operations, respond directly without using tools
- Always use absolute paths when referencing files
- If a tool returns an error, explain it clearly to the user
- For destructive operations (move/delete), confirm the action was successful
"""

# Metadata for each tool (useful for logging and debugging)
TOOL_METADATA = {
    "search_files": {
        "category": "retrieval",
        "risk_level": "safe",
        "description": "Hybrid RAG search across indexed files"
    },
    "read_file": {
        "category": "read",
        "risk_level": "safe",
        "description": "Read file content with format-specific parsing"
    },
    "list_directory": {
        "category": "read",
        "risk_level": "safe",
        "description": "List directory contents with size information"
    },
    "move_file": {
        "category": "write",
        "risk_level": "moderate",
        "description": "Move or rename files and directories"
    }
}


# ============================================================================
# UTILITY FUNCTIONS FOR AGENT SERVICE
# ============================================================================

def get_tool_by_name(tool_name: str) -> Optional[Any]:
    """Get a tool by its name."""
    for tool in AVAILABLE_TOOLS:
        if tool.name == tool_name:
            return tool
    return None


def get_safe_tools() -> List[Any]:
    """Get only safe (non-destructive) tools."""
    return [
        tool for tool in AVAILABLE_TOOLS 
        if TOOL_METADATA.get(tool.name, {}).get("risk_level") == "safe"
    ]


def get_all_tool_names() -> List[str]:
    """Get names of all available tools."""
    return [tool.name for tool in AVAILABLE_TOOLS]
