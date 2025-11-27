"""
Enhanced /ask endpoint with Intent Routing
Complete implementation with SEARCH, ACTION, CHAT, and MULTI intents
"""

# This is a replacement for the /ask endpoint in main.py
# Copy this into main.py starting at line 196

@app.post("/ask")
async def ask(request: AskRequest):
    """
    Ask a question and get AI-generated answer with intelligent intent routing.
    
    Supports:
    - SEARCH: Question about file content (uses RAG)
    - ACTION: File operation request 
    - CHAT: General conversation
    - MULTI: Compound queries (find + answer)
    
    Args:
        request: Contains question and optional k (number of context chunks)
        
    Returns:
        AI-generated answer with source references
    """
    
    # Step 1: Route the query to determine intent
    routing_result = router_service.route_query(request.query)
    intent = routing_result["intent"]
    parameters = routing_result.get("parameters", {})
    
    print(f"Intent detected: {intent}")
    print(f"Parameters: {parameters}")
    
    # Step 2: Handle based on intent
    
    if intent == "SEARCH":
        # Handle SEARCH intent - use RAG to answer from file content
        
        search_query = parameters.get("query", request.query)
        search_results = searchEngine.hybrid_search(search_query, k=request.k)
        
        if not search_results:
            return {
                "answer": "I couldn't find any relevant files. Try adding more folders or indexing more files.",
                "sources": [],
                "intent": intent
            }
        
        # Build context and sources
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
        
        prompt = f"""You are a helpful AI assistant with access to the user's files. Answer based on the context provided.

Question: {request.query}

Context from files:
{context}

Instructions:
1. Answer using information from the context
2. Be specific and cite which files you're referencing
3. If context is insufficient, say so
4. Keep your answer concise and helpful

Answer:"""
        
        try:
            response = ollama.chat(
                model="llama3.2:3b",
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.7, 'num_predict': 500}
            )
            
            return {
                "answer":response['message']['content'].strip(),
                "sources": sources,
                "context_used": len(search_results),
                "intent": intent
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
    elif intent == "MULTI":
        # Handle MULTI intent - compound queries (search + follow-up question)
        
        primary_intent = parameters.get("primary_intent")
        follow_up_question = parameters.get("follow_up_question", "")
        
        if primary_intent == "SEARCH":
            search_query = parameters.get("search_query", request.query)
            search_results = searchEngine.hybrid_search(search_query, k=request.k)
            
            if not search_results:
                return {
                    "answer": "I couldn't find any relevant files for your query.",
                    "sources": [],
                    "intent": intent
                }
            
            # Build context and sources
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
            
            # Answer the follow-up question using the found files
            prompt = f"""You are a helpful AI assistant. The user made a compound request.

Original Request: {request.query}

I found these relevant files:
{context}

Now answer this specific question: {follow_up_question}

Instructions:
1. Use information from the files above
2. Be specific and cite sources
3. Focus on the follow-up question
4. Be concise

Answer:"""
            
            try:
                response = ollama.chat(
                    model="llama3.2:3b",
                    messages=[{'role': 'user', 'content': prompt}],
                    options={'temperature': 0.7, 'num_predict': 500}
                )
                
                return {
                    "answer": response['message']['content'].strip(),
                    "sources": sources,
                    "context_used": len(search_results),
                    "intent": intent,
                    "multi_intent_details": {
                        "primary": primary_intent,
                        "follow_up": follow_up_question
                    }
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        else:
            return {
                "answer": "Multi-step operation understood but couldn't complete. Try breaking into separate queries.",
                "sources": [],
                "intent": intent
            }
    
    elif intent == "ACTION":
        # Handle ACTION intent - file operations
        
        action = parameters.get("action", "unknown")
        target = parameters.get("target", "")
        details = parameters.get("details", "")
        
        return {
            "answer": f"I understand you want to perform a file operation:\n\nAction: {action}\nTarget: {target}\n{f'Details: {details}' if details else ''}\n\nThis is being implemented. Use dedicated endpoints like /create_folder, /move, /delete for now.",
            "sources": [],
            "intent": intent,
            "action_details": {
                "action": action,
                "target": target,
                "details": details
            }
        }
    
    else:  # intent == "CHAT"
        # Handle CHAT intent - general conversation
        
        try:
            response = ollama.chat(
                model="llama3.2:3b",
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are FileGPT, a helpful AI assistant for file management. Be friendly and concise.'
                    },
                    {
                        'role': 'user',
                        'content': request.query
                    }
                ],
                options={'temperature': 0.8, 'num_predict': 300}
            )
            
            return {
                "answer": response['message']['content'].strip(),
                "sources": [],
                "intent": intent
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
