# FileGPT Backend - Complete Setup Guide

This guide will help you set up and run the complete FileGPT backend with full file indexing, searching, and AI-powered file organization capabilities.

## System Requirements

- **Python**: 3.10 or higher
- **RAM**: 4GB minimum (8GB recommended)
- **Disk Space**: 10GB for models and indexes
- **Ollama**: Required for LLM functionality (summarization and categorization)

## Step 1: Install Dependencies

### 1.1 Install Python Packages

```bash
cd c:\Users\Mohammad\Desktop\FileGPT\backend
pip install -r requirements.txt
```

### 1.2 Install and Start Ollama

Ollama provides the local LLM needed for file summarization and categorization.

1. Download from [ollama.ai](https://ollama.ai)
2. Install and start Ollama
3. Pull the required model:

```bash
ollama pull llama3.2:3b
```

**Model Options:**
- `llama3.2:3b` (Recommended): ~2GB RAM, faster, good quality
- `llama3:8b`: ~8GB RAM, better quality, slower

The server will work with either model or fallback between them.

## Step 2: Understand the Architecture

### Core Components

```
FileGPT Backend
├── File Parsing & Indexing
│   ├── doclingDocumentParser.py  - Supports .txt, .pdf, .docx, code files
│   ├── embeddingGeneration.py     - Creates vector embeddings
│   └── indexingService.py         - Processes files into embeddings
│
├── Storage & Search
│   ├── searchEngine.py            - Hybrid search (semantic + keyword)
│   ├── ChromaDB                   - Vector database for embeddings
│   ├── BM25 Index                 - Keyword-based search
│   └── metadata_db.py             - File metadata & summaries
│
├── File Management
│   ├── file_watcher.py            - Real-time file monitoring
│   ├── index_manager.py           - Smart indexing (first-run vs incremental)
│   └── categorization_service.py  - AI-powered file organization
│
├── Intelligence
│   ├── router_service.py          - Intent classification (SEARCH/ACTION/CHAT)
│   ├── summary_service.py         - File summarization with Ollama
│   └── llmHandler.py              - LLM interactions
│
└── API
    └── main.py                    - FastAPI endpoints
```

### Data Flow

```
1. STARTUP (First-Run)
   ├─ Scan Desktop, Documents, Downloads
   ├─ Parse each file (PDF, DOCX, TXT, Code)
   ├─ Generate embeddings for text chunks
   ├─ Create file summaries with LLM
   ├─ Store in ChromaDB + BM25 + SQLite
   └─ Start real-time file watcher

2. USER QUERY
   ├─ Route query (SEARCH/ACTION/CHAT)
   ├─ If SEARCH: Hybrid search (semantic + keyword)
   ├─ If ACTION: Execute file operation
   ├─ If CHAT: General conversation
   └─ Return results with sources

3. REAL-TIME UPDATES
   ├─ File watcher detects changes
   ├─ New/modified files auto-indexed
   ├─ Deleted files removed from index
   └─ Metadata and summaries updated
```

## Step 3: Start the Backend

### Option A: Run Directly

```bash
cd c:\Users\Mohammad\Desktop\FileGPT\backend
python start.py
```

The server will:
1. Initialize ChromaDB and search indexes
2. Scan Desktop, Documents, Downloads folders
3. Index all supported files (full scan on first run, incremental on subsequent runs)
4. Start file watcher for real-time updates
5. Be available at `http://127.0.0.1:8000`

### Option B: Run with Python

```bash
cd c:\Users\Mohammad\Desktop\FileGPT\backend
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

### Expected First-Run Output

```
============================================================
FileGPT Backend Starting...
============================================================
✓ Metadata database initialized
✓ Search indexes loaded

📁 Initializing directory monitoring:
🔍 First run detected - performing full scan of: C:\Users\Mohammad\Desktop
📄 Indexing: file1.pdf
📄 Indexing: file2.py
📄 Indexing: file3.docx
... (all files indexed)
✅ Scan complete: 150 indexed, 0 skipped, 0 errors

✓ File watcher started

📁 Watching directories:
  • C:\Users\Mohammad\Desktop
  • C:\Users\Mohammad\Documents
  • C:\Users\Mohammad\Downloads

============================================================
🚀 FileGPT Backend Ready!
============================================================
```

## Step 4: Test the API

### Access the API Documentation

Open in browser: `http://127.0.0.1:8000/docs`

This shows the interactive API documentation where you can test all endpoints.

### Health Check

```bash
curl http://127.0.0.1:8000/
```

### Search Example

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Python sorting algorithms", "k": 5}'
```

### Ask with Intent Routing

The `/ask` endpoint automatically routes your query:

**Example 1: SEARCH Intent**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What sorting algorithms are in my files?", "k": 5}'
```

**Example 2: ACTION Intent**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Create a folder called ProjectX"}'
```

**Example 3: CHAT Intent**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello! What can you do?"}'
```

## Step 5: Understand the Functionality

### 1. File Parsing & Indexing

**Supported File Types:**
- Text: `.txt`, `.md`, `.markdown`, `.rst`, `.log`, `.json`, `.xml`, `.yaml`, `.csv`
- Code: `.py`, `.js`, `.java`, `.cpp`, `.c`, `.rs`, `.go`, `.rb`, etc.
- Documents: `.pdf`, `.docx`, `.doc`

**First-Run Process:**
1. Full scan of Desktop, Documents, Downloads
2. Extract content from each file
3. Split into 600-character chunks with 100-character overlap
4. Generate embeddings for each chunk
5. Create 2-3 sentence summary for each file
6. Store embeddings in ChromaDB (vector search)
7. Store text in BM25 index (keyword search)
8. Store metadata in SQLite database

**Subsequent Runs:**
- Only indexes new or modified files
- Skips unchanged files
- Removes deleted files from index
- Much faster startup

### 2. Hybrid Search

Combines two search methods:

**Semantic Search (Vector-based):**
- Uses embeddings to find conceptually similar content
- Good for: "Find files about sorting algorithms" (conceptual)
- Scores based on similarity distance

**Keyword Search (BM25):**
- Traditional full-text search
- Good for: "Find files with 'quicksort' in them" (exact terms)
- Scores based on term frequency and inverse document frequency

**Result Fusion:**
- Both methods run in parallel
- Results deduplicated by content
- Sorted by combined score
- Returns top-k results

### 3. Intent Routing

The `/ask` endpoint automatically classifies your query:

**SEARCH Intent**
- Keywords: "find", "search", "what", "how", "summarize", "show"
- Triggers: Hybrid search + LLM answer generation
- Example: "What files mention machine learning?"

**ACTION Intent**
- Keywords: "create", "delete", "move", "organize", "rename"
- Triggers: File operation execution
- Example: "Create a folder called Projects"

**CHAT Intent**
- Keywords: "hello", "explain", "what can you do", general conversation
- Triggers: Direct LLM conversation (no file search)
- Example: "Explain quantum computing"

### 4. File Summarization

When a file is indexed:
1. Extract file content (full text or first 8000 characters)
2. Send to Ollama LLM with prompt
3. Get 2-3 sentence summary
4. Store with file metadata
5. Summaries appear in search results

### 5. Real-Time File Monitoring

The file watcher:
- Monitors Desktop, Documents, Downloads
- Detects file creation, modification, deletion
- Auto-indexes new files within 0.5 seconds
- Removes deleted files from index
- Updates summaries for modified files
- Ignores system files and cache directories

### 6. AI File Organization

**Categorization:**
- Analyzes file content and metadata
- Groups files by semantic similarity
- Suggests natural language categories
- Supports complex queries: "Group all sorting algorithms"

**Auto-Organization:**
- Find matching files using search
- Filter by confidence threshold
- Move files to destination folder
- Avoid naming conflicts with auto-numbering
- Dry-run mode to preview changes

## Step 6: API Endpoints Reference

### Core Endpoints

**GET `/`** - Health check
```json
{
  "status": "online",
  "stats": {
    "chroma_chunks": 5000,
    "bm25_chunks": 5000,
    "total_files": 150
  }
}
```

**POST `/search`** - Hybrid search
```json
{
  "query": "Python sorting algorithms",
  "k": 5
}
```

**POST `/ask`** - Intelligent query with intent routing
```json
{
  "query": "What are the main sorting algorithms in my files?",
  "k": 5
}
```

**POST `/create_folder`** - Create a new folder
```json
{
  "path": "C:\\Users\\Mohammad\\Desktop\\NewFolder"
}
```

**POST `/move`** - Move file or folder
```json
{
  "source": "C:\\source\\file.txt",
  "destination": "C:\\destination\\file.txt"
}
```

**DELETE `/delete`** - Delete file or folder
```json
{
  "path": "C:\\Users\\Mohammad\\file.txt"
}
```

**POST `/list`** - List directory contents
```json
{
  "path": "C:\\Users\\Mohammad\\Desktop"
}
```

**GET `/stats`** - Get index statistics
**GET `/watched_folders`** - Get monitored directories

### Categorization Endpoints

**POST `/categorize`** - Find files by category
```json
{
  "category_description": "sorting algorithms",
  "max_files": 50
}
```

**POST `/organize`** - Auto-organize files
```json
{
  "category_description": "sorting algorithms",
  "destination_folder": "C:\\SortingAlgorithms",
  "min_confidence": 0.6,
  "dry_run": true
}
```

**POST `/suggest_categories`** - Get category suggestions
```json
{
  "file_paths": ["C:\\file1.py", "C:\\file2.py"]
}
```

## Troubleshooting

### Issue: "Ollama connection failed"
**Solution:** 
1. Start Ollama: `ollama serve` (or use Ollama app)
2. Check model installed: `ollama list`
3. Pull model: `ollama pull llama3.2:3b`

### Issue: "No chunks indexed" on first run
**Solution:**
1. Ensure supported file types in monitored folders
2. Check `index_state.json` was created (first-run indicator)
3. Check file_watcher is running
4. Verify file permissions

### Issue: Search returns empty results
**Solution:**
1. Check `/stats` endpoint - verify files were indexed
2. Try broader search query
3. Check file summaries were generated
4. Increase `k` parameter for more results

### Issue: Slow indexing on first run
**Normal behavior!** First run scans and indexes all files:
- 100 files: ~5-10 minutes
- 500 files: ~20-30 minutes
- 1000+ files: 1+ hours
(Depends on file sizes and CPU)

Subsequent runs are much faster (incremental indexing only).

### Issue: "Address already in use"
**Solution:** Port 8000 is already in use
```bash
# Find process on port 8000
netstat -ano | findstr :8000

# Kill process
taskkill /PID [PID] /F

# Or use different port
python -m uvicorn api.main:app --port 8001
```

## Performance Optimization

### Memory Usage
- Smaller Ollama model: `ollama pull llama3.2:3b`
- Reduces RAM from ~8GB to ~2GB
- Minimal quality loss for summarization

### Search Speed
- Hybrid search: ~0.5-1 second per query
- Semantic search (ChromaDB): ~0.3 seconds
- Keyword search (BM25): ~0.2 seconds

### Indexing Speed
- ~1-2 files per second
- Depends on file size and content complexity
- First run: Full scan = slower
- Subsequent runs: Incremental = 10x faster

## Next Steps

1. **Frontend Integration**: Connect frontend to these endpoints
2. **Custom Directories**: Use `/add_folder` to monitor additional folders
3. **Backup Indexes**: Back up `chroma_db/` and `filegpt_metadata.db`
4. **Advanced Configuration**: Adjust chunk size, model, temperature in service files

## Support & Issues

If you encounter issues:
1. Check the error messages in console
2. Review logs in the output
3. Verify Ollama is running: `ollama list`
4. Check file permissions in monitored directories
5. Ensure Python 3.10+ is installed

## Architecture Summary

This implementation provides a complete RAG (Retrieval Augmented Generation) system:

1. **Retrieval**: Hybrid search (semantic + keyword)
2. **Augmentation**: Retrieved documents provide context
3. **Generation**: LLM generates answers based on context

Plus intelligent file management:
- Intent routing (SEARCH/ACTION/CHAT)
- File categorization and organization
- Real-time file monitoring
- Persistent storage of embeddings and metadata

All running locally with no external dependencies or API calls!
