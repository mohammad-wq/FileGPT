"""
Startup script for FileGPT Backend
Initializes database, search engine, and background worker.
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
    import fitz  # PyMuPDF
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Error: Missing dependency - {e}")
    print("\nPlease install dependencies:")
    print("  E:\\Dev\\Envs\\FileGPT_env\\Scripts\\activate.ps1")
    print("  pip install -r requirements.txt")
    sys.exit(1)

# Check if Ollama is available
print("Checking Ollama connection...")
try:
    models = ollama.list()
    print("[OK] Ollama is running")
    
    # Check if qwen2.5:0.5b is installed
    model_list = models.get('models', [])
    has_qwen = any('qwen2.5:0.5b' in model.get('name', '') for model in model_list)
    
    if has_qwen:
        print("✓ Found qwen2.5:0.5b - all LLM features ready (500MB RAM)")
    else:
        print("\n[WARNING] qwen2.5:0.5b model not found")
        print("   Install with: ollama pull qwen2.5:0.5b")
        print("   The server will start but AI features will fail.\n")
except Exception as e:
    print(f"\n[WARNING] Could not connect to Ollama - {e}")
    print("   Start Ollama: ollama serve")
    print("   The server will start but AI features will fail.\n")


print("\n" + "=" * 60)
print("FileGPT Backend - High-Performance Architecture")
print("=" * 60)
print("\nFeatures:")
print("  ✓ SHA256 deduplication")
print("  ✓ PyMuPDF fast parsing")
print("  ✓ Background async processing")
print ("  ✓ Tiered search (cache → BM25 → vector → RRF)")
print("\nServer will be available at:")
print("  - http://127.0.0.1:8000")
print("  - API Docs: http://127.0.0.1:8000/docs")
print("\nPress Ctrl+C to stop")
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
