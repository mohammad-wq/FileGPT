# search_engine.py

import chromadb
from sentence_transformers import SentenceTransformer

# 1. Initialize ChromaDB client. It will store data in a local folder.
client = chromadb.Client()
collection = client.get_or_create_collection(name="filegpt_collection")

# 2. Load the embedding model. This will download it on the first run.
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded.")

# --- SIMULATE FILE CONTENT ---
# In your actual app, this text will come from parsing PDFs, DOCX, etc.
file_chunks = [
    "The project, named FileGPT, aims to solve file management issues.",
    "It uses Natural Language Processing (NLP) and local language models.",
    "Key features include semantic search, summarization, and file Q&A.",
    "The system will run locally on the user's PC to ensure privacy.",
    "Optional cloud integration with Google Drive and Dropbox is planned."
]
# --- END SIMULATION ---

# 3. Generate embeddings and store them in ChromaDB
# This step is the "indexing" process. You'll run this for every file.
print("Generating embeddings and indexing documents...")
collection.add(
    embeddings=model.encode(file_chunks).tolist(), # Generate and convert to list
    documents=file_chunks,
    ids=[f"chunk_{i}" for i in range(len(file_chunks))] # Each chunk needs a unique ID
)
print("Indexing complete.")

# 4. Define a function to search for relevant context
def find_relevant_context(query):
    """
    Takes a user query, embeds it, and retrieves the most relevant text chunks.
    """
    print(f"\nSearching for context related to: '{query}'")
    # Generate the embedding for the user's query
    query_embedding = model.encode([query]).tolist()

    # Query the collection to find the 2 most relevant chunks
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=2
    )
    
    # The actual text is in the 'documents' field
    context = "\n".join(results['documents'][0])
    return context

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    user_query = "What features does FileGPT have?"
    relevant_context = find_relevant_context(user_query)
    
    print("\n--- Found Context ---")
    print(relevant_context)
    print("---------------------\n")