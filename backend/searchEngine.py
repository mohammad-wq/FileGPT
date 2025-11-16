# backend/services/searchEngine.py

import chromadb
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

# Import your file parser
# This assumes doclingDocumentParser.py is in the same folder
try:
    from doclingDocumentParser import get_file_content
except ImportError:
    print("Error: Could not import get_file_content from doclingDocumentParser.py")
    # Define a dummy function to allow the rest of the script to load
    def get_file_content(file_path: str):
        print(f"DUMMY PARSER: reading {file_path}")
        if file_path.endswith(".txt"):
            with open(file_path, 'r') as f:
                return f.read()
        return None

# --- 1. INITIALIZE MODELS AND DB (runs once when service starts) ---

print("Initializing search engine components...")

# Load the embedding model (this will download it on first run)
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print(f"Error loading SentenceTransformer model: {e}")
    embedding_model = None

# Initialize the text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,  # Max characters per chunk (adjust as needed)
    chunk_overlap=50 # Characters to overlap between chunks
)

# Initialize the persistent ChromaDB client
# This will store the database files in a folder named 'chroma_db'
# inside your 'backend' directory.
db_path = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
db_client = chromadb.PersistentClient(path=db_path)

# Get or create a collection (like a table in a SQL DB)
collection = db_client.get_or_create_collection(name="filegpt_index")

print("Search engine initialized successfully.")
print(f"Database path: {db_path}")

# --- 2. CORE FUNCTION TO PROCESS A FILE ---

def process_and_store_file(file_path: str):
    """
    Main function to read a file, chunk it, generate embeddings,
    and store (or update) them in ChromaDB.
    """
    if not embedding_model:
        print("Embedding model is not loaded. Cannot process file.")
        return

    print(f"[Indexer] Processing file: {file_path}")
    
    # 1. Read content from the file using your parser
    content = get_file_content(file_path)
    
    if not content:
        print(f"[Indexer] No content extracted from {file_path}. Skipping.")
        return

    # 2. Split the content into chunks
    chunks = text_splitter.split_text(content)
    
    if not chunks:
        print(f"[Indexer] No chunks generated for {file_path}. Skipping.")
        return

    # 3. Generate embeddings for all chunks
    try:
        embeddings = embedding_model.encode(chunks)
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return

    # 4. Create IDs and metadata
    # The ID must be unique for each chunk
    ids = [f"{file_path}_chunk_{i}" for i in range(len(chunks))]
    # The metadata helps us know where the chunk came from
    metadatas = [{"source_file": file_path} for _ in range(len(chunks))]

    # 5. Store (or update) in ChromaDB
    try:
        # Use upsert: adds if new, updates if ID already exists
        collection.upsert(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=chunks,
            metadatas=metadatas
        )
        print(f"[Indexer] Successfully indexed {len(chunks)} chunks for {file_path}")
    
    except Exception as e:
        print(f"[Indexer] Error indexing {file_path}: {e}")

# --- 3. FUNCTION TO SEARCH ---

def search_documents(query_text: str, n_results: int = 3):
    """
    Searches the collection for relevant document chunks.
    
    Returns:
        The results from ChromaDB query, or None if an error occurs.
    """
    if not embedding_model:
        print("Embedding model is not loaded. Cannot search.")
        return None

    try:
        # 1. Create an embedding for the user's query
        query_embedding = embedding_model.encode([query_text]).tolist()
        
        # 2. Query the collection
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        return results
    except Exception as e:
        print(f"Error during search: {e}")
        return None


# --- 4. EXAMPLE USAGE (for testing this file directly) ---
if __name__ == "__main__":
    print("\n--- Running Search Engine Test ---")
    
    # Create a dummy file in the 'services' folder for testing
    test_file_name = "test_doc_for_search.txt"
    with open(test_file_name, "w") as f:
        f.write("The FileGPT project aims to build a local-first AI file manager. ")
        f.write("It uses ChromaDB for vector storage and Sentence Transformers for embeddings. ")
        f.write("The frontend is built with React and Tauri.")
    
    # Test 1: Process and store the file
    process_and_store_file(test_file_name)
    
    # Test 2: Search for content
    print("\n--- Test Search ---")
    query = "What is FileGPT?"
    search_results = search_documents(query)
    
    if search_results:
        print(f"Query: {query}")
        print(f"Results: {search_results['documents']}")
        
    # Clean up the test file
    os.remove(test_file_name)