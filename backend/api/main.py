"""
FastAPI Application for FileGPT
REST API server with file management, search, and AI chat capabilities.
"""

import os
import sys
import shutil
import threading
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import ollama
import asyncio

# Setup configuration and logging first
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import get_logger, SessionConfig

logger = get_logger("main")

# Add services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))
sys.path.insert(0, os.path.dirname(__file__))

# Import all backend services
from services import (
    searchEngine, 
    metadata_db, 
    file_watcher,
    fileParser,
    router_service,
    summary_service,
    background_worker,
    session_service,
    rag_workflow,
    ollama_monitor,
    rate_limiter,
    agent_service  # NEW: ReAct agent service
)

# Import storage backends based on config
if SessionConfig.STORAGE_MODE == "sqlite":
    from services import session_storage
    session_backend = session_storage
    logger.info("Using SQLite session storage")
else:
    session_backend = session_service
    logger.info("Using in-memory session storage")

try:
    from services import categorization_service
except ImportError:
    categorization_service = None  # Optional service

# Request schemas
class SearchRequest(BaseModel):
    query: str
    k: Optional[int] = 5

class AskRequest(BaseModel):
    query: str
    k: Optional[int] = 5
    session_id: Optional[str] = None  # For conversation history

class AddFolderRequest(BaseModel):
    path: str

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
# NOTE: Add CORS first, then other middleware (order matters)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware after CORS
app.add_middleware(rate_limiter.RateLimitMiddleware)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("FileGPT Backend - High-Performance Architecture")

    # Initialize metadata database with WAL mode
    metadata_db.init_db()

    # Initialize search indexes
    searchEngine.initialize_indexes()

    # Start background worker for async embedding/summarization
    from services import background_worker
    background_worker.start_worker()
    logger.info("Background worker started")

    # Start Ollama health monitor
    ollama_monitor.start_health_checker()
    logger.info("Ollama health monitor started")

    # Start session cleanup scheduler if using SQLite
    if SessionConfig.STORAGE_MODE == "sqlite":
        from services import session_storage
        session_storage.start_cleanup_scheduler()
        logger.info("Session storage cleanup scheduler started")
    
    # Use absolute path for testing (limited files for development)
    test_path = r"C:\Users\Mohammad\Desktop\test"
    
    logger.info(f"Test directory: {test_path}")
    
    # Create test directory if it doesn't exist
    if not os.path.exists(test_path):
        os.makedirs(test_path, exist_ok=True)
        logger.info(f"  Created test directory: {test_path}")
        logger.info(f"  Add test files (PDF, TXT, DOCX) to this directory")
    
    # Perform initial scan
    if os.path.exists(test_path):
        logger.info("Scanning test directory...")
        indexed_count = file_watcher.scan_directory(test_path)
        logger.info(f"Indexed {indexed_count} files")
    
    # Start file watcher for real-time updates
    def run_watcher():
        watcher = file_watcher.get_watcher()
        if os.path.exists(test_path):
            watcher.add_path(test_path)
        watcher.start()
    
    watcher_thread = threading.Thread(target=run_watcher, daemon=True)
    watcher_thread.start()
    
    logger.info("="*60)
    logger.info("FileGPT Backend Ready")
    logger.info("="*60)
    logger.info(f"Monitoring: {test_path}")
    stats = metadata_db.get_stats()
    logger.info(f"Database: {stats['total_files']} files, {stats['db_size_mb']:.2f} MB")
    logger.info(f"Queue: {stats['pending_embedding']} pending embedding, {stats['pending_summary']} pending summary")
    logger.info("="*60)


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


@app.get("/health")
async def health_check():
    """Detailed health check with dependency status."""
    ollama_status = ollama_monitor.get_monitor().get_status()
    
    if SessionConfig.STORAGE_MODE == "sqlite":
        session_stats = session_storage.get_persistent_storage().get_stats()
    else:
        session_stats = {"mode": "in-memory"}
    
    rate_limit_stats = rate_limiter.get_rate_limit_stats()
    
    return {
        "status": "healthy",
        "dependencies": {
            "ollama": ollama_status,
            "session_storage": session_stats,
            "rate_limiting": rate_limit_stats,
            "search_engine": searchEngine.get_index_stats()
        },
        "timestamp": __import__('time').time()
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
    from starlette.concurrency import run_in_threadpool
    
    # Run heavy search operation in threadpool to avoid blocking main loop
    results = await run_in_threadpool(searchEngine.hybrid_search, request.query, k=request.k)
    
    return {
        "query": request.query,
        "results": results,
        "count": len(results)
    }




@app.post("/ask")
async def ask(request: AskRequest):
    """
    Ask a question and get AI-generated answer using ReAct Agent with LangGraph.
    
    The agent can:
    - Search for files using hybrid RAG
    - Read file contents
    - List directory contents
    - Move/rename files
    - Have natural conversations
    
    Args:
        request: Contains question and optional k (number of context chunks)
        
    Returns:
        AI-generated answer with source references and tool usage information
    """
    from starlette.concurrency import run_in_threadpool
    
    # Check Ollama availability
    if not ollama_monitor.is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama service is unavailable. Try again later."
        )
    
    # Use session backend (SQLite or in-memory)
    if SessionConfig.STORAGE_MODE == "sqlite":
        session_mgr = session_storage.get_persistent_storage()
    else:
        session_mgr = session_service.get_session_manager()
    
    # Create new session if not provided
    if not request.session_id:
        session_id = session_mgr.create_session()
    else:
        session_id = request.session_id
    
    # Get conversation history
    conversation_history = session_mgr.get_history(session_id)
    
    try:
        # Run the Agent pipeline in threadpool to prevent blocking
        logger.info(f"Processing query with agent: {request.query}")
        
        result = await run_in_threadpool(
            agent_service.run_agent_pipeline,
            user_query=request.query,
            session_history=conversation_history
        )
        
        # Record Ollama success
        ollama_monitor.record_ollama_success()
        
        # Extract answer and metadata
        answer = result.get("answer", "")
        tool_used = result.get("tool_used", "none")
        sources = result.get("sources", [])
        tool_calls = result.get("tool_calls", 0)
        intent = result.get("intent", "AGENT")
        
        # Store conversation in session
        session_mgr.add_message(session_id, "user", request.query)
        session_mgr.add_message(session_id, "assistant", answer)
        
        # Log agent activity
        logger.info(f"Agent completed: tool_used={tool_used}, tool_calls={tool_calls}, intent={intent}")
        
        # Return response with backward compatibility
        return {
            "answer": answer,
            "sources": sources,
            "intent": intent,
            "tool_used": tool_used,
            "tool_calls": tool_calls,
            "context_used": len(sources),
            "session_id": session_id,
            "agent_type": "router_v1"  # Indicate this is the robust router
        }
        
    except Exception as e:
        logger.error(f"Error in agent pipeline: {e}", exc_info=True)
        
        # Record Ollama failure
        ollama_monitor.record_ollama_failure()
        
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing query with agent: {str(e)}"
        )


@app.post("/ask_rag")
async def ask_rag(request: AskRequest):
    """
    Ask a question using Self-Correcting RAG with LangGraph.
    Implements Retrieve → Grade → Decide → [Transform → Retrieve] → Generate loop.
    
    This endpoint provides:
    - Document relevance filtering (removes semantic drift)
    - Automatic query rewriting when no relevant docs found
    - LLM-based document grading for hallucination reduction
    
    Args:
        request: Contains question and optional k (number of initial documents to retrieve)
        
    Returns:
        AI-generated answer with sources, grading statistics, and workflow metrics
    """
    # Check Ollama availability
    if not ollama_monitor.is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama service is unavailable. Try again later."
        )
    
    # Use session backend (SQLite or in-memory)
    if SessionConfig.STORAGE_MODE == "sqlite":
        session_mgr = session_storage.get_persistent_storage()
    else:
        session_mgr = session_service.get_session_manager()
    
    # Create new session if not provided
    if not request.session_id:
        session_id = session_mgr.create_session()
    else:
        session_id = request.session_id
    
    try:
        # Run Self-Correcting RAG workflow
        rag_result = rag_workflow.run_rag_workflow_sync(
            query=request.query,
            k=request.k
        )
        
        # Record success
        ollama_monitor.record_ollama_success()
        
        # Store conversation in session
        session_mgr.add_message(session_id, "user", request.query)
        session_mgr.add_message(session_id, "assistant", rag_result["answer"])
        
        # Extract grading stats (stored inside generation_result)
        grading_stats = rag_result.get("grading_stats", {
            "retrieved": 0,
            "graded": 0,
            "attempts": 0
        })
        
        # Return response with grading statistics
        return {
            "answer": rag_result.get("answer", ""),
            "sources": rag_result.get("sources", []),
            "results": rag_result.get("results", []),
            "query": request.query,
            "count": len(rag_result.get("sources", [])),
            "session_id": session_id,
            "grading_stats": grading_stats,
            "workflow_status": "completed"
        }
        
    except Exception as e:
        logger.error(f"RAG workflow error: {str(e)}", exc_info=True)
        ollama_monitor.record_ollama_failure()
        raise HTTPException(status_code=500, detail=f"RAG workflow error: {str(e)}")


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


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """
    WebSocket endpoint for real-time file watcher logs.
    """
    await websocket.accept()
    
    # Create a queue for this connection
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    
    # Subscribe to broadcaster
    broadcaster = file_watcher.get_broadcaster()
    broadcaster.subscribe(queue, loop)
    
    try:
        while True:
            # Wait for message
            message = await queue.get()
            
            # Send to client
            await websocket.send_text(message)
            
    except WebSocketDisconnect:
        broadcaster.unsubscribe(queue)
    except Exception as e:
        print(f"WebSocket error: {e}")
        broadcaster.unsubscribe(queue)



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
    if not categorization_service:
        raise HTTPException(status_code=501, detail="Categorization service not available")
    
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
    if not categorization_service:
        raise HTTPException(status_code=501, detail="Categorization service not available")
    
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
    if not categorization_service:
        raise HTTPException(status_code=501, detail="Categorization service not available")
    
    suggestions = categorization_service.suggest_categories(request.file_paths)
    
    return {
        "suggestions": suggestions,
        "count": len(suggestions)
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
