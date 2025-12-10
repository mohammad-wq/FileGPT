"""
Summary Service for FileGPT
Local LLM-powered file summarization using Ollama.
"""

import os
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
        Generated summary (one sentence, <50 words), or error message if generation fails
    """
    print(f"📝 Generating summary for {os.path.basename(file_path)}...")
    
    # Truncate content to fit context window
    truncated_content = content[:MAX_CONTEXT_LENGTH]
    if len(content) > MAX_CONTEXT_LENGTH:
        truncated_content += "\n... (truncated)"
    
    # Detect file type and context for better summary
    file_name = os.path.basename(file_path).lower()
    file_ext = file_name.split('.')[-1] if '.' in file_name else ''
    role_prefix = ""
    if "resume" in file_name:
        # Try to extract name from filename
        name = ""
        for part in file_name.replace('.pdf', '').replace('.docx', '').split('_'):
            if part and part != "resume":
                name = part.capitalize()
                break
        role_prefix = f"Resume for {name if name else 'user'}: "
    elif file_ext in ["pdf", "docx", "txt"]:
        role_prefix = f"{file_ext.upper()} document: "
    elif file_ext in ["html", "htm"]:
        role_prefix = "HTML file: "
    elif file_ext in ["xlsx", "xls"]:
        role_prefix = "Excel spreadsheet: "
    elif file_ext in ["pptx", "ppt"]:
        role_prefix = "PowerPoint presentation: "
    else:
        role_prefix = f"{file_ext.upper()} file: " if file_ext else "File: "

    # Build a more detailed, generic system prompt for the LLM
    prompt = f"""
You are an expert file summarizer. Your job is to generate a clear, concise summary for any file type.

Instructions:
- Start by stating what type of file it is (e.g., Resume, PDF document, Python script, Spreadsheet, etc.).
- If possible, mention the file's purpose or role (e.g., Resume for Mohammad, Invoice for client, Project report).
- Then, briefly summarize the main contents or topics covered in the file.
- Use one sentence, maximum 20 words. Be factual and avoid speculation.
- Do not include file paths, metadata, or unnecessary details.

File name: {file_name}
File content:
{truncated_content}

Summary (one sentence, 20 words max):
"""
    
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
                'temperature': 0.1,  # Lower temperature for more focused summaries
                'num_predict': 30,  # Limit output tokens
            }
        )
        
        summary = response['message']['content'].strip()
        # Remove "Summary:" prefix if LLM adds it
        if summary.lower().startswith('summary:'):
            summary = summary[8:].strip()
        # Ensure we got a valid summary
        if not summary:
            print(f"⚠️ Summary generation returned empty for {file_path}")
            return role_prefix + "Summary generation returned empty response."
        # Truncate if still too long (safety check)
        words = summary.split()
        if len(words) > 50:
            summary = ' '.join(words[:50]) + '...'
        print(f"✓ Generated summary for {os.path.basename(file_path)}: {len(words)} words")
        # Prepend role prefix for context-aware summary
        return role_prefix + summary
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Summary generation failed for {file_path}: {error_msg[:100]}")
        # Return a simple fallback summary based on file type
        file_ext = file_path.split('.')[-1].lower()
        return f"[{file_ext.upper()} file - Summary unavailable]"


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
