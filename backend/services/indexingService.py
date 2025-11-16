import chromadb
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import our new file parser
from file_parser import get_file_content

# --- 1. INITIALIZE MODELS AND DB ---

# Load the embedding model (as before)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize the text splitter (as before)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50
)

# Initialize a PERSISTENT ChromaDB client
# This will save the database files in a folder named 'chroma_db'
db_client = chromadb.PersistentClient(path="./chroma_db")

# Create or get a collection to store our embeddings
collection = db_client.get_or_create_collection(name="filegpt_index")

print("ChromaDB persistent client initialized.")


# --- 2. EMBEDDING GENERATION FUNCTION (from previous step) ---

def generate_embeddings(file_content: str):
    """
    Splits content into chunks and generates embeddings.
    """
    chunks = text_splitter.split_text(file_content)
    if not chunks:
        return [], []
    
    try:
        embeddings = embedding_model.encode(chunks)
        return chunks, embeddings.tolist()
    except Exception as e:
        print(f"Error during embedding generation: {e}")
        return [], []


# --- 3. MAIN FUNCTION TO PROCESS AND STORE A FILE ---

def process_and_store_file(file_path: str):
    """
    Main function to read, chunk, embed, and store a file.
    """
    print(f"Processing file: {file_path}")
    
    # 1. Get content from the file
    content = get_file_content(file_path)
    
    if not content:
        print(f"No content extracted from {file_path}. Skipping.")
        return

    # 2. Generate embeddings
    chunks, embeddings = generate_embeddings(content)
    
    if not chunks:
        print(f"No chunks generated for {file_path}. Skipping.")
        return

    # 3. Create IDs and metadata for storage
    # This is how we'll know where the chunk came from
    ids = []
    metadatas = []
    for i in range(len(chunks)):
        # A unique ID for each chunk
        ids.append(f"{file_path}_chunk_{i}")
        # Metadata to store with the vector
        metadatas.append({"source_file": file_path})

    # 4. Add to ChromaDB
    try:
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully indexed {len(chunks)} chunks for {file_path}")
    
    except chromadb.errors.IDAlreadyExistsError:
        print(f"Updating file: {file_path}")
        # If file already exists, we use 'update' instead of 'add'
        collection.update(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
    except Exception as e:
        print(f"Error indexing {file_path}: {e}")


# --- Example Usage ---
if __name__ == "__main__":
    # Create another dummy file
    with open("test2.txt", "w") as f:
        f.write("This is the second test file. It talks about ChromaDB.")
    
    # Process and store the file
    process_and_store_file("test.txt")
    process_and_store_file("test2.txt")
    
    # Test our search
    results = collection.query(
        query_texts=["What is ChromaDB?"],
        n_results=1
    )
    print("\n--- Search Result ---")
    print(results['documents'])