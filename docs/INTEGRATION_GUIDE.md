# FileGPT Backend Integration Guide

## Step 1: Add Router Service Import

In `backend/api/main.py`, line 21, change:
```python
from services import searchEngine, file_watcher, metadata_db, categorization_service
```

To:
```python  
from services import searchEngine, file_watcher, metadata_db, categorization_service, router_service
```

## Step 2: Replace the /ask Endpoint  

Find the `/ask` endpoint (starts around line 196). Replace the entire function with this code:

```python
@app.post("/ask")
async def ask(request: AskRequest):
    """
    Ask a question with intelligent intent routing.
    
    Supports SEARCH, ACTION, CHAT, and MULTI intents.
    """
    
    # Route the query
    routing_result = router_service.route_query(request.query)
    intent = routing_result["intent"]
    parameters = routing_result.get("parameters", {})
    
    print(f"Intent: {intent}, Parameters: {parameters}")
    
    if intent == "SEARCH":
        search_query = parameters.get("query", request.query)
        search_results = searchEngine.hybrid_search(search_query, k=request.k)
        
        if not search_results:
            return {"answer": "No relevant files found.", "sources": [], "intent": intent}
        
        context_parts, sources = [], []
        for i, result in enumerate(search_results):
            context_parts.append(f"--- Source {i+1}: {result['source']} ---")
            if result.get('summary'):
                context_parts.append(f"Summary: {result['summary']}")
            context_parts.append(f"Content: {result['content']}")
            context_parts.append("")
            sources.append({"path": result['source'], "summary": result.get('summary', ''), "relevance_score": result.get('score', 0)})
        
        prompt = f"""Answer based on context.

Question: {request.query}

Context:
{chr(10).join(context_parts)}

Answer using context, cite sources, be concise."""
        
        response = ollama.chat(model="qwen2.5:0.5b", messages=[{'role': 'user', 'content': prompt}], options={'temperature': 0.7, 'num_predict': 500})
        return {"answer": response['message']['content'].strip(), "sources": sources, "context_used": len(search_results), "intent": intent}
    
    elif intent == "MULTI":
        primary_intent = parameters.get("primary_intent")
        follow_up = parameters.get("follow_up_question", "")
        
        if primary_intent == "SEARCH":
            search_query = parameters.get("search_query", request.query)
            search_results = searchEngine.hybrid_search(search_query, k=request.k)
            
            if not search_results:
                return {"answer": "No files found.", "sources": [], "intent": intent}
            
            context_parts, sources = [], []
            for i, result in enumerate(search_results):
                context_parts.append(f"--- Source {i+1}: {result['source']} ---")
                if result.get('summary'):
                    context_parts.append(f"Summary: {result['summary']}")
                context_parts.append(f"Content: {result['content']}")
                context_parts.append("")
                sources.append({"path": result['source'], "summary": result.get('summary', ''), "relevance_score": result.get('score', 0)})
            
            prompt = f"""Compound request.

Original: {request.query}

Found files:
{chr(10).join(context_parts)}

Answer this: {follow_up}

Use file information, cite sources."""
            
            response = ollama.chat(model="qwen2.5:0.5b", messages=[{'role': 'user', 'content': prompt}], options={'temperature': 0.7, 'num_predict': 500})
            return {"answer": response['message']['content'].strip(), "sources": sources, "context_used": len(search_results), "intent": intent, "multi_intent_details": {"primary": primary_intent, "follow_up": follow_up}}
        return {"answer": "Multi-step understood but couldn't complete.", "sources": [], "intent": intent}
    
    elif intent == "ACTION":
        action = parameters.get("action", "unknown")
        target = parameters.get("target", "")
        details = parameters.get("details", "")
        return {"answer": f"File operation:\nAction: {action}\nTarget: {target}\n{details}\n\nUse /create_folder, /move, /delete endpoints.", "sources": [], "intent": intent, "action_details": {"action": action, "target": target, "details": details}}
    
    else:  # CHAT
        response = ollama.chat(model="qwen2.5:0.5b", messages=[{'role': 'system', 'content': 'You are FileGPT. Be friendly and concise.'}, {'role': 'user', 'content': request.query}], options={'temperature': 0.8, 'num_predict': 300})
        return {"answer": response['message']['content'].strip(), "sources": [], "intent": intent}
```

## Step 3: Save and Test

1. Save the file
2. Start backend: `cd backend && python start.py`
3. Start frontend: `cd frontend && npm run tauri dev`
4. Test queries:
   - "Show me Python files" (SEARCH)
   - "Hello!" (CHAT)
   - "Find expense.xls and tell me the total" (MULTI)

The integration is complete!
