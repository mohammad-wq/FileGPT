# In your backend/services/indexing_service.py

from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Initialize your model and text splitter once
#    (You can do this in your main app file and pass them to the function)
try:
    # Load the embedding model
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Initialize the text splitter
    # chunk_size = 512: Tries to create chunks of 512 characters.
    # chunk_overlap = 50: Each chunk will have 50 overlapping characters
    #                     with the previous one. This helps keep context
    #                     between chunks.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50
    )

except Exception as e:
    print(f"Error initializing models: {e}")
    # Handle the error appropriately (e.g., log and exit)
    embedding_model = None
    text_splitter = None


def generate_embeddings_for_file(file_content: str):
    """
    Takes raw file content, splits it into manageable chunks,
    and generates an embedding for each chunk.
    
    Returns:
        A tuple: (list_of_chunks, list_of_embeddings)
        - list_of_chunks: The actual text content for each chunk.
        - list_of_embeddings: The corresponding vector embedding for each chunk.
    """
    if not embedding_model or not text_splitter:
        print("Error: Models are not initialized.")
        return [], []

    print(f"Original content length: {len(file_content)} characters")

    # 2. Split the document into chunks
    # This is the "split the data" step you asked for.
    chunks = text_splitter.split_text(file_content)
    
    print(f"Content split into {len(chunks)} chunks.")
    
    if not chunks:
        print("Warning: No text chunks were created. Content might be empty.")
        return [], []

    # 3. Generate embeddings for all chunks in one go
    # The model.encode() function handles batching efficiently.
    try:
        print("Generating embeddings for all chunks...")
        embeddings = embedding_model.encode(chunks, show_progress_bar=True)
        print("Embeddings generated successfully.")
        
        # We return both lists. You MUST store these together.
        # The vector DB needs the 'chunk' as the metadata for its 'embedding'.
        return chunks, embeddings.tolist() # .tolist() converts numpy array to list

    except Exception as e:
        print(f"Error during embedding generation: {e}")
        return [], []


# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # A long piece of sample text (simulating a file)
    sample_file_content = """
    FileGPT is a local-first desktop application that uses Natural Language Processing (NLP),
    local language models, and semantic search to help users manage their files.
    The system will allow users to search file content using natural language, ask questions
    about documents, get summaries of long files, and reorganize files automatically.
    It will support common file formats such as PDF, Word, text, spreadsheets, and images.
    
    The project is motivated by the need for a privacy-first, Al-powered file and
    knowledge management system. By enabling semantic search and intelligent reorganization,
    the system will transform how users interact with their data.
    The core features include:
    1. Semantic File Search - foundation of the assistant.
    2. File Content Q&A - lets users query file contents.
    3. Summarization - essential for handling long documents efficiently.
    """
    
    chunks, embeddings = generate_embeddings_for_file(sample_file_content)
    
    if chunks:
        print("\n--- Example of the first chunk ---")
        print(f"Text: {chunks[0]}")
        print(f"Embedding (first 5 values): {embeddings[0][:5]}")
        print(f"Total Embeddings: {len(embeddings)}")