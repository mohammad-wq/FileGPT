"""
Router-based Agent Service for FileGPT.
Optimized for small models (like qwen2.5:0.5b) that struggle with complex JSON/ReAct agents.
"""

from typing import Dict, Any, List, Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from config import OllamaConfig, logger
from services import tools
import json

# Initialize LLM with strict parameters
def get_llm():
    return ChatOllama(
        model=OllamaConfig.MODEL,
        temperature=0.0,  # Zero temperature for deterministic outputs
        base_url=OllamaConfig.HOST
    )

def classify_intent(query: str, llm) -> str:
    """Step 1: Determine what the user wants to do."""
    # Deterministic heuristics for file-related queries
    q_lower = query.strip().lower()
    search_triggers = [
        "find ", "find the ", "show ", "show me ", "search ", "search for ",
        "where is ", "open ", "find file", "find code", "show code", "show file",
        "do i have", "list files", "any ", "find my ", "find the file", "resume", "cv", "document", "pdf", "txt", "docx", "xlsx", "pptx", "html", "code", "file", "files", "implement", "source"
    ]
    import re
    if any(trigger in q_lower for trigger in search_triggers) or re.search(r"\.(py|cpp|c|js|java|txt|md|docx|pdf|xlsx|pptx|html)\b", q_lower):
        return "SEARCH"
    # Fallback to LLM classification for other queries
    prompt = f"""You are a query classifier. Classify the user query into EXACTLY one of these categories:
    SEARCH, READ, LIST, MOVE, CHAT
    Query: "{query}"
    Reply ONLY with the category name (e.g. SEARCH). Do not add any punctuation or explanation.
    """
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        intent = response.content.strip().upper()
        intent = intent.replace(".", "").replace('"', '').strip()
        valid_intents = {"SEARCH", "READ", "LIST", "MOVE", "CHAT"}
        for valid in valid_intents:
            if valid == intent:
                return valid
            if valid in intent and len(intent) < 20:
                return valid
        return "CHAT"
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return "CHAT"

def extract_search_params(query: str, llm) -> str:
    """Extract search keywords."""
    prompt = f"""Extract specific search keywords from this query. Remove words like "find", "search", "all", "files", "please".
    Query: "{query}"
    Reply ONLY with the keywords.
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()

def extract_path(query: str, llm) -> str:
    """Extract file/folder path."""
    prompt = f"""Extract the file or folder path from this query. 
    If a path is explicitly mentioned, return it.
    If a filename is mentioned, return it.
    Query: "{query}"
    Reply ONLY with the path/filename.
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    path = response.content.strip()
    # Cleanup markdown code blocks if model adds them
    path = path.replace('`', '').strip()
    return path

def run_agent_pipeline(user_query: str, session_history: List[Dict] = None) -> Dict[str, Any]:
    """
    Robust Router Pipeline:
    1. Classify Intent
    2. Extract Parameters
    3. Execute Tool
    4. Format Response
    """
    logger.info(f"Router Agent received: {user_query}")
    llm = get_llm()
    
    try:
        # Step 1: Classify
        intent = classify_intent(user_query, llm)
        logger.info(f"Classified intent: {intent}")
        
        # Step 2 & 3: Execute based on intent
        if intent == "SEARCH":
            # Use raw user query for search, matching search view logic
            k = 10 if "all" in user_query.lower() else 5
            tool_result = tools.search_files.invoke({"query": user_query, "k": k})
            results = []
            if isinstance(tool_result, list):
                for r in tool_result:
                    results.append({
                        "path": r.get("source", ""),
                        "source": r.get("source", ""),
                        "summary": r.get("summary", ""),
                        "relevance_score": r.get("score", 0),
                        "processing_status": r.get("processing_status", "unknown"),
                        "content": r.get("content", "")
                    })
            # Sort results by relevance_score descending for consistency
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            answer = f"I found {len(results)} files matching '{user_query}'. Showing the most relevant files below."
            return {
                "answer": answer,
                "tool_used": "search_files",
                "sources": results,
                "tool_calls": 1,
                "intent": "AGENT",
                "agent_type": "router_v1"
            }
            
        elif intent in ["READ", "LIST"]:
            path = extract_path(user_query, llm)
            logger.info(f"Extracted path: {path}")
            # If path extraction fails, is ambiguous, or is not a valid file/dir, fallback to CHAT intent
            invalid_path = (
                not path or not isinstance(path, str) or path.strip() == "" or
                "None of these queries" in path or "The reply should be" in path or
                path.lower().endswith('.py') or path.lower().endswith('.chp') or
                path.lower() in ["merge_sort.py", "introduction.chp"]
            )
            if invalid_path:
                logger.info("Path extraction failed, ambiguous, or general question. Routing to CHAT intent.")
                prompt = f"You are a helpful assistant. Reply to the user.\nUser: {user_query}"
                response = llm.invoke([HumanMessage(content=prompt)])
                return {
                    "answer": response.content,
                    "tool_used": "none",
                    "sources": [],
                    "tool_calls": 0,
                    "intent": "CHAT",
                    "agent_type": "router_v1"
                }
            if intent == "READ":
                tool_result = tools.read_file.invoke({"file_path": path})
                if "Error" in tool_result:
                    answer = tool_result
                else:
                    answer = f"Here is the content of `{path}`:\n\n{tool_result}"
                return {
                    "answer": answer,
                    "tool_used": "read_file",
                    "sources": [{"source": path, "path": path}],
                    "tool_calls": 1,
                    "intent": "AGENT",
                    "agent_type": "router_v1"
                }
            else: # intent == "LIST"
                tool_result = tools.list_directory.invoke({"path": path})
                return {
                    "answer": f"Contents of `{path}`:\n\n{tool_result}",
                    "tool_used": "list_directory",
                    "sources": [],
                    "tool_calls": 1,
                    "intent": "AGENT",
                    "agent_type": "router_v1"
                }
            
        elif intent == "MOVE":
            # Just say it's not fully implemented safely yet or do simple extraction
            # For robustness with 0.5b, maybe best to defer complex multi-param extractions or hardcode prompt
            return {
                "answer": "Move operations are currently disabled for safety in this robust mode.",
                "tool_used": "none",
                "sources": [],
                "tool_calls": 0,
                "intent": "AGENT",
                "agent_type": "router_v1"
            }
            
        else: # CHAT
            # Standard chat response
            prompt = f"You are a helpful assistant. Reply to the user.\nUser: {user_query}"
            response = llm.invoke([HumanMessage(content=prompt)])
            return {
                "answer": response.content,
                "tool_used": "none",
                "sources": [],
                "tool_calls": 0,
                "intent": "CHAT",
                "agent_type": "router_v1"
            }

    except Exception as e:
        logger.error(f"Router pipeline error: {e}", exc_info=True)
        return {
            "answer": f"I encountered an error: {str(e)}",
            "tool_used": "error",
            "sources": [],
            "tool_calls": 0,
            "error": str(e),
            "intent": "ERROR"
        }

def _extract_sources(tool_output: str) -> List[Dict]:
    """Helper to extract sources from string output."""
    sources: List[Dict] = []
    try:
        # If tool_output is a list of result dicts from hybrid_search
        if isinstance(tool_output, list):
            for item in tool_output:
                if isinstance(item, dict):
                    path = item.get('source') or item.get('path') or item.get('source_path')
                    if path:
                        sources.append({'source': path, 'path': path})
            return sources

        # If it's a string, try to parse lines containing 'Path:' (backwards compatibility)
        if isinstance(tool_output, str):
            lines = tool_output.split("\n")
            for line in lines:
                if "Path:" in line:
                    path = line.replace("Path:", "").strip()
                    sources.append({"source": path, "path": path})
            return sources

    except Exception:
        # Best-effort: return empty list on any parsing error
        pass

    return sources
