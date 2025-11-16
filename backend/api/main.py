# backend/api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

# --- Add the 'services' directory to the Python path ---
# This is a crucial step so that main.py can find your service modules
script_dir = os.path.dirname(__file__)
services_dir = os.path.join(script_dir, "..", "services")
sys.path.append(os.path.abspath(services_dir))

# --- Import your services ---
try:
    # Now you can import from the files in 'services'
    from searchEngine import search_documents, process_and_store_file
    from llmHandler import get_answer_from_llm
except ImportError as e:
    print(f"Error importing services: {e}")
    print(f"Please check that searchEngine.py and llmHandler.py exist in {services_dir}")
    sys.exit(1)

# --- Initialize the FastAPI App ---
app = FastAPI()

# --- CORS Middleware ---
# This is required to allow your React frontend (on a different "origin")
# to make requests to this FastAPI backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- Pydantic Models (for request data validation) ---
class QueryRequest(BaseModel):
    query: str

class IndexRequest(BaseModel):
    file_path: str

# --- API Endpoints ---

@app.get("/")
def read_root():
    """ A simple test endpoint to see if the server is running. """
    return {"status": "FileGPT Backend is running!"}


@app.post("/ask")
def ask_question(request: QueryRequest):
    """
    The main Q&A endpoint.
    1. Receives a query from the frontend.
    2. Searches ChromaDB for relevant context.
    3. Sends the query and context to the LLM.
    4. Returns the final answer.
    """
    print(f"[API] Received query: {request.query}")
    
    # 1. Search for relevant documents (The "Indexer" is used)
    search_results = search_documents(request.query, n_results=5)
    
    if not search_results or not search_results.get('documents'):
        print("[API] No relevant documents found.")
        return {"answer": "I could not find any relevant information in your files."}

    # Extract the text chunks
    context = search_results['documents'][0]
    
    # 2. Get the answer from the LLM (The "Answerer" is used)
    answer = get_answer_from_llm(request.query, context)
    
    print(f"[API] Sending answer: {answer}")
    
    # 3. Return the answer
    return {"answer": answer, "sources": search_results['metadatas'][0]}


@app.post("/index_file")
def index_file(request: IndexRequest):
    """
    An endpoint to manually trigger indexing for a single file.
    """
    print(f"[API] Received request to index: {request.file_path}")
    
    if not os.path.exists(request.file_path):
        return {"status": "error", "message": "File not found."}
        
    try:
        process_and_store_file(request.file_path)
        return {"status": "success", "message": f"File '{request.file_path}' processed."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to process file: {e}"}

# --- How to Run This Server ---
if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server...")
    # Run the server on http://127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)