# AI File Categorization Guide

## 🎯 Overview

FileGPT now includes **intelligent file categorization** powered by AI. You can organize files using natural language commands like:

- "Put all sorting algorithms into one folder"
- "Group all React components together"
- "Find all configuration files"

## 📋 How It Works

1. **AI Search**: Uses hybrid RAG to find potentially relevant files
2. **LLM Classification**: Evaluates each file using `llama3:8b` to determine if it matches your category
3. **Confidence Scoring**: Assigns a confidence score (0.0-1.0) to each match
4. **Auto-Organization**: Optionally moves matching files to a destination folder

## 🔌 API Endpoints

### 1. `/categorize` - Find Files by Category

Find all files matching a natural language description.

**Request:**
```json
POST /categorize
{
  "category_description": "sorting algorithms",
  "search_path": "C:\\Users\\Mohammad\\Projects",  // Optional: limit search scope
  "max_files": 100  // Optional: max files to evaluate
}
```

**Response:**
```json
{
  "category": "sorting algorithms",
  "matched_files": [
    {
      "path": "C:\\Projects\\quicksort.py",
      "filename": "quicksort.py",
      "summary": "Implementation of quicksort algorithm...",
      "confidence": 0.95,
      "search_score": 0.88
    },
    {
      "path": "C:\\Projects\\mergesort.cpp",
      "filename": "mergesort.cpp",
      "summary": "Merge sort implementation...",
      "confidence": 0.92,
      "search_score": 0.85
    }
  ],
  "total_evaluated": 45,
  "total_matched": 2
}
```

---

### 2.`/organize` - Auto-Organize Files

Automatically move files matching a category into a folder.

**Request:**
```json
POST /organize
{
  "category_description": "sorting algorithms",
  "destination_folder": "C:\\SortingAlgorithms",
  "search_path": null,  // Optional: search all indexed files
  "min_confidence": 0.6,  // Only move files with confidence >= 0.6
  "dry_run": false  // Set to true to preview without moving
}
```

**Response:**
```json
{
  "status": "success",
  "category": "sorting algorithms",
  "destination": "C:\\SortingAlgorithms",
  "evaluated": 45,
  "matched": 2,
  "files_moved": [
    {
      "original_path": "C:\\Projects\\quicksort.py",
      "new_path": "C:\\SortingAlgorithms\\quicksort.py",
      "confidence": 0.95,
      "dry_run": false
    },
    {
      "original_path": "C:\\Projects\\mergesort.cpp",
      "new_path": "C\\SortingAlgorithms\\mergesort.cpp",
      "confidence": 0.92,
      "dry_run": false
    }
  ],
  "errors": []
}
```

**Dry Run Mode:**
Set `"dry_run": true` to see what would be moved without actually moving files.

---

### 3. `/suggest_categories` - Get AI Category Suggestions

Get AI-suggested categories for organizing your files.

**Request:**
```json
POST /suggest_categories
{
  "file_paths": [
    "C:\\Projects\\app.py",
    "C:\\Projects\\utils.py",
    "C:\\Projects\\config.json",
    "C:\\Projects\\react_component.jsx"
  ]
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "category": "Python Backend Code",
      "description": "Python scripts for backend logic and utilities"
    },
    {
      "category": "Frontend Components",
      "description": "React/JSX component files"
    },
    {
      "category": "Configuration Files",
      "description": "JSON configuration and settings files"
    }
  ],
  "count": 3
}
```

---

## 💬 Natural Language Examples

### Example 1: Organize Python Files
```bash
curl -X POST http://localhost:8000/organize ^
  -H "Content-Type: application/json" ^
  -d "{\"category_description\": \"Python utility functions\", \"destination_folder\": \"C:\\Utils\"}"
```

### Example 2: Find Machine Learning Code
```bash
curl -X POST http://localhost:8000/categorize ^
  -H "Content-Type: application/json" ^
  -d "{\"category_description\": \"machine learning models\"}"
```

### Example 3: Group React Components
```bash
curl -X POST http://localhost:8000/organize ^
  -H "Content-Type: application/json" ^
  -d "{\"category_description\": \"React UI components\", \"destination_folder\": \"C:\\Components\", \"min_confidence\": 0.7}"
```

### Example 4: Find Configuration Files
```bash
curl -X POST http://localhost:8000/categorize ^
  -H "Content-Type: application/json" ^
  -d "{\"category_description\": \"configuration and settings files\"}"
```

---

## ⚙️ Configuration Options

### `min_confidence`
- **Range**: 0.0 to 1.0
- **Default**: 0.6
- **Recommendation**: 
  - Use 0.5-0.6 for broad categorization
  - Use 0.7-0.8 for precise categorization
  - Use 0.9+ for very strict matching

### `dry_run`
- **Default**: false
- **Recommendation**: Always test with `dry_run=true` first to preview results

### `max_files`
- **Default**: 100
- **Recommendation**: Lower values (20-50) for faster processing

---

## 🎨 Chat Interface Integration

You can integrate these endpoints into a chat interface so users can say:

**User**: "Put all my sorting algorithms into a folder"

**Backend Logic**:
1. Parse intent → category: "sorting algorithms"
2. Generate destination → "C:\\Users\\Mohammad\\Desktop\\SortingAlgorithms"
3. Call `/organize` with `dry_run=true`
4. Show preview to user
5. On confirmation, call with `dry_run=false`

**Example Chat Flow**:
```
User: "Organize all my Python scripts about databases"

Bot: "I found 5 files related to database Python scripts:
      - db_connector.py (95% confidence)
      - mysql_utils.py (88% confidence)
      - database_models.py (82% confidence)
      - query_builder.py (76% confidence)
      - db_config.py (71% confidence)
      
      Would you like me to move them to 'C:\\DatabaseScripts'?"

User: "Yes"

Bot: "✓ Moved 5 files to C:\\DatabaseScripts"
```

---

## 🧠 How the AI Classifies Files

For each file, the LLM evaluates:
1. **File path**: Does the filename/path suggest relevance?
2. **Summary**: Does the AI-generated summary match the category?
3. **Content**: Does the actual code/content match?

**Prompt Template:**
```
Determine if the following file belongs to the category: "sorting algorithms"

File: C:\quicksort.py
Summary: Implementation of quicksort algorithm with pivot selection

Content Preview:
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    ...

Question: Does this file belong to the category "sorting algorithms"?

Response format:
MATCH: [YES or NO]
CONFIDENCE: [0.0 to 1.0]
REASON: [brief explanation]
```

---

## 📊 Performance

- **Categorization Speed**: ~2-5 files/second (depends on LLM speed)
- **Accuracy**: ~85-95% with proper category descriptions
- **Best Categories**: Specific technical terms (e.g., "merge sort algorithm" vs "code")

---

## 💡 Tips for Better Results

1. **Be Specific**: "React functional components" > "React files"
2. **Use Technical Terms**: "authentication middleware" > "login stuff"
3. **Test with Dry Run**: Always preview before moving files
4. **Adjust Confidence**: Lower for exploration, higher for precision
5. **Limit Scope**: Use `search_path` to search specific directories

---

## 🚀 Integration Example

### Python Frontend:
```python
import requests

# Find files
response = requests.post("http://localhost:8000/categorize", json={
    "category_description": user_input,
    "max_files": 50
})

matches = response.json()["matched_files"]

# Show user and confirm
if confirm_dialog(matches):
    # Organize files
    requests.post("http://localhost:8000/organize", json={
        "category_description": user_input,
        "destination_folder": generate_folder_name(user_input),
        "min_confidence": 0.6,
        "dry_run": False
    })
```

### JavaScript Frontend:
```javascript
// Categorize files
const response = await fetch('http://localhost:8000/categorize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    category_description: userInput,
    max_files: 50
  })
});

const data = await response.json();
console.log(`Found ${data.total_matched} matching files`);
```

---

## 🎯 Use Cases

1. **Code Organization**: Group files by language, framework, or functionality
2. **Document Sorting**: Categorize by topic, project, or file type
3. **Project Cleanup**: Find and organize related files across directories
4. **Research**: Group papers, notes, or data files by topic
5. **Media Organization**: Categorize images, videos by content (with proper descriptions)

Ready to organize your files with AI! 🚀
