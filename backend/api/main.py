"""
FastAPI Application for FileGPT
REST API server with file management, search, and AI chat capabilities.
"""

import os
import shutil
import threading
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ollama

# Import services
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services import searchEngine, file_watcher, metadata_db, categorization_service


# Pydantic models for request/response
class AddFolderRequest(BaseModel):
    path: str

class SearchRequest(BaseModel):
    query: str
    k: Optional[int] = 5

class AskRequest(BaseModel):
    query: str
    k: Optional[int] = 5

class CreateFolderRequest(BaseModel):
    path: str

class RenameRequest(BaseModel):
    old_path: str
    new_path: str

class MoveRequest(BaseModel):
    source: str
    destination: str

class DeleteRequest(BaseModel):
    path: str

class ListRequest(BaseModel):
    path: str

class CategorizeRequest(BaseModel):
    category_description: str
    search_path: Optional[str] = None
    max_files: Optional[int] = 100

class OrganizeRequest(BaseModel):
    category_description: str
    destination_folder: str
    search_path: Optional[str] = None
    min_confidence: Optional[float] = 0.6
    dry_run: Optional[bool] = False

class SuggestCategoriesRequest(BaseModel):
    file_paths: List[str]


# Initialize FastAPI app
app = FastAPI(
    title="FileGPT Backend",
    description="Local AI-powered file search and management system",
    version="1.0.0"
)

# CORS middleware - allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("=" * 60)
    print("FileGPT Backend Starting...")
    print("=" * 60)
    
    # Initialize metadata database
    metadata_db.init_db()
    print("✓ Metadata database initialized")
    
    # Initialize search indexes
    searchEngine.initialize_indexes()
    print("✓ Search indexes loaded")
    
    # Start file watcher in background thread
    watcher_thread = threading.Thread(target=file_watcher.start_watcher, daemon=True)
    watcher_thread.start()
    print("✓ File watcher started")
    
    # Auto-index common user directories (PC-wide monitoring)
    user_home = str(Path.home())
    default_paths = [
        os.path.join(user_home, "Documents"),
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Downloads"),
    ]
    
    print("\n📁 Auto-monitoring common directories:")
    for path in default_paths:
        if os.path.exists(path):
            watcher = file_watcher.get_watcher()
            watcher.add_path(path)
            print(f"  • {path}")
    
    print("\n" + "=" * 60)
    print("🚀 FileGPT Backend Ready!")
    print("=" * 60)


@app.get("/")
async def root():
    """Health check endpoint."""
    stats = searchEngine.get_index_stats()
    return {
        "status": "online",
        "service": "FileGPT Backend",
        "version": "1.0.0",
        "stats": stats
    }


@app.post("/add_folder")
async def add_folder(request: AddFolderRequest):
    """
    Add a folder to the watch list and perform initial scan.
    
    Args:
        request: Contains path to folder
        
    Returns:
        Status and number of files indexed
    """
    folder_path = request.path
    
    # Validate path
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail=f"Path does not exist: {folder_path}")
    
    if not os.path.isdir(folder_path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {folder_path}")
    
    # Add to watcher
    watcher = file_watcher.get_watcher()
    success = watcher.add_path(folder_path)
    
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to add watcher for: {folder_path}")
    
    # Perform initial scan
    indexed_count = file_watcher.scan_directory(folder_path)
    
    return {
        "status": "success",
        "path": folder_path,
        "files_indexed": indexed_count,
        "message": f"Folder added and {indexed_count} files indexed"
    }


@app.post("/search")
async def search(request: SearchRequest):
    """
    Search for files using hybrid RAG (semantic + keyword).
    
    Args:
        request: Contains search query and optional k (number of results)
        
    Returns:
        List of search results with content, source, and summary
    """
    results = searchEngine.hybrid_search(request.query, k=request.k)
    
    return {
        "query": request.query,
        "results": results,
        "count": len(results)
    }


@app.post("/ask")
async def ask(request: AskRequest):
    """
    Ask a question and get AI-generated answer with context from indexed files.
    
    Args:
        request: Contains question and optional k (number of context chunks)
        
    Returns:
        AI-generated answer with source references
    """
    # Get relevant context using hybrid search
    search_results = searchEngine.hybrid_search(request.query, k=request.k)
    
    if not search_results:
        return {
            "answer": "I couldn't find any relevant files to answer your question. Try adding more folders or indexing more files.",
            "sources": []
        }
    
    # Build context string from search results
    context_parts = []
    sources = []
    
    for i, result in enumerate(search_results):
        context_parts.append(f"--- Source {i+1}: {result['source']} ---")
        if result.get('summary'):
            context_parts.append(f"Summary: {result['summary']}")
        context_parts.append(f"Content: {result['content']}")
        context_parts.append("")
        
        sources.append({
            "path": result['source'],
            "summary": result.get('summary', ''),
            "relevance_score": result.get('score', 0)
        })
    
    context = "\n".join(context_parts)
    
    # Build prompt for LLM
    prompt = f"""You are a helpful AI assistant with access to the user's files. Answer the following question based on the provided context from their indexed files.

Question: {request.query}

Context from files:
{context}

Instructions:
1. Answer the question using information from the context
2. Be specific and cite which files you're referencing
3. If the context doesn't contain enough information, say so
4. Keep your answer concise and helpful

Answer:"""
    
    try:
        # Call Ollama for answer generation
        response = ollama.chat(
            model="llama3:8b",
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            options={
                'temperature': 0.7,
                'num_predict': 500,
            }
        )
        
        answer = response['message']['content'].strip()
        
        return {
            "answer": answer,
            "sources": sources,
            "context_used": len(search_results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")


@app.post("/create_folder")
async def create_folder(request: CreateFolderRequest):
    """
    Create a new folder.
    
    Args:
        request: Contains path for new folder
        
    Returns:
        Success status
    """
    try:
        os.makedirs(request.path, exist_ok=True)
        return {
            "status": "success",
            "path": request.path,
            "message": "Folder created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating folder: {str(e)}")


@app.post("/rename")
async def rename(request: RenameRequest):
    """
    Rename a file or folder.
    
    Args:
        request: Contains old_path and new_path
        
    Returns:
        Success status
    """
    if not os.path.exists(request.old_path):
        raise HTTPException(status_code=404, detail=f"Path does not exist: {request.old_path}")
    
    try:
        os.rename(request.old_path, request.new_path)
        
        # Update index if it's a file
        if os.path.isfile(request.new_path):
            searchEngine.delete_file_from_index(request.old_path)
            searchEngine.index_file_pipeline(request.new_path)
        
        return {
            "status": "success",
            "old_path": request.old_path,
            "new_path": request.new_path,
            "message": "Renamed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error renaming: {str(e)}")


@app.post("/move")
async def move(request: MoveRequest):
    """
    Move a file or folder.
    
    Args:
        request: Contains source and destination paths
        
    Returns:
        Success status
    """
    if not os.path.exists(request.source):
        raise HTTPException(status_code=404, detail=f"Source does not exist: {request.source}")
    
    try:
        shutil.move(request.source, request.destination)
        
        # Update index if it's a file
        if os.path.isfile(request.destination):
            searchEngine.delete_file_from_index(request.source)
            searchEngine.index_file_pipeline(request.destination)
        
        return {
            "status": "success",
            "source": request.source,
            "destination": request.destination,
            "message": "Moved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error moving: {str(e)}")


@app.delete("/delete")
async def delete(request: DeleteRequest):
    """
    Delete a file or folder.
    
    Args:
        request: Contains path to delete
        
    Returns:
        Success status
    """
    if not os.path.exists(request.path):
        raise HTTPException(status_code=404, detail=f"Path does not exist: {request.path}")
    
    try:
        if os.path.isfile(request.path):
            os.remove(request.path)
            searchEngine.delete_file_from_index(request.path)
        elif os.path.isdir(request.path):
            shutil.rmtree(request.path)
        
        return {
            "status": "success",
            "path": request.path,
            "message": "Deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting: {str(e)}")


@app.post("/list")
async def list_directory(request: ListRequest):
    """
    List contents of a directory.
    
    Args:
        request: Contains directory path
        
    Returns:
        List of files and folders with metadata
    """
    if not os.path.exists(request.path):
        raise HTTPException(status_code=404, detail=f"Path does not exist: {request.path}")
    
    if not os.path.isdir(request.path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.path}")
    
    try:
        items = []
        for item_name in os.listdir(request.path):
            item_path = os.path.join(request.path, item_name)
            
            item_info = {
                "name": item_name,
                "path": item_path,
                "is_directory": os.path.isdir(item_path),
                "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0,
            }
            
            # Add summary if file is indexed
            if os.path.isfile(item_path):
                summary = metadata_db.get_summary(item_path)
                if summary:
                    item_info["summary"] = summary
            
            items.append(item_info)
        
        return {
            "path": request.path,
            "items": items,
            "count": len(items)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing directory: {str(e)}")


@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    return searchEngine.get_index_stats()


@app.get("/watched_folders")
async def get_watched_folders():
    """Get list of folders being monitored."""
    watcher = file_watcher.get_watcher()
    return {
        "folders": watcher.get_watched_paths()
    }


# ============================================================================
# AI CATEGORIZATION ENDPOINTS
# ============================================================================

@app.post("/categorize")
async def categorize(request: CategorizeRequest):
    """
    Find files matching a category description using AI.
    
    Example: "sorting algorithms" will find all files related to sorting
    
    Args:
        request: Contains category_description, optional search_path and max_files
        
    Returns:
        List of files that match the category with confidence scores
    """
    result = categorization_service.categorize_files(
        category_description=request.category_description,
        search_path=request.search_path,
        max_files=request.max_files
    )
    
    return result


@app.post("/organize")
async def organize(request: OrganizeRequest):
    """
    Automatically organize files into a folder based on category description.
    
    Example: "Put all sorting algorithms into C:\\\\SortingAlgorithms"
    
    Args:
        request: Contains category_description, destination_folder, and options
        
    Returns:
        Results of the organization operation including files moved
    """
    result = categorization_service.auto_organize_by_category(
        category_description=request.category_description,
        destination_folder=request.destination_folder,
        search_path=request.search_path,
        min_confidence=request.min_confidence,
        dry_run=request.dry_run
    )
    
    return result


@app.post("/suggest_categories")
async def suggest_categories(request: SuggestCategoriesRequest):
    """
    Get AI-suggested categories for organizing a list of files.
    
    Args:
        request: Contains list of file paths
        
    Returns:
        List of suggested categories with descriptions
    """
    suggestions = categorization_service.suggest_categories(request.file_paths)
    
    return {
        "suggestions": suggestions,
        "count": len(suggestions)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")