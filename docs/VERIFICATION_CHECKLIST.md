# FileGPT Backend - Verification Checklist

Use this checklist to verify that all components are working correctly.

## Pre-Startup Checks

- [ ] Python 3.10+ installed: `python --version`
- [ ] Ollama installed and running: `ollama serve` (in separate terminal)
- [ ] Ollama model available: `ollama list` (should show qwen2.5:0.5b)
- [ ] Dependencies installed: `pip install -r requirements.txt` (no errors)
- [ ] Desktop, Documents, Downloads folders exist
- [ ] Read permissions on monitored folders

## Startup Verification

Start the backend:
```bash
cd C:\Users\Mohammad\Desktop\FileGPT\backend
python start.py
```

### Expected Console Output (First Run)

- [ ] "FileGPT Backend Starting..." message
- [ ] "✓ Metadata database initialized"
- [ ] "✓ Search indexes loaded"
- [ ] "🔍 First run detected - performing full scan"
- [ ] "📄 Indexing: [filenames]" messages
- [ ] "✅ Scan complete: [X] indexed, [Y] skipped"
- [ ] "✓ File watcher started"
- [ ] "📁 Watching directories:" with 3 paths listed
- [ ] "🚀 FileGPT Backend Ready!"
- [ ] No error messages in console

### Expected Databases Created

After first run, verify these exist:
- [ ] `backend/chroma_db/` directory (ChromaDB)
- [ ] `backend/filegpt_metadata.db` file (SQLite)
- [ ] `backend/bm25_index.pkl` file (BM25)
- [ ] `backend/index_state.json` file (state tracking)

## API Endpoint Tests

### 1. Health Check ✓

**Test:**
```bash
curl http://127.0.0.1:8000/
```

**Expected Response:**
```json
{
  "status": "online",
  "service": "FileGPT Backend",
  "version": "1.0.0",
  "stats": {
    "chroma_chunks": [X],
    "bm25_chunks": [X],
    "embedding_model": "all-MiniLM-L6-v2",
    "db_stats": {
      "total_files": [X],
      "db_size_mb": [X.XX]
    }
  }
}
```

- [ ] Status code: 200
- [ ] Status: "online"
- [ ] Stats show indexed files (total_files > 0)

### 2. Get Statistics ✓

**Test:**
```bash
curl http://127.0.0.1:8000/stats
```

**Expected Response:**
- [ ] chroma_chunks > 0
- [ ] bm25_chunks > 0
- [ ] total_files > 0
- [ ] db_size_mb > 0

### 3. Get Watched Folders ✓

**Test:**
```bash
curl http://127.0.0.1:8000/watched_folders
```

**Expected Response:**
```json
{
  "folders": [
    "C:\\Users\\Mohammad\\Desktop",
    "C:\\Users\\Mohammad\\Documents",
    "C:\\Users\\Mohammad\\Downloads"
  ]
}
```

- [ ] Returns array of 3 folders

### 4. Search Endpoint ✓

**Test:**
```bash
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"python","k":5}'
```

**Expected Response:**
```json
{
  "query": "python",
  "results": [
    {
      "content": "[chunk text]",
      "source": "[file path]",
      "summary": "[2-3 sentence summary]",
      "score": 0.85
    }
  ],
  "count": [X]
}
```

- [ ] Status code: 200
- [ ] results is an array
- [ ] results contain content, source, summary, score
- [ ] count > 0

### 5. Ask Endpoint (SEARCH Intent) ✓

**Test:**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"What Python files do I have?"}'
```

**Expected Response:**
- [ ] Status code: 200
- [ ] answer is a non-empty string
- [ ] sources array is not empty
- [ ] intent is "SEARCH"
- [ ] context_used > 0

### 6. Ask Endpoint (ACTION Intent) ✓

**Test:**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"Create a test folder called TestFolder123"}'
```

**Expected Response:**
- [ ] Status code: 200
- [ ] answer contains "✅ Successfully created"
- [ ] intent is "ACTION"
- [ ] action_executed is true
- [ ] path contains "TestFolder123"

**Verify:**
- [ ] Folder `C:\Users\Mohammad\Desktop\TestFolder123` was created

### 7. Ask Endpoint (CHAT Intent) ✓

**Test:**
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"Hello! What can you do?"}'
```

**Expected Response:**
- [ ] Status code: 200
- [ ] answer is a non-empty response
- [ ] intent is "CHAT"
- [ ] sources array is empty
- [ ] context_used is 0

### 8. Create Folder Endpoint ✓

**Test:**
```bash
curl -X POST http://127.0.0.1:8000/create_folder \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\Users\\Mohammad\\Desktop\\TestFolder456"}'
```

**Expected Response:**
- [ ] Status code: 200
- [ ] status is "success"

**Verify:**
- [ ] Folder was created at specified path

### 9. List Endpoint ✓

**Test:**
```bash
curl -X POST http://127.0.0.1:8000/list \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\Users\\Mohammad\\Desktop"}'
```

**Expected Response:**
- [ ] Status code: 200
- [ ] path matches input
- [ ] items is an array
- [ ] count > 0
- [ ] Items contain: name, path, is_directory, size, summary (if indexed)

### 10. Move Endpoint ✓

**Test:**
```bash
# Create a test file first
New-Item -Path "C:\Users\Mohammad\Desktop\test_move.txt" -Value "test"

# Then move it
curl -X POST http://127.0.0.1:8000/move \
  -H "Content-Type: application/json" \
  -d '{
    "source":"C:\\Users\\Mohammad\\Desktop\\test_move.txt",
    "destination":"C:\\Users\\Mohammad\\Desktop\\test_move_new.txt"
  }'
```

**Expected Response:**
- [ ] Status code: 200
- [ ] status is "success"

**Verify:**
- [ ] File moved to new location
- [ ] Old location no longer exists

### 11. Delete Endpoint ✓

**Test:**
```bash
curl -X DELETE http://127.0.0.1:8000/delete \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\Users\\Mohammad\\Desktop\\test_move_new.txt"}'
```

**Expected Response:**
- [ ] Status code: 200
- [ ] status is "success"

**Verify:**
- [ ] File deleted
- [ ] File no longer exists

### 12. Add Folder Endpoint ✓

**Test:**
```bash
mkdir C:\TestFolder
curl -X POST http://127.0.0.1:8000/add_folder \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\TestFolder"}'
```

**Expected Response:**
- [ ] Status code: 200
- [ ] status is "success"
- [ ] files_indexed >= 0

### 13. Categorize Endpoint ✓

**Test:**
```bash
curl -X POST http://127.0.0.1:8000/categorize \
  -H "Content-Type: application/json" \
  -d '{"category_description":"Python sorting algorithms","max_files":10}'
```

**Expected Response:**
- [ ] Status code: 200 (or 501 if service not available)
- [ ] status is "success"
- [ ] files is an array
- [ ] Each file has: path, summary, relevance_score

## Interactive API Documentation Test

**Test:**
```
Open http://127.0.0.1:8000/docs
```

- [ ] Page loads without errors
- [ ] Swagger UI is visible
- [ ] All endpoints listed
- [ ] Can expand each endpoint
- [ ] Request/response schemas visible
- [ ] "Try it out" button works
- [ ] Can execute requests directly

## Real-Time File Monitoring Test

### 1. Create New File ✓

```bash
# Create a new file in Desktop
"Test content about Python algorithms" | Out-File "C:\Users\Mohammad\Desktop\test_new.txt"
```

**Check:**
- [ ] Console shows "New file detected: ...test_new.txt"
- [ ] File appears in search results within 1 second
- [ ] File shows up in `/list` endpoint

### 2. Modify File ✓

```bash
# Modify the file
"Updated content about Python sorting" | Out-File "C:\Users\Mohammad\Desktop\test_new.txt"
```

**Check:**
- [ ] Console shows "File modified: ...test_new.txt"
- [ ] Summary updated in database
- [ ] Changes reflected in search results

### 3. Delete File ✓

```bash
Remove-Item "C:\Users\Mohammad\Desktop\test_new.txt"
```

**Check:**
- [ ] Console shows "File deleted: ...test_new.txt"
- [ ] File no longer appears in search results
- [ ] File removed from database

## Performance Tests

### 1. Search Speed ✓

Measure time for search:
```bash
Measure-Command {
  curl -X POST http://127.0.0.1:8000/search `
    -H "Content-Type: application/json" `
    -d '{\"query\":\"python\",\"k\":5}'
} | Select-Object TotalMilliseconds
```

**Expected:**
- [ ] Takes 500-1000 milliseconds

### 2. Ask Speed ✓

Measure time for ask:
```bash
Measure-Command {
  curl -X POST http://127.0.0.1:8000/ask `
    -H "Content-Type: application/json" `
    -d '{\"query\":\"What Python files do I have?\"}'
} | Select-Object TotalMilliseconds
```

**Expected:**
- [ ] Takes 2000-5000 milliseconds (includes LLM time)

### 3. Indexing Speed ✓

Add a new file and measure indexing time:

**Check:**
- [ ] New file indexed within 1 second
- [ ] Summary generated quickly
- [ ] File searchable immediately

## Error Handling Tests

### 1. Invalid Path ✓

```bash
curl -X POST http://127.0.0.1:8000/list \
  -H "Content-Type: application/json" \
  -d '{"path":"C:\\NonExistent\\Path"}'
```

**Expected:**
- [ ] Status code: 404
- [ ] error message mentioning "Path does not exist"

### 2. Invalid Operation ✓

```bash
curl -X POST http://127.0.0.1:8000/move \
  -H "Content-Type: application/json" \
  -d '{
    "source":"C:\\NonExistent\\file.txt",
    "destination":"C:\\Other\\file.txt"
  }'
```

**Expected:**
- [ ] Status code: 404 or 500
- [ ] Proper error message

### 3. Ollama Disconnection ✓

Stop Ollama and try:
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query":"Test"}'
```

**Expected:**
- [ ] Status code: 500
- [ ] Error message about connection
- [ ] Server continues running (doesn't crash)

**Restart Ollama:**
- [ ] Server recovers after Ollama restarts

## Database Verification

### SQLite Database

```bash
sqlite3 filegpt_metadata.db
```

- [ ] `files` table exists
- [ ] Can query: `SELECT COUNT(*) FROM files;`
- [ ] Returns count > 0

### ChromaDB

Verify by checking:
- [ ] `backend/chroma_db/` exists
- [ ] Contains database files
- [ ] `/stats` endpoint shows chroma_chunks > 0

### BM25 Index

- [ ] `backend/bm25_index.pkl` exists
- [ ] File size > 0
- [ ] `/stats` endpoint shows bm25_chunks > 0

## Cleanup

After verification:

```bash
# Remove test folders
Remove-Item "C:\Users\Mohammad\Desktop\TestFolder123" -Recurse
Remove-Item "C:\Users\Mohammad\Desktop\TestFolder456" -Recurse
Remove-Item "C:\TestFolder" -Recurse
```

## Final Verification Summary

### All Tests Passed? ✓

If you've checked all boxes:

- [ ] All 13 API endpoint tests passed
- [ ] API documentation loads correctly
- [ ] Real-time file monitoring works
- [ ] Performance is acceptable
- [ ] Error handling works
- [ ] Databases created correctly

**Congratulations! FileGPT Backend is fully operational!** 🎉

### Next Steps

1. Connect frontend to the API
2. Test with actual file collections
3. Monitor performance with varied workloads
4. Customize monitored folders as needed
5. Deploy to production

---

## Troubleshooting Failed Tests

**If any test fails:**

1. **Check console logs** - Look for error messages
2. **Verify Ollama** - `ollama list` should show model
3. **Check file permissions** - Can you read monitored folders?
4. **Verify dependencies** - `pip list | grep -E "fastapi|chromadb|langchain"`
5. **Check ports** - Is 8000 available? `netstat -ano | findstr :8000`
6. **Review documentation** - See SETUP_GUIDE.md for solutions

## Contact & Support

Refer to:
- QUICKSTART.md - 5-minute quick start
- SETUP_GUIDE.md - Complete documentation
- IMPLEMENTATION_SUMMARY.md - Architecture details

**All components tested and ready!** ✨
