@app.post("/ask")
async def ask(request: AskRequest):
    """
    Ask a question with intelligent intent routing.
    Supports SEARCH, ACTION, CHAT, and MULTI intents.
    """
    try:
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
            
            # Build context and sources (simplified for small model)
            context_parts = []
            sources = []
            
            for i, result in enumerate(search_results):
                # Simplified format - easier for small model to parse
                file_name = os.path.basename(result['source'])
                context_parts.append(f"FILE {i+1}: {file_name}")
                context_parts.append(result['content'])
                context_parts.append("")  # Blank line separator
                
                sources.append({
                    "path": result['source'],
                    "summary": result.get('summary', ''),
                    "relevance_score": result.get('score', 0)
                })
            
            context = "\n".join(context_parts)
            
            
            # OPTIMIZATION: For code-related queries, use extraction mode (no LLM = no hallucination)
            code_keywords = ['code', 'function', 'implementation', 'algorithm', 'snippet', 'program']
            is_code_query = any(keyword in request.query.lower() for keyword in code_keywords)
            
            print(f"DEBUG: Query='{request.query}', is_code_query={is_code_query}, has_results={len(search_results) > 0}")
            
            if is_code_query and search_results:
                # Pure extraction mode - just show the code, no LLM interpretation
                print(f"✓ Using code extraction mode (bypassing LLM)")
                answer_parts = []
                answer_parts.append(f"Found {len(search_results)} relevant file(s):\n")
                
                for i, result in enumerate(search_results[:3], 1):  # Limit to top 3
                    file_name = os.path.basename(result['source'])
                    answer_parts.append(f"\n**{i}. {file_name}**")
                    answer_parts.append(f"```\n{result['content']}\n```\n")
                
                return {
                    "answer": "\n".join(answer_parts), 
                    "sources": sources,
                    "intent": intent,
                    "context_used": len(search_results)
                }
            
            # Standard LLM mode for non-code queries
            # Ultra-simple prompt optimized for 0.5b model
            prompt = f"""Answer this question using ONLY the files shown below. Do not make up information.

Question: {request.query}

Files:
{context}

Rules:
- Only use what's shown above
- Don't invent code
- If you only find it in one file, say so

Answer:"""
            
            try:
                # Optimize for small model (0.5b)
                # - Temperature 0 = more deterministic, less creative/hallucination
                # - Reduced tokens = prevents rambling
                # - Shorter context = easier for small model to handle
                
                # Truncate context if too long (small models struggle with long context)
                max_context_chars = 2000  # ~500 tokens
                if len(context) > max_context_chars:
                    context = context[:max_context_chars] + "\n\n[Context truncated for model capacity]"
                
                response = ollama.chat(
                    model="qwen2.5:0.5b",
                    messages=[{'role': 'user', 'content': prompt}],
                    options={
                        'temperature': 0.0,      # Deterministic (no creativity = less hallucination)
                        'num_predict': 300,      # Shorter responses (was 500)
                        'top_p': 0.9,           # Nucleus sampling
                        'repeat_penalty': 1.1   # Discourage repetition
                    }
                )
                
                answer = response['message']['content'].strip()
                
                # Simple post-processing: warn if answer seems too long (likely hallucinating)
                if len(answer) > 1000:
                    answer = answer[:1000] + "\n\n[Answer truncated - query might be too broad for this model]"
                
                return {
                    "answer": answer,
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
                    file_name = os.path.basename(result['source'])
                    context_parts.append(f"--- Source {i+1}: {file_name} ---")
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
                        model="qwen2.5:0.5b",
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
                    model="qwen2.5:0.5b",
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
    
    except Exception as e:
        print(f"Error in /ask endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")