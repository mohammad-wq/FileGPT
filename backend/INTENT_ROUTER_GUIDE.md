# Intent Router Implementation Guide

## Overview

The Intent Router is an intelligent query classification system that uses a local LLM to determine user intent before processing queries. This allows FileGPT to handle three distinct types of user interactions appropriately.

## Architecture

### Intent Classification
The router classifies queries into three categories:

**1. SEARCH** - Questions about file content
- Uses hybrid RAG (semantic + keyword search)
- Provides answers with file sources
- Example: "Summarize the expense report", "Find functions that use asyncio"

**2. ACTION** - File operation requests  
- Detected file management commands
- Returns structured action details
- Example: "Create a folder named Data", "Move temp files to archive"

**3. CHAT** - General conversation
- No file context needed
- Direct LLM conversation
- Example: "Hello", "What can you do?", "Explain quantum physics"

### System Flow

```
User Query → Intent Router → Intent Classification
                                  ↓
                    ┌─────────────┼─────────────┐
                    ↓             ↓             ↓
                 SEARCH        ACTION         CHAT
                    ↓             ↓             ↓
              Hybrid Search   File Ops    Simple Chat
                    ↓             ↓             ↓
              RAG Answer     Action Plan   Conversation
```

## Implementation Details

### 1. Router Service (`router_service.py`) - LangChain Version

**Key Features:**
- **Pydantic Models**: Type-safe schema definitions for each intent
- **LangChain Structured Output**: Guaranteed JSON parsing with automatic validation
- **ChatOllama**: LangChain's Ollama integration for local LLM
- **Temperature 0.1**: Consistent classification results
- **Cascading Fallback**: Tries SEARCH → ACTION → CHAT → Error fallback

**Pydantic Models:**
```python
class SearchIntent(BaseModel):
    intent: Literal["SEARCH"]
    query: str  # Cleaned search query

class ActionIntent(BaseModel):
    intent: Literal["ACTION"]  
    action: str  # create_folder, delete, move, etc.
    target: str  # Path or file pattern
    details: Optional[str]

class ChatIntent(BaseModel):
    intent: Literal["CHAT"]
```

**Advantages over Manual JSON Parsing:**
- Automatic validation against Pydantic schemas
- No JSON parsing errors (handled by LangChain)
- Type hints for better IDE support
- Easier to extend with new fields
- Better error messages

**Usage:**
```python
from services import router_service

result = router_service.route_query("Find all Python files about sorting")
# Returns: {"intent": "SEARCH", "parameters": {"query": "Python sorting files"}}
```

### 2. Updated /ask Endpoint

The endpoint now follows this flow:

1. **Route** - Classify intent using `router_service.route_query()`
2. **Branch** - Execute appropriate logic based on intent
3. **Return** - Include `intent` field in response

**Response Structure:**
```json
{
  "answer": "...",
  "sources": [...],
  "intent": "SEARCH",
  "context_used": 5
}
```

## Testing the Router

### Example SEARCH Queries:
- "What files mention machine learning?"
- "Summarize my expenses.xlsx"
- "Find the init_db function"

### Example ACTION Queries:
- "Create a folder named Projects"
- "Delete all temp files"
- "Move this to Documents"

### Example CHAT Queries:
- "Hello!"
- "What can you do?"
- "Explain how RAG works"

## Benefits

1. **Improved User Experience** - System understands intent, not just keywords
2. **Efficient Processing** - No unnecessary file searches for chat queries
3. **Future Extensibility** - Easy to add new intent categories
4. **Query Refinement** - LLM cleans/focuses queries before search
5. **Type Safety** - Pydantic models ensure valid data structures
6. **Reliability** - LangChain's structured output eliminates JSON parsing errors
7. **Maintainability** - Clear schemas make code easier to understand and modify

## LangChain Structured Output Advantages

**Compared to manual JSON parsing:**
- ✅ Automatic schema validation
- ✅ No `json.loads()` errors
- ✅ Type hints for IDE autocomplete
- ✅ Pydantic field validation
- ✅ Better error messages
- ✅ Extensible field definitions

**Example Schema Evolution:**
Adding a new field is trivial with Pydantic:
```python
class SearchIntent(BaseModel):
    intent: Literal["SEARCH"]
    query: str
    filters: Optional[List[str]] = []  # New field - automatically handled!
```

## Future Enhancements

- ACTION intent execution (currently returns plan only)
- Multi-intent detection (handle combined queries)
- Intent-specific tuning (different models per intent)
- User feedback loop for classification accuracy

## Debugging

The router prints intent and parameters to console:
```
Intent detected: SEARCH
Parameters: {'query': 'Python sorting algorithms'}
```

Check backend logs to verify classification is working correctly.
