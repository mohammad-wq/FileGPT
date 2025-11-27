"""
Startup script for FileGPT Backend
Convenience script to start the FastAPI server.
"""

import sys
import os

# Check Python version
if sys.version_info < (3, 10):
    print("Error: Python 3.10 or higher is required")
    sys.exit(1)

# Check if dependencies are installed
try:
    import fastapi
    import uvicorn
    import chromadb
    import ollama
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Error: Missing dependency - {e}")
    print("\nPlease install dependencies:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

# Check if Ollama is available
print("Checking Ollama connection...")
try:
    models = ollama.list()
    print("[OK] Ollama is running")
    
    # Check if llama3.2:3b is installed (used for summarization)
    model_list = models.get('models', [])
    has_llama3_2 = any('llama3.2:3b' in model.get('name', '') for model in model_list)
    has_llama3_8b = any('llama3:8b' in model.get('name', '') for model in model_list)
    
    if not has_llama3_2 and not has_llama3_8b:
        print("\n[WARNING] No llama3 model found")
        print("   Please install one of:")
        print("     ollama pull llama3.2:3b  (Recommended - smaller, 2GB RAM)")
        print("     ollama pull llama3:8b    (Larger, better quality)")
        print("   The server will start but summarization will fail.\n")
    elif has_llama3_2:
        print("✓ Found llama3.2:3b - summarization will use this model")
    elif has_llama3_8b:
        print("✓ Found llama3:8b - will use llama3.2:3b if available, or llama3:8b as fallback")
except Exception as e:
    print(f"\n[WARNING] Could not connect to Ollama - {e}")
    print("   Please ensure Ollama is running: ollama serve")
    print("   The server will start but summarization will fail.\n")

print("\n" + "=" * 60)
print("Starting FileGPT Backend Server")
print("=" * 60)
print("\nServer will be available at:")
print("  - http://127.0.0.1:8000")
print("  - API Docs: http://127.0.0.1:8000/docs")
print("\nPress Ctrl+C to stop the server")
print("=" * 60 + "\n")

# Change to the correct directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Start the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
