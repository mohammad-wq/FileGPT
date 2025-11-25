"""
Summary Service for FileGPT
Local LLM-powered file summarization using Ollama.
"""

from typing import Optional
import ollama


# Model configuration
MODEL_NAME = "llama3:8b"
MAX_CONTEXT_LENGTH = 8000  # Characters to send to LLM


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
        # Call Ollama for local inference
        response = ollama.chat(
            model=MODEL_NAME,
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
        print(f"Error generating summary for {file_path}: {e}")
        return f"Summary unavailable (Error: {str(e)[:100]})"


def test_ollama_connection() -> bool:
    """
    Test if Ollama is running and the model is available.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        response = ollama.chat(
            model=MODEL_NAME,
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
        models = ollama.list()
        for model in models.get('models', []):
            if MODEL_NAME in model.get('name', ''):
                return model
        return None
    except Exception as e:
        print(f"Error getting model info: {e}")
        return None
