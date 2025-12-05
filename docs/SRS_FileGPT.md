# Software Requirements Specification
# FileGPT: AI-Powered File Search and Management System

**Version 1.0**  
**Date:** November 26, 2025

---

## Table of Contents

1. [INTRODUCTION](#1-introduction)
   - 1.1. Purpose of Document
   - 1.2. Intended Audience
   - 1.3. Abbreviations
   - 1.4. Document Convention
2. [OVERALL SYSTEM DESCRIPTION](#2-overall-system-description)
   - 2.1. Project Background
   - 2.2. Project Scope
   - 2.3. Not In Scope
   - 2.4. Project Objectives
   - 2.5. Stakeholders
   - 2.6. Operating Environment
   - 2.7. System Constraints
   - 2.8. Assumptions & Dependencies
3. [EXTERNAL INTERFACE REQUIREMENTS](#3-external-interface-requirements)
   - 3.1. Hardware Interfaces
   - 3.2. Software Interfaces
   - 3.3. Communications Interfaces
4. [FUNCTIONAL REQUIREMENTS](#4-functional-requirements)
   - 4.1. Functional Hierarchy
   - 4.2. Use Cases
5. [NON-FUNCTIONAL REQUIREMENTS](#5-non-functional-requirements)
   - 5.1. Performance Requirements
   - 5.2. Safety Requirements
   - 5.3. Security Requirements
   - 5.4. User Documentation
6. [REFERENCES](#6-references)
7. [APPENDICES](#7-appendices)

---

## 1. INTRODUCTION

### 1.1. Purpose of Document

The purpose of this Software Requirements Specification (SRS) document is to provide a detailed and structured outline of the functional and non-functional requirements for **FileGPT**, an AI-powered file search and management system. This document serves as a comprehensive guide for all stakeholders, including developers, users, and project evaluators, to ensure a shared understanding of the system's goals, functionalities, and constraints.

**Objectives:**
- To provide a clear communication framework among stakeholders
- To act as a reference document for developers during the system's design, implementation, and testing phases
- To ensure that the system's design and implementation align with user needs and privacy-first principles
- To establish a foundation for requirement traceability throughout the project lifecycle

### 1.2. Intended Audience

- **End Users**: Individuals seeking efficient, privacy-first file management and search
- **Developers**: Software engineers implementing and maintaining the system
- **Project Evaluators**: Academic supervisors and jury members assessing the project
- **Students of FAST-NU**: Potential users and contributors
- **Quality Assurance Team**: Testers validating system functionality
- **Documentation Team**: Technical writers creating user manuals

### 1.3. Abbreviations

- **RAG** = Retrieval-Augmented Generation
- **LLM** = Large Language Model
- **API** = Application Programming Interface
- **UI** = User Interface
- **NLP** = Natural Language Processing
- **BM25** = Best Matching 25 (keyword search algorithm)
- **CRUD** = Create, Read, Update, Delete
- **SRS** = Software Requirements Specification

### 1.4. Document Convention

- **Font Family**: Arial
- **Font Size**: 12 for headings, 10 for body content
- **Code Blocks**: Courier New, 9pt
- **Emphasis**: Bold for key terms, Italic for file/directory names

---

## 2. OVERALL SYSTEM DESCRIPTION

### 2.1. Project Background

In the digital age, users accumulate vast amounts of files across their systems, making it increasingly difficult to locate specific documents, code files, or research papers efficiently. Traditional file explorers rely on exact filename matches or basic keyword searches, which often fail to understand user intent or provide contextual answers about file content.

**Problem Statement:**
- Traditional search tools require exact filename matches
- Users cannot ask natural language questions about their files
- No intelligent categorization or organization assistance
- Privacy concerns with cloud-based solutions
- Lack of content understanding in search results

FileGPT addresses these challenges by combining cutting-edge AI technologies with privacy-first, fully offline operation to create an intelligent file management assistant that understands natural language queries and provides contextual answers from file content.

### 2.2. Project Scope

FileGPT aims to revolutionize personal file management by providing an AI-powered, privacy-first platform that enables users to search, organize, and interact with their files using natural language. The system operates entirely offline, ensuring complete data privacy.

**Included Functionalities:**

**Core Search Features:**
- Hybrid RAG search combining semantic understanding and keyword matching
- Natural language question answering from file content
- AI-powered intent classification (SEARCH, ACTION, CHAT, MULTI)
- Real-time file indexing with background monitoring

**AI Capabilities:**
- Multi-intent query processing
- Intelligent file categorization
- Automated content summarization
- Context-aware responses with source citations

**File Management:**
- Create, move, rename, and delete operations
- AI-suggested organization workflows
- Real-time file system synchronization
- Metadata extraction and storage

**User Interface:**
- Desktop application (Tauri-based)
- Intuitive chat-like interface
- File preview and quick actions
- Organization approval workflows

### 2.3. Not In Scope

- Cloud synchronization or remote storage
- Multi-user collaboration features
- File sharing or permission management
- Cross-device synchronization
- Mobile applications (iOS/Android)
- Network file system support
- Real-time collaborative editing

### 2.4. Project Objectives

**User Objectives:**
- Search files using natural language questions
- Get AI-generated answers from file content
- Organize files with AI assistance
- Maintain complete data privacy (offline operation)
- Access file metadata and summaries
- Perform file operations through chat interface

**System Objectives:**
- Achieve 95%+ accuracy in intent classification
- Index 1000+ files within 10 minutes
- Respond to queries within 3 seconds
- Maintain 99% uptime during active use
- Support 10+ file formats (PDF, DOCX, TXT, code files, etc.)
- Provide transparent AI decision-making

### 2.5. Stakeholders

- **End Users**: Individual PC users seeking better file management
- **Developers**: Backend (Python/FastAPI) and Frontend (React/Tauri) teams
- **Database Administrator**: Managing ChromaDB and SQLite
- **AI/ML Engineer**: Implementing and optimizing LLM integration
- **Project Supervisor**: Dr. Shahbaz Siddiqui
- **Academic Institution**: FAST-NU
- **Quality Assurance**: Testing team

### 2.6. Operating Environment

**Software Environment:**
- **Operating Systems**: Windows 10/11, macOS 10.13+, Linux (kernel 4.x+)
- **Backend**: Python 3.12+, FastAPI, Uvicorn
- **Frontend**: Tauri (Rust + Web), React 18+, Vite
- **Database**: ChromaDB (vector store), SQLite (metadata)
- **AI**: Ollama (qwen2.5:0.5b)

**Hardware Environment:**
- Minimum 8GB RAM (16GB recommended)
- Quad-core processor (Intel i5/AMD Ryzen 5 or better)
- 10GB free disk space for application and indexes
- SSD recommended for optimal indexing performance

**Network Requirements:**
- Internet connection required only for initial setup (Ollama model download)
- Fully offline operation after setup

### 2.7. System Constraints

**Technical Constraints:**
- LLM model size limited by available RAM
- Indexing speed dependent on disk I/O performance
- Vector database size grows with number of files
- Real-time monitoring requires background processes

**Operational Constraints:**
- Ollama must be running locally for AI features
- File watcher may impact system resources on large directories
- Initial indexing may take time for large file collections

**Platform Constraints:**
- Desktop-only application (no mobile version)
- Requires modern desktop OS with GUI support
- Some file formats may require additional libraries

**Privacy Constraints:**
- No external API calls except Ollama (local)
- No telemetry or usage tracking
- All data stored locally

### 2.8. Assumptions & Dependencies

**Assumptions:**
- Users have basic computer literacy
- Users value privacy and prefer offline solutions
- Files are stored locally on the system
- Users have permission to access and modify files
- Ollama service is properly installed and configured

**Dependencies:**
- **Ollama**: Required for LLM inference (qwen2.5:0.5b)
- **ChromaDB**: Vector database for semantic search
- **FastAPI**: Backend framework
- **Tauri**: Cross-platform desktop framework
- **LangChain**: LLM orchestration and structured output
- **Watchdog**: File system monitoring
- **Sentence Transformers**: Embedding generation

---

## 3. EXTERNAL INTERFACE REQUIREMENTS

### 3.1. Hardware Interfaces

**Desktop Computer:**
- **Minimum RAM**: 8GB
- **Processor**: Quad-core 2.0GHz or better
- **Storage**: 10GB free space (SSD recommended)
- **Display**: 1280x720 minimum resolution

**Peripheral Devices:**
- Standard keyboard and mouse/trackpad for navigation
- Display capable of rendering modern web content

### 3.2. Software Interfaces

**Backend Components:**

1. **Ollama (Local LLM)**
   - Purpose: AI inference for query understanding and answer generation
   - Models: qwen2.5:0.5b (required)
   - Communication: HTTP REST API (localhost:11434)

2. **ChromaDB (Vector Database)**
   - Purpose: Store and query document embeddings
   - Version: 0.4.18
   - Storage: Local filesystem

3. **SQLite (Metadata Database)**
   - Purpose: Store file metadata and summaries
   - Storage: Local file (filegpt_metadata.db)

4. **FastAPI Backend**
   - Purpose: REST API server
   - Port: 8000 (configurable)
   - Endpoints: /ask, /search, /categorize, /organize, etc.

**Frontend Components:**

5. **Tauri Desktop Application**
   - Purpose: Native desktop wrapper
   - Technology: Rust + Web (React)

6. **React UI**
   - Purpose: User interface
   - Build Tool: Vite
   - State Management: React hooks

**External Libraries:**
- **LangChain**: LLM orchestration (v0.3.16)
- **Sentence Transformers**: Text embeddings (v2.7.0)
- **Watchdog**: File monitoring (v3.0.0)

### 3.3. Communications Interfaces

**Internal Communication:**
- **Frontend ↔ Backend**: HTTP REST API (JSON)
  - Base URL: `http://127.0.0.1:8000`
  - Content-Type: application/json
  
- **Backend ↔ Ollama**: HTTP REST API
  - URL: `http://localhost:11434`
  - Model inference and embeddings

- **Backend ↔ ChromaDB**: Direct Python API calls
  - In-process communication

**Data Formats:**
- Request/Response: JSON
- File Content: UTF-8 encoded text
- Embeddings: Float32 arrays
- Metadata: SQLite binary

---

## 4. FUNCTIONAL REQUIREMENTS

### 4.1. Functional Hierarchy

```
1. User Interface
   1.1. Chat Interface
   1.2. File Explorer Integration
   1.3. Settings Panel
   1.4. Organization Approval Modal

2. Search & Query
   2.1. Natural Language Query Processing
        2.1.1. Intent Classification (SEARCH/ACTION/CHAT/MULTI)
        2.1.2. Parameter Extraction
   2.2. Hybrid Search
        2.2.1. Semantic Search (ChromaDB)
        2.2.2. Keyword Search (BM25)
        2.2.3. Result Ranking & Fusion
   2.3. Answer Generation
        2.3.1. Context Preparation
        2.3.2. LLM Prompting
        2.3.3. Source Attribution

3. File Management
   3.1. Indexing Pipeline
        3.1.1. File Discovery
        3.1.2. Content Extraction
        3.1.3. Summarization
        3.1.4. Embedding Generation
        3.1.5. Database Storage
   3.2. File Operations
        3.2.1. Create Folder
        3.2.2. Move Files
        3.2.3. Rename Files
        3.2.4. Delete Files
   3.3. Real-time Monitoring
        3.3.1. File Change Detection
        3.3.2. Automatic Re-indexing
        3.3.3. Index Synchronization

4. AI-Powered Organization
   4.1. File Categorization
        4.1.1. Category Detection
        4.1.2. Confidence Scoring
   4.2. Organization Suggestions
        4.2.1. Destination Recommendation
        4.2.2. Category Assignment
   4.3. Batch Operations
        4.3.1. Multi-file Selection
        4.3.2. Approval Workflow
        4.3.3. Execution & Rollback

5. Data Management
   5.1. Metadata Storage (SQLite)
   5.2. Vector Storage (ChromaDB)
   5.3. File System Sync
   5.4. Backup & Recovery

6. System Administration
   6.1. Folder Monitoring
   6.2. Index Statistics
   6.3. System Health
```

### 4.2. Use Cases

#### UC-USER-01: Natural Language File Search

**Use Case ID:** UC-USER-01  
**Actors:** User  
**Feature:** Search files using natural language queries  
**Precondition:**
- Application is running
- At least one folder has been indexed
- Ollama service is running

**Scenarios:**

| Step# | Action | Software Reaction |
|-------|--------|-------------------|
| 1 | User enters query: "Show me Python files about sorting" | System classifies intent as SEARCH |
| 2 | System performs hybrid search | Retrieves relevant files using semantic + keyword search |
| 3 | System generates AI response | LLM creates answer citing specific files |
| 4 | User views results | Display shows answer with clickable file references |

**Alternate Scenarios:**
- 1a: If no relevant files found, system responds: "No relevant files found. Try adding more folders."
- 2a: If Ollama is not running, system shows error: "AI service unavailable. Please start Ollama."

**Post Conditions:**
- User receives contextual answer with file sources
- Search results are cached for quick re-access
- Query is logged for future improvements

**Cross References:** UC-USER-02, UC-USER-05

---

#### UC-USER-02: Multi-Intent Query Processing

**Use Case ID:** UC-USER-02  
**Actors:** User  
**Feature:** Process compound queries with multiple intents  
**Precondition:**
- Application is running
- Router service is initialized
- Folders are indexed

**Scenarios:**

| Step# | Action | Software Reaction |
|-------|--------|-------------------|
| 1 | User enters: "Find expense.xlsx and tell me the total" | System detects MULTI intent (SEARCH + follow-up) |
| 2 | System executes search | Locates expense.xlsx file |
| 3 | System reads file content | Extracts data from spreadsheet |
| 4 | System answers follow-up | LLM calculates and responds with total |

**Alternate Scenarios:**
- 1a: If file not found, system responds: "File not found. Would you like to search by content?"
- 3a: If file format unsupported, system notes: "Could not read file format."

**Post Conditions:**
- Both search and question are answered in single response
- User receives comprehensive answer with sources
- File content is cached for follow-up queries

**Cross References:** UC-USER-01, UC-USER-04

---

#### UC-USER-03: AI-Powered File Organization

**Use Case ID:** UC-USER-03  
**Actors:** User  
**Feature:** Organize files using AI categorization  
**Precondition:**
- Application is running
- Files are indexed
- Categorization service is active

**Scenarios:**

| Step# | Action | Software Reaction |
|-------|--------|-------------------|
| 1 | User enters: "Organize my code files" | System classifies as ACTION (organize) |
| 2 | System scans for code files | AI identifies files by extension and content |
| 3 | System suggests categories | Displays: "Found 15 Python files, 8 JavaScript files" |
| 4 | User reviews suggestions | Modal shows proposed file moves |
| 5 | User approves organization | System moves files to destinations |

**Alternate Scenarios:**
- 2a: If no files match category, system responds: "No files found matching criteria."
- 4a: User can modify destination paths before approving
- 5a: User can cancel operation, no files are moved

**Post Conditions:**
- Files are organized into appropriate folders
- Index is updated to reflect changes
- Operation is logged for potential undo

**Cross References:** UC-USER-04, UC-SYS-02

---

#### UC-USER-04: Ask Questions About File Content

**Use Case ID:** UC-USER-04  
**Actors:** User  
**Feature:** Get AI answers from indexed file content  
**Precondition:**
- Files are indexed with summaries
- Ollama is running
- User has asked a question

**Scenarios:**

| Step# | Action | Software Reaction |
|-------|--------|-------------------|
| 1 | User asks: "What sorting algorithms are in my code?" | System performs semantic search |
| 2 | System retrieves relevant code files | ChromaDB returns top-k matches |
| 3 | System builds context | Combines file content + summaries |
| 4 | LLM generates answer | Cites specific files and line numbers |
| 5 | User views detailed response | UI shows answer with file links |

**Alternate Scenarios:**
- 1a: If question is too vague, system asks for clarification
- 2a: If no relevant content, system suggests rephrasing query

**Post Conditions:**
- User receives answer with source citations
- Can click files to open them directly
- Related files shown for exploration

**Cross References:** UC-USER-01, UC-USER-02

---

#### UC-USER-05: Add Folder for Indexing

**Use Case ID:** UC-USER-05  
**Actors:** User  
**Feature:** Add new folder to monitoring and index its files  
**Precondition:**
- Application is running
- User has folder path ready

**Scenarios:**

| Step# | Action | Software Reaction |
|-------|--------|-------------------|
| 1 | User clicks "Add Folder" | System shows folder picker dialog |
| 2 | User selects folder | System validates path exists |
| 3 | System starts indexing | Background process scans all files |
| 4 | Progress shown to user | UI displays: "Indexed 50/200 files..." |
| 5 | Indexing completes | System shows summary: "Indexed 200 files" |

**Alternate Scenarios:**
- 2a: If folder doesn't exist, show error
- 3a: If folder is already monitored, ask to re-index
- 4a: User can cancel indexing mid-process

**Post Conditions:**
- Folder is added to monitoring list
- All files are indexed and searchable
- File watcher monitors for changes

**Cross References:** UC-SYS-01, UC-SYS-02

---

#### UC-SYS-01: Real-time File Monitoring

**Use Case ID:** UC-SYS-01  
**Actors:** System (Background Process)  
**Feature:** Automatically detect and index file changes  
**Precondition:**
- File watcher service is running
- Folders are being monitored

**Scenarios:**

| Step# | Action | Software Reaction |
|-------|--------|-------------------|
| 1 | User creates/modifies a file | File watcher detects change event |
| 2 | System validates file type | Checks if file should be indexed |
| 3 | System re-indexes file | Updates embeddings and metadata |
| 4 | Index is updated | ChromaDB and SQLite reflect changes |

**Alternate Scenarios:**
- 2a: If file is ignored type (.tmp, etc.), skip indexing
- 3a: If indexing fails, retry after 30 seconds

**Post Conditions:**
- New/modified files are searchable immediately
- Index stays synchronized with filesystem
- No manual re-indexing needed

**Cross References:** UC-USER-05

---

#### UC-SYS-02: Index Synchronization

**Use Case ID:** UC-SYS-02  
**Actors:** System  
**Feature:** Keep search index synchronized with file operations  
**Precondition:**
- File operation is performed

**Scenarios:**

| Step# | Action | Software Reaction |
|-------|--------|-------------------|
| 1 | User moves/renames/deletes file | Operation is executed |
| 2 | System detects operation | Triggers index update |
| 3 | Old entry removed from index | ChromaDB and SQLite updated |
| 4 | New entry added (if applicable) | File re-indexed at new location |

**Alternate Scenarios:**
- 2a: If operation fails, index remains unchanged
- 3a: If file not in index, only add new entry

**Post Conditions:**
- Index accurately reflects filesystem state
- No orphaned entries in database
- Search returns current file locations

**Cross References:** UC-USER-03, UC-SYS-01

---

## 5. NON-FUNCTIONAL REQUIREMENTS

### 5.1. Performance Requirements

**Response Time:**
- Search queries must return results within **3 seconds** (95th percentile)
- AI answer generation must complete within **5 seconds** (95th percentile)
- File indexing must process at least **100 files per minute**
- File operations (move/rename/delete) must complete within **1 second**

**Throughput:**
- System must handle **1,000+ concurrent file monitoring events**
- Database must support **100,000+ indexed files** without degradation
- Hybrid search must query **10,000+ documents** within time limits

**Resource Usage:**
- Memory usage should not exceed **2GB** during normal operation
- CPU usage should average **< 10%** when idle
- Disk I/O should be optimized to prevent system slowdown

**Scalability:**
- System should gracefully handle indexing of **500,000+ files**
- Vector database should efficiently scale to **1GB+ of embeddings**

### 5.2. Safety Requirements

**Data Protection:**
- Automatic backup of metadata database every **24 hours**
- File operations must be **reversible** (undo capability)
- System must prevent accidental deletion with confirmation dialogs
- All file operations must be **logged** for audit trail

**Error Handling:**
- System must gracefully handle corrupted files without crashing
- Failed indexing operations must not corrupt the database
- Network errors (Ollama unavailable) must show user-friendly messages
- System must recover from unexpected shutdown without data loss

**File Integrity:**
- Original files must **never be modified** during indexing
- File operations must preserve file attributes and permissions
- System must detect and handle file access permission errors

### 5.3. Security Requirements

**Data Privacy:**
- **All data remains local** - no external transmission except to Ollama (localhost)
- No telemetry or analytics data collection
- No cloud synchronization or remote access

**Authentication:**
- Application runs with user's OS-level permissions
- No separate authentication system required (single-user desktop app)

**Data Encryption:**
- Sensitive metadata can be stored encrypted (optional feature)
- File paths and content remain in clear text for performance

**Access Control:**
- System respects OS-level file permissions
- Cannot access files without user permission

### 5.4. User Documentation

**User Manual:**
- Comprehensive guide covering all features
- Step-by-step tutorials for common tasks
- Troubleshooting section for common issues

**In-App Help:**
- Context-sensitive help tooltips
- "Getting Started" tutorial on first launch
- FAQ section accessible from settings

**Technical Documentation:**
- API documentation for backend endpoints
- Architecture diagrams explaining system design
- Developer guide for extending functionality

**Video Tutorials:**
- Quick start guide (5 minutes)
- Advanced features walkthrough (15 minutes)
- File organization workflow demo (10 minutes)

---

## 6. REFERENCES

### Academic Papers

1. **Retrieval-Augmented Generation**
   - Lewis, P., et al. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." *NeurIPS 2020*. [Online]. Available: https://arxiv.org/abs/2005.11401

2. **BM25 Algorithm**
   - Robertson, S., & Zaragoza, H. (2009). "The Probabilistic Relevance Framework: BM25 and Beyond." *Foundations and Trends in Information Retrieval*, 3(4), 333-389.

### Technical Documentation

3. **LangChain**
   - LangChain Documentation. "Structured Output with Pydantic." [Online]. Available: https://python.langchain.com/docs/how_to/structured_output

4. **ChromaDB**
   - ChromaDB Documentation. "Getting Started." [Online]. Available: https://docs.trychroma.com/

5. **Ollama**
   - Ollama Documentation. "Running LLMs Locally." [Online]. Available: https://ollama.ai/

6. **Tauri**
   - Tauri Documentation. "Build Cross-Platform Apps." [Online]. Available: https://tauri.app/

### Software Frameworks

7. **FastAPI**
   - Ramírez, S. (2024). *FastAPI Framework*. [Online]. Available: https://fastapi.tiangolo.com/

8. **React**
   - Meta Open Source. *React Documentation*. [Online]. Available: https://react.dev/

---

## 7. APPENDICES

### Appendix A: System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Tauri Frontend                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Chat UI     │  │ File Explorer│  │  Settings    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/REST
                         ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend Server                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │          Router Service (LangChain)             │    │
│  │   SEARCH │ ACTION │ CHAT │ MULTI Intents        │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                                │
│  ┌──────────┬──────────┴──────────┬──────────┐         │
│  │ Search   │  Categorization     │  File    │         │
│  │ Engine   │  Service            │  Watcher │         │
│  └──────────┴─────────────────────┴──────────┘         │
└──────┬─────────────┬──────────────┬────────────────────┘
       │             │              │
       ▼             ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ ChromaDB │  │ SQLite   │  │  Ollama  │  │   File   │
│ (Vector  │  │(Metadata)│  │  (LLM)   │  │  System  │
│  Store)  │  │          │  │          │  │          │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### Appendix B: Database Schema

**SQLite Metadata Database:**

```sql
-- File Metadata Table
CREATE TABLE file_metadata (
    file_path TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_type TEXT,
    file_size INTEGER,
    created_date TEXT,
    modified_date TEXT,
    summary TEXT,
    indexed_date TEXT,
    word_count INTEGER
);

-- Folder Monitoring Table
CREATE TABLE monitored_folders (
    folder_path TEXT PRIMARY KEY,
    added_date TEXT,
    last_scan_date TEXT,
    file_count INTEGER
);
```

**ChromaDB Collections:**
- Collection Name: `file_embeddings`
- Embedding Model: `all-MiniLM-L6-v2`
- Dimensions: 384
- Distance Metric: Cosine similarity

### Appendix C: API Endpoints

**Core Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check |
| `/ask` | POST | Natural language query with intent routing |
| `/search` | POST | Hybrid search (semantic + keyword) |
| `/add_folder` | POST | Add folder for monitoring and indexing |
| `/stats` | GET | System statistics |
| `/categorize` | POST | AI-powered file categorization |
| `/organize` | POST | Execute organization workflow |
| `/create_folder` | POST | Create new folder |
| `/move` | POST | Move files or folders |
| `/rename` | POST | Rename files or folders |
| `/delete` | DELETE | Delete files or folders |

### Appendix D: Supported File Formats

**Text Documents:**
- PDF (`.pdf`)
- Microsoft Word (`.docx`, `.doc`)
- Plain text (`.txt`)
- Markdown (`.md`)
- Rich Text Format (`.rtf`)

**Code Files:**
- Python (`.py`)
- JavaScript/TypeScript (`.js`, `.ts`, `.jsx`, `.tsx`)
- Java (`.java`)
- C/C++ (`.c`, `.cpp`, `.h`)
- HTML/CSS (`.html`, `.css`)
- JSON/XML (`.json`, `.xml`)

**Other Formats:**
- CSV (`.csv`)
- Log files (`.log`)

### Appendix E: Glossary

- **Embedding**: Numerical vector representation of text for semantic search
- **Hybrid Search**: Combined semantic and keyword-based search
- **Intent Classification**: Determining user's goal from natural language
- **RAG**: Using retrieved documents to enhance LLM responses
- **Vector Database**: Database optimized for similarity search on embeddings
- **File Watcher**: Background service monitoring filesystem changes

---

**Document Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-26 | Development Team | Initial release |

---

**End of Software Requirements Specification**
