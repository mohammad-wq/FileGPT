"""
Enhanced Intent Router Service using LangChain
Supports multi-intent queries (e.g., find file + answer question)
"""

from typing import Literal, Optional, List
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate


# Pydantic models for structured output
class SearchIntent(BaseModel):
    """Schema for SEARCH intent"""
    intent: Literal["SEARCH"] = Field(description="Intent type - must be SEARCH")
    query: str = Field(description="Cleaned and focused search query extracted from user input")
    follow_up_question: Optional[str] = Field(
        default=None,
        description="If user wants to ask something about the search results, the question to answer"
    )


class ActionIntent(BaseModel):
    """Schema for ACTION intent"""
    intent: Literal["ACTION"] = Field(description="Intent type - must be ACTION")
    action: str = Field(description="Type of action: create_folder, delete, move, organize, rename")
    target: str = Field(description="Target path, folder name, or file pattern mentioned")
    details: Optional[str] = Field(default="", description="Additional context or parameters")


class ChatIntent(BaseModel):
    """Schema for CHAT intent"""
    intent: Literal["CHAT"] = Field(description="Intent type - must be CHAT")


class MultiIntent(BaseModel):
    """Schema for queries with multiple intents"""
    intent: Literal["MULTI"] = Field(description="Intent type - must be MULTI for compound queries")
    primary_intent: Literal["SEARCH", "ACTION"] = Field(
        description="The main intent (what to do first)"
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Search query if primary is SEARCH"
    )
    action_type: Optional[str] = Field(
        default=None, 
        description="Action type if primary is ACTION"
    )
    action_target: Optional[str] = Field(
        default=None,
        description="Action target if primary is ACTION"
    )
    follow_up_question: str = Field(
        description="The question or task to perform after the primary action"
    )


def route_query(user_query: str) -> dict:
    """
    Route a user query to the appropriate intent category.
    
    Handles both single and multi-intent queries.
    Example multi-intent: "Find expense.xlsx and tell me the total"
    
    Args:
        user_query: The raw user input string
        
    Returns:
        Dictionary with structure:
        {
            "intent": "SEARCH" | "ACTION" | "CHAT" | "MULTI",
            "parameters": {
                # Intent-specific parameters
            }
        }
    """
    
    try:
        # Fast deterministic heuristic: if the user explicitly asks to find/show/search files or code,
        # classify as SEARCH immediately to avoid LLM misclassification.
        q_lower = user_query.strip().lower()
        search_triggers = [
            "find ", "find the ", "show ", "show me ", "search ", "search for ",
            "where is ", "open ", "find file", "find code", "show code", "show file",
            "do i have", "list files", "any .* files", "find my ", "find the file",
        ]

        # quick regex-ish checks for file extensions or code keywords
        import re
        if any(trigger in q_lower for trigger in search_triggers) or re.search(r"\\.(py|cpp|c|js|java|txt|md|docx|pdf)\\b", q_lower) or any(kw in q_lower for kw in ("code", "file", "files", "implement", "source")):
            # Normalize query for search parameter
            cleaned = re.sub(r"^(find|show|search) (the )?", "", q_lower).strip()
            # fallback to full original if cleaned becomes empty
            search_q = cleaned if cleaned else user_query
            return {"intent": "SEARCH", "parameters": {"query": search_q}}

        # Initialize Ollama with LangChain
        llm = ChatOllama(
            model="qwen2.5:0.5b",
            temperature=0.1,
            num_predict=300,
        )
        
        # Enhanced system message that detects multi-intent
        system_message = """You are an intent classification system. Classify user queries carefully.

**IMPORTANT: Default to SEARCH when user asks about code, files, or content!**

**Categories:**

1. **SEARCH**: Finding files OR asking about file content
   Examples:
   - "find bubble sort code" → SEARCH
   - "show me the bubble sort code" → SEARCH  
   - "search for bubble sort" → SEARCH
   - "do I have any Python files?" → SEARCH
   - "what's in expense.xlsx?" → SEARCH
   - "find my meeting notes" → SEARCH
   - "show me config files" → SEARCH
   
2. **ACTION**: File operations (create, delete, move, rename)
   Examples:
   - "Create folder Data" → ACTION
   - "Delete old files" → ACTION
   - "Move PDFs to archive" → ACTION
   
3. **CHAT**: General questions NOT about user's files
   Examples:
   - "How does bubble sort work?" → CHAT (asking for explanation, not user's code)
   - "What's the weather?" → CHAT
   - "Hello" → CHAT
   - "Hi", "How are you?", "Explain quantum physics"

4. **MULTI**: Compound queries combining search/action with a follow-up
   - "Find expense.xlsx and summarize it"
   - "Show me Python files and explain what they do"
   - "Create folder Data and move all CSVs there"

**Detection Rules:**
- Keywords indicating multi-intent: "and then", "and tell me", "and explain", "and summarize", "then"
- If query has TWO distinct requests, classify as MULTI
- If query is simple with one request, use single intent

**Instructions:**
- For MULTI: Identify primary action (search/action) and the follow-up question/task
- For SEARCH with question: Extract both search query and the question
- Be precise in classification

Classify this query:"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", "{query}")
        ])
        
        # Try MULTI intent first (most specific)
        try:
            structured_llm = llm.with_structured_output(MultiIntent)
            chain = prompt | structured_llm
            result = chain.invoke({"query": user_query})
            
            # Successfully detected multi-intent
            params = {
                "primary_intent": result.primary_intent,
                "follow_up_question": result.follow_up_question
            }
            
            if result.primary_intent == "SEARCH":
                params["search_query"] = result.search_query
            elif result.primary_intent == "ACTION":
                params["action_type"] = result.action_type
                params["action_target"] = result.action_target
            
            return {
                "intent": "MULTI",
                "parameters": params
            }
        except:
            pass
        
        # Try SEARCH with optional follow-up
        try:
            structured_llm = llm.with_structured_output(SearchIntent)
            chain = prompt | structured_llm
            result = chain.invoke({"query": user_query})
            
            params = {"query": result.query}
            if result.follow_up_question:
                params["follow_up_question"] = result.follow_up_question
            
            return {
                "intent": "SEARCH",
                "parameters": params
            }
        except:
            pass
        
        # Try ACTION
        try:
            structured_llm = llm.with_structured_output(ActionIntent)
            chain = prompt | structured_llm
            result = chain.invoke({"query": user_query})
            
            return {
                "intent": "ACTION",
                "parameters": {
                    "action": result.action,
                    "target": result.target,
                    "details": result.details or ""
                }
            }
        except:
            pass
        
        # Default to CHAT
        structured_llm = llm.with_structured_output(ChatIntent)
        chain = prompt | structured_llm
        result = chain.invoke({"query": user_query})
        
        return {
            "intent": "CHAT",
            "parameters": {}
        }
        
    except Exception as e:
        print(f"Router error: {e}")
        
        return {
            "intent": "CHAT",
            "parameters": {
                "original_query": user_query
            }
        }


def get_intent_description(intent: str) -> str:
    """
    Get a human-readable description of an intent type.
    
    Args:
        intent: The intent category
        
    Returns:
        Description string
    """
    descriptions = {
        "SEARCH": "Searching file content",
        "ACTION": "File operation",
        "CHAT": "General conversation",
        "MULTI": "Multi-step operation"
    }
    return descriptions.get(intent, "Unknown intent")
