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
    session_service  # For conversation history
)

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
    print("FileGPT Backend - High-Performance Architecture")
    print("=" * 60)
    
    # Initialize metadata database with WAL mode
    metadata_db.init_db()
    
    # Initialize search indexes
    searchEngine.initialize_indexes()
    
    # Start background worker for async embedding/summarization
    from services import background_worker
    background_worker.start_worker()
    print("✓ Background worker started")
    
    # Use absolute path for testing (limited files for development)
    test_path = r"C:\Users\Mohammad\Desktop\test"
    
    print(f"\n📁 Test directory: {test_path}")
    
    # Create test directory if it doesn't exist
    if not os.path.exists(test_path):
        os.makedirs(test_path, exist_ok=True)
        print(f"  Created test directory: {test_path}")
        print(f"  Add test files (PDF, TXT, DOCX) to this directory")
    
    # Perform initial scan
    if os.path.exists(test_path):
        print(f"\n🔍 Scanning test directory...")
        indexed_count = file_watcher.scan_directory(test_path)
        print(f"✅ Indexed {indexed_count} files")
    
    # Start file watcher for real-time updates
    def run_watcher():
        watcher = file_watcher.get_watcher()
        if os.path.exists(test_path):
            watcher.add_path(test_path)
        watcher.start()
    
    watcher_thread = threading.Thread(target=run_watcher, daemon=True)
    watcher_thread.start()
    
    print("\n" + "=" * 60)
    print("🚀 FileGPT Backend Ready!")
    print("=" * 60)
    print(f"\nMonitoring: {test_path}")
    stats = metadata_db.get_stats()
    print(f"Database: {stats['total_files']} files, {stats['db_size_mb']:.2f} MB")
    print(f"Queue: {stats['pending_embedding']} pending embedding, {stats['pending_summary']} pending summary")
    print("=" * 60 + "\n")


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
    Supports SEARCH, ACTION, and CHAT intents.
    
    Args:
        request: Contains question and optional k (number of context chunks)
        
    Returns:
        AI-generated answer with source references and intent information
    """
    # Session management for conversation history
    session_mgr = session_service.get_session_manager()
    
    # Create new session if not provided
    if not request.session_id:
        session_id = session_mgr.create_session()
    else:
        session_id = request.session_id
    
    # Get conversation history
    conversation_history = session_mgr.get_history(session_id)
    
    # Route the query to determine intent
    route_result = router_service.route_query(request.query)
    intent = route_result.get("intent", "CHAT")
    parameters = route_result.get("parameters", {})
    
    print(f"Intent detected: {intent}")
    print(f"Parameters: {parameters}")
    
    # Handle SEARCH intent
    if intent == "SEARCH":
        search_query = parameters.get("query", request.query)
        
        # Get relevant context using hybrid search
        search_results = searchEngine.hybrid_search(search_query, k=request.k)
        
        if not search_results:
            return {
                "answer": "I couldn't find any relevant files to answer your question. Try adding more folders or indexing more files.",
                "sources": [],
                "intent": "SEARCH",
                "context_used": 0
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
        
        # EXTRACTION MODE: For code queries, bypass LLM to avoid hallucination
        code_keywords = ['code', 'function', 'implementation', 'algorithm', 'snippet', 'program', 'find', 'show']
        is_code_query = any(keyword in request.query.lower() for keyword in code_keywords)
        
        print(f"DEBUG: is_code_query={is_code_query}")
        
        if is_code_query:
            # Just return the actual code, no LLM generation
            print("✓ Using extraction mode")
            answer_parts = []
            for i, result in enumerate(search_results, 1):
                file_name = os.path.basename(result['source'])
                answer_parts.append(f"**{i}. {file_name}**\n")
                if result.get('summary'):
                    answer_parts.append(f"*{result['summary']}*\n")  
                answer_parts.append(f"```cpp\n{result['content']}\n```\n")
            
            answer = "\n".join(answer_parts)
            
            # Store in session
            session_mgr.add_message(session_id, "user", request.query)
            session_mgr.add_message(session_id, "assistant", answer)
            
            return {
                "answer": answer,
                "sources": sources,
                "intent": "SEARCH",
                "context_used": len(search_results),
                "session_id": session_id
            }
        
        # Build prompt for LLM with conversation history
        history_context = ""
        if conversation_history:
            history_context = "\nPrevious conversation:\n"
            for msg in conversation_history[-3:]:  # Last 3 exchanges for context
                history_context += f"{msg['role'].title()}: {msg['content']}\n"
            history_context += "\n"
        
        prompt = f"""You are a helpful AI assistant with access to the user's files. Answer the following question based on the provided context from their indexed files.
{history_context}
Question: {search_query}

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
            model_name = summary_service.get_available_model()
            response = ollama.chat(
                model=model_name,
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
            
            # **FIX**: If LLM says "no files" but we have sources, override with extraction mode
            no_result_phrases = ["couldn't find", "no relevant", "don't have", "no files", "no information"]
            llm_says_no_results = any(phrase in answer.lower() for phrase in no_result_phrases)
            
            if llm_says_no_results and sources:
                # LLM is wrong - we DO have results! Show them directly
                print("⚠️  LLM said no results but we have sources - using extraction mode")
                answer_parts = [f"Found {len(sources)} relevant files:\n\n"]
                for i, src in enumerate(sources, 1):
                    file_name = os.path.basename(src['path'])
                    answer_parts.append(f"**{i}. {file_name}**\n")
                    if src.get('summary'):
                        answer_parts.append(f"*{src['summary']}*\n")
                answer = "".join(answer_parts)
            
            # Store conversation in session
            session_mgr.add_message(session_id, "user", request.query)
            session_mgr.add_message(session_id, "assistant", answer)
            
            return {
                "answer": answer,
                "sources": sources,
                "intent": "SEARCH",
                "context_used": len(search_results),
                "session_id": session_id  # Return for frontend to track
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")
    
    # Handle ACTION intent
    elif intent == "ACTION":
        action = parameters.get("action", "unknown")
        target = parameters.get("target", "")
        details = parameters.get("details", "")
        
        try:
            # ===== CREATE_FOLDER =====
            if action == "create_folder":
                folder_path = target
                # Handle relative paths
                if not os.path.isabs(folder_path):
                    user_home = str(Path.home())
                    folder_path = os.path.join(user_home, "Desktop", folder_path)
                
                os.makedirs(folder_path, exist_ok=True)
                return {
                    "answer": f"✅ Successfully created folder: {folder_path}",
                    "sources": [],
                    "intent": "ACTION",
                    "action_executed": True,
                    "path": folder_path
                }
            
            # ===== DELETE (with safety check) =====
            elif action == "delete":
                if not os.path.exists(target):
                    return {
                        "answer": f"❌ Path not found: {target}",
                        "intent": "ACTION",
                        "action_executed": False
                    }
                
                # SAFETY: Require confirmation for destructive operations
                return {
                    "answer": f"⚠️ Delete requested: {target}\n\nFor safety, please confirm using /delete endpoint or frontend.",
                    "intent": "ACTION",
                    "action_executed": False,
                    "requires_confirmation": True,
                    "delete_target": target
                }
            
            # ===== ORGANIZE (AI-powered) =====
            elif action == "organize":
                return {
                    "answer": f"📁 Organization request detected: '{target}'\n\nUse the frontend's AI organization workflow for approval and execution.",
                    "intent": "ACTION",
                    "action_executed": False,
                    "suggestion": "use_frontend_organization",
                    "organization_query": target
                }
            
            # ===== MOVE/RENAME (require explicit parameters) =====
            elif action in ["move", "rename"]:
                return {
                    "answer": f"I understood you want to {action} something.\n\nPlease use the /{action} endpoint with explicit source and destination for safety.",
                    "intent": "ACTION",
                    "action_executed": False
                }
            
            # ===== UNKNOWN ACTION =====
            else:
                return {
                    "answer": f"I understood '{action}' on '{target}' but this action isn't yet supported via chat.\n\nSupported: create_folder, organize\nUse dedicated endpoints for: move, delete, rename",
                    "intent": "ACTION",
                    "action_executed": False,
                    "action_details": {"action": action, "target": target}
                }
                
        except Exception as e:
            return {
                "answer": f"❌ Error executing {action}: {str(e)}",
                "intent": "ACTION",
                "action_executed": False,
                "error": str(e)
            }
    
    # Handle CHAT intent
    else:
        # General conversation without file context
        prompt = f"""You are a helpful assistant. Answer the following question or respond to the message.

User: {request.query}

Respond helpfully and conversationally:"""
        
        try:
            model_name = summary_service.get_available_model()
            response = ollama.chat(
                model=model_name,
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
                "sources": [],
                "intent": "CHAT",
                "context_used": 0
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


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
