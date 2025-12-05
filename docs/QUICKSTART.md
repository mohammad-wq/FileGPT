# FileGPT - Complete Backend Implementation Guide

## 🚀 Quick Start (5 Minutes)

### Prerequisites

1. **Python 3.10+** (`python --version`)
2. **Ollama** running with a model installed
3. Dependencies installed

### 1️⃣ Install Ollama & Model

```bash
# Download from https://ollama.ai

# In a terminal, pull the model:
ollama pull qwen2.5:0.5b

# Keep this terminal running or start Ollama in background
ollama serve
```

### 2️⃣ Install Backend Dependencies

```bash
cd C:\Users\Mohammad\Desktop\FileGPT\backend
pip install -r requirements.txt
```

### 3️⃣ Start the Backend

```bash
python start.py
```

**You should see:**
```
============================================================
FileGPT Backend Starting...
============================================================
✓ Metadata database initialized
✓ Search indexes loaded

📁 Initializing directory monitoring:
🔍 First run detected - performing full scan...
📄 Indexing: file1.pdf
📄 Indexing: file2.py
... (all files being indexed)
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

### 4️⃣ Test It

**Open in Browser:**
```
http://127.0.0.1:8000/docs
```

**Test Search:**
```
POST /search
{"query": "python", "k": 5}
```

**Test Ask with Intent Routing:**
```
POST /ask
{"query": "What Python files do I have?"}
```

---

## 📋 Complete Feature List

### ✅ What's Implemented

1. **File Parsing & Indexing**
   - Supports 50+ file types (Python, Java, C++, PDF, DOCX, etc.)
   - Automatic embeddings generation
   - Smart first-run full scan vs incremental updates
   - State tracking in `index_state.json`

2. **Hybrid Search Engine**
   - Semantic search via ChromaDB (vector embeddings)
   - Keyword search via BM25 (traditional full-text)
   - Deduplication and result fusion
   - Relevance scoring

3. **Intent Classification**
   - **SEARCH**: Find files and ask questions
   - **ACTION**: Create folders, organize files, delete
   - **CHAT**: General conversation
   - Automatic routing based on user query

4. **File Management**
   - Create folders
   - Rename files/folders
   - Move files/folders
   - Delete files/folders
   - List directory contents with metadata

5. **AI-Powered Features**
   - Automatic file summarization (2-3 sentences per file)
   - File categorization by semantic similarity
   - Auto-organization into folders
   - Intelligent action execution

6. **Real-Time Monitoring**
   - Watches Desktop, Documents, Downloads
   - Auto-indexes new files instantly
   - Removes deleted files from index
   - Ignores system files and cache

7. **Data Storage**
   - SQLite database for file metadata
   - ChromaDB for vector embeddings
   - BM25 index for keywords
   - Persistent state tracking

---

## 🔧 API Endpoints

### Search & Query

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check |
| `/search` | POST | Hybrid search |
| `/ask` | POST | **Intent-routed query** (SEARCH/ACTION/CHAT) |

### File Operations

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/create_folder` | POST | Create folder |
| `/rename` | POST | Rename file/folder |
| `/move` | POST | Move file/folder |
| `/delete` | DELETE | Delete file/folder |
| `/list` | POST | List directory |

### System

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/stats` | GET | Index statistics |
| `/watched_folders` | GET | Monitored directories |
| `/add_folder` | POST | Add folder to watch |

### AI Categorization

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/categorize` | POST | Find files by category |
| `/organize` | POST | Auto-organize files |
| `/suggest_categories` | POST | Suggest categories |

---

## 🎯 Usage Examples

### Example 1: Search Files
```bash
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"Python sorting algorithms","k":5}'
```

### Example 2: Ask with Intent Routing
```bash
# SEARCH Intent - finds files about Python
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What Python functions do I have?"}'
```

```bash
# ACTION Intent - creates a folder
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"Create a folder called MyProject"}'
```

```bash
# CHAT Intent - general conversation
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"Hello! What can you do?"}'
```

### Example 3: Organize Files
```bash
# Find files related to "sorting algorithms" and move them
curl -X POST http://127.0.0.1:8000/organize \
  -H "Content-Type: application/json" \
  -d '{
    "category_description":"sorting algorithms",
    "destination_folder":"C:\\SortingAlgorithms",
    "min_confidence":0.6,
    "dry_run":false
  }'
```

---

## 📁 Architecture

```
STARTUP
├─ Load ChromaDB + BM25 indexes
├─ Initialize SQLite database
├─ Scan Desktop/Documents/Downloads
├─ Extract file content
├─ Generate embeddings
├─ Create summaries with Ollama
├─ Store in databases
└─ Start file watcher

USER QUERY (/ask)
├─ router_service.route_query()
├─ Classify intent (SEARCH/ACTION/CHAT)
│
├─ If SEARCH:
│  ├─ searchEngine.hybrid_search()
│  ├─ Generate LLM answer
│  └─ Return answer + sources
│
├─ If ACTION:
│  ├─ Parse action (create/delete/organize/etc)
│  ├─ Execute safely (confirm destructive ops)
│  └─ Return status
│
└─ If CHAT:
   ├─ Direct LLM conversation
   └─ No file search

REAL-TIME UPDATES
├─ File watcher detects changes
├─ Index new/modified files
├─ Remove deleted files
└─ Update metadata & summaries
```

---

## 📊 Performance

| Operation | Time | Notes |
|-----------|------|-------|
| First-run indexing | 5-60 min | Depends on file count |
| Subsequent startup | ~30 sec | Incremental indexing only |
| Search query | 0.5-1 sec | Hybrid (semantic + keyword) |
| LLM answer | 2-5 sec | Ollama generation time |
| File indexing (real-time) | <1 sec | Auto-index new files |

---

## 🗂️ File Structure

```
backend/
├── api/
│   └── main.py                      ← FastAPI endpoints
├── services/
│   ├── __init__.py
│   ├── searchEngine.py              ← Hybrid search (ChromaDB + BM25)
│   ├── router_service.py            ← Intent classification
│   ├── index_manager.py             ← Smart indexing
│   ├── file_watcher.py              ← Real-time monitoring
│   ├── metadata_db.py               ← SQLite wrapper
│   ├── summary_service.py           ← Ollama summarization
│   ├── categorization_service.py    ← AI categorization
│   ├── doclingDocumentParser.py     ← File parsing
│   └── embeddingGeneration.py       ← Embedding creation
├── start.py                         ← Startup script
└── requirements.txt

Databases (created on first run):
├── chroma_db/                       ← Vector embeddings
├── filegpt_metadata.db              ← File metadata
├── bm25_index.pkl                   ← Keyword index
└── index_state.json                 ← Indexing state
```

---

## 🔍 Supported File Types

**Text:** `.txt`, `.md`, `.json`, `.xml`, `.yaml`, `.csv`, `.log`
**Code:** `.py`, `.js`, `.java`, `.cpp`, `.c`, `.rs`, `.go`, `.rb`, `.php`, `.ts`, `.jsx`, etc.
**Documents:** `.pdf`, `.docx`, `.doc`

---

## ⚠️ Troubleshooting

**"Ollama connection failed"**
```bash
# Start Ollama
ollama serve

# Check model
ollama list

# Pull model if missing
ollama pull qwen2.5:0.5b
```

**"Port 8000 already in use"**
```bash
# Use different port
python -m uvicorn api.main:app --port 8001
```

**"No files indexed"**
- Check Desktop/Documents/Downloads contain files
- Verify supported file types
- Check console for errors

**"Search empty results"**
- Wait for indexing to complete
- Check `/stats` endpoint
- Try different query

---

## 🚀 Next Steps

1. ✅ Backend running successfully
2. Test each intent type (SEARCH/ACTION/CHAT)
3. Connect frontend to `http://127.0.0.1:8000`
4. Customize monitored folders
5. Add custom file organization rules

**See `SETUP_GUIDE.md` for detailed documentation and advanced features!**

---

**Your FileGPT backend is now fully operational!** 🎉
