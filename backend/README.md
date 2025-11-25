# FileGPT Backend

**Fully offline** AI-powered file search and management system with hybrid RAG architecture.

## 🌟 Features

- **100% Local & Offline** - No internet required, complete privacy
- **Hybrid Search** - Combines semantic (ChromaDB) + keyword (BM25) search
- **AI Summarization** - Local LLM generates file summaries via Ollama
- **AI Categorization** - **NEW** Organize files with natural language ("put all sorting algorithms in one folder")
- **Real-time Monitoring** - Automatic indexing of file changes
- **File Management** - Create, move, rename, delete via REST API
- **Chat Interface** - Ask questions about your files in natural language
- **PC-Wide Indexing** - Automatically monitors Documents, Desktop, Downloads

## 📋 Prerequisites

1. **Python 3.10+**
2. **Ollama** with `llama3:8b` model

```bash
# Install Ollama from: https://ollama.ai
# Then pull the model:
ollama pull llama3:8b
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Or use the startup script:

```bash
python start.py
```

### 3. API is Ready!

Server runs at: `http://127.0.0.1:8000`

Documentation: `http://127.0.0.1:8000/docs`

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check & stats |
| `POST` | `/add_folder` | Add folder to monitoring |
| `POST` | `/search` | Hybrid search (semantic + keyword) |
| `POST` | `/ask` | AI Q&A with file context |
| `POST` | `/create_folder` | Create new folder |
| `POST` | `/rename` | Rename file/folder |
| `POST` | `/move` | Move file/folder |
| `DELETE` | `/delete` | Delete file/folder |
| `POST` | `/list` | List directory contents |
| `GET` | `/stats` | Index statistics |
| `GET` | `/watched_folders` | List monitored folders |
| `POST` | `/categorize` | **NEW** Find files by category (AI) |
| `POST` | `/organize` | **NEW** Auto-organize files by category |
| `POST` | `/suggest_categories` | **NEW** Get AI category suggestions |

## 📦 Architecture

```
backend/
├── api/
│   └── main.py              # FastAPI application
├── services/
│   ├── doclingDocumentParser.py   # Multi-format file parser
│   ├── metadata_db.py             # SQLite metadata store
│   ├── summary_service.py         # Ollama LLM summarization
│   ├── searchEngine.py            # Hybrid RAG (ChromaDB + BM25)
│   └── file_watcher.py            # Real-time file monitoring
├── requirements.txt
├── start.py
└── README.md
```

## 🔍 Usage Examples

### Add a Folder

```bash
curl -X POST http://localhost:8000/add_folder \
  -H "Content-Type: application/json" \
  -d '{"path": "C:\\Users\\YourName\\Projects"}'
```

### Search Files

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication code", "k": 5}'
```

### Ask Questions

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "How does the login system work?"}'
```

### Create Folder

```bash
curl -X POST http://localhost:8000/create_folder \
  -H "Content-Type: application/json" \
  -d '{"path": "C:\\Users\\YourName\\NewFolder"}'
```

### Move File

```bash
curl -X POST http://localhost:8000/move \
  -H "Content-Type: application/json" \
  -d '{"source": "C:\\file.txt", "destination": "C:\\NewFolder\\file.txt"}'
```

## 🗃️ Supported File Types

**Text & Code** (40+ languages):
- Python, JavaScript, TypeScript, Rust, C/C++, Java, Go, PHP, Ruby, etc.
- JSON, YAML, XML, HTML, CSS, Markdown

**Documents**:
- PDF (via pypdf)
- DOCX (via python-docx)

## 🧠 How It Works

1. **File Monitoring**: Watchdog monitors specified directories for changes
2. **Parsing**: Extract text from 50+ file formats
3. **Chunking**: Split content into 600-char chunks with 100-char overlap
4. **Indexing**:
   - **Vector**: Store embeddings in ChromaDB (all-MiniLM-L6-v2)
   - **Keyword**: Build BM25 index for exact matches
5. **Summarization**: Generate 2-3 sentence summaries via Ollama
6. **Storage**: Save metadata (path, hash, summary) in SQLite
7. **Retrieval**: Hybrid search combines semantic + keyword results
8. **Generation**: LLM answers questions using retrieved context

## ⚙️ Configuration

Default settings in `searchEngine.py`:
- `CHUNK_SIZE`: 600 characters
- `CHUNK_OVERLAP`: 100 characters
- `EMBEDDING_MODEL`: all-MiniLM-L6-v2
- `LLM_MODEL`: llama3:8b

## 🛠️ Development

```bash
# Run with auto-reload
uvicorn api.main:app --reload

# Run tests (if added)
pytest tests/

# Check API docs
# Navigate to http://localhost:8000/docs
```

## 📊 Performance Notes

- **Initial Indexing**: ~10-50 files/second depending on file size
- **ChromaDB**: Stores ~1GB of embeddings per 10,000 chunks
- **BM25 Index**: ~10MB per 10,000 chunks (pickle file)
- **SQLite**: ~1MB per 10,000 files

## 🔒 Privacy

All processing happens **100% locally**:
- ✅ Ollama runs on your machine
- ✅ ChromaDB stores data locally
- ✅ No external API calls
- ✅ No data leaves your computer

## 🐛 Troubleshooting

**"Ollama connection failed"**
- Ensure Ollama is running: `ollama serve`
- Verify model is installed: `ollama list`

**"No files indexed"**
- Check folder path exists
- Verify file extensions are supported
- Check console logs for parsing errors

**"Search returns no results"**
- Ensure files are indexed (check `/stats`)
- Try different search queries
- Add more folders with `/add_folder`

## 📄 License

MIT License - Use freely for personal or commercial projects.
