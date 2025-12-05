"""
Summary Service for FileGPT
Local LLM-powered file summarization using Ollama.
"""

from typing import Optional
import ollama


# Model configuration
PRIMARY_MODEL = "qwen2.5:0.5b"  # Only model available, needs ~500MB RAM
FALLBACK_MODEL = "qwen2.5:0.5b"  # Same as primary since only one model is available
MAX_CONTEXT_LENGTH = 8000  # Characters to send to LLM


def get_available_model() -> str:
    """
    Get the first available model from the priority list.
    
    Returns:
        Model name to use
    """
    try:
        models = ollama.list()
        model_names = [m.get('name', '') for m in models.get('models', [])]
        
        # Try primary model first
        if PRIMARY_MODEL in model_names:
            return PRIMARY_MODEL
        
        # Fall back to same model (only one model available)
        if FALLBACK_MODEL in model_names:
            print(f"Note: Using fallback model {FALLBACK_MODEL}")
            return FALLBACK_MODEL
        
        # Default to primary even if not found (will error gracefully later)
        return PRIMARY_MODEL
    except Exception:
        return PRIMARY_MODEL


def generate_summary(content: str, file_path: str) -> str:
    """
    Generate a concise summary of file content using local LLM.
    
    Args:
        content: File content to summarize
        file_path: Path to the file (for context)
        
    Returns:
        Generated summary (2-3 sentences), or error message if generation fails
    """
    # Truncate content to fit context window
    truncated_content = content[:MAX_CONTEXT_LENGTH]
    if len(content) > MAX_CONTEXT_LENGTH:
        truncated_content += "\n... (truncated)"
    
    # Build prompt
    prompt = f"""You are a technical documentation assistant. Analyze the following file and provide a concise 2-3 sentence summary.

File Path: {file_path}

Content:
{truncated_content}

Provide a summary that describes:
1. What this file does or contains
2. Key functionality or important information

Summary:"""
    
    try:
        # Get available model
        model_name = get_available_model()
        
        # Call Ollama for local inference
        response = ollama.chat(
            model=model_name,
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            options={
                'temperature': 0.3,  # Lower temperature for more focused summaries
                'num_predict': 150,  # Limit output tokens
            }
        )
        
        summary = response['message']['content'].strip()
        
        # Ensure we got a valid summary
        if not summary:
            return "Summary generation returned empty response."
        
        return summary
        
    except Exception as e:
        error_msg = str(e)
        print(f"Warning: Summary generation failed for {file_path}: {error_msg[:100]}")
        # Return a simple fallback summary based on file type
        file_ext = file_path.split('.')[-1].lower()
        return f"[{file_ext.upper()} file - Summary unavailable due to insufficient memory]"


def test_ollama_connection() -> bool:
    """
    Test if Ollama is running and the model is available.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        model_name = get_available_model()
        response = ollama.chat(
            model=model_name,
            messages=[
                {
                    'role': 'user',
                    'content': 'Hello'
                }
            ]
        )
        return True
    except Exception as e:
        print(f"Ollama connection test failed: {e}")
        return False


def get_model_info() -> Optional[dict]:
    """
    Get information about the current LLM model.
    
    Returns:
        Model information dictionary, or None if unavailable
    """
    try:
        model_name = get_available_model()
        models = ollama.list()
        for model in models.get('models', []):
            if model_name in model.get('name', ''):
                return model
        return None
    except Exception as e:
        print(f"Error getting model info: {e}")
        return None
