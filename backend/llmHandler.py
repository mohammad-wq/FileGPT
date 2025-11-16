# backend/services/llmHandler.py

import ollama
import json

# --- Configuration ---
# Make sure you have run: ollama run llama3:8b
LLM_MODEL = "llama3:8b"

def get_answer_from_llm(query: str, context: list[str]):
    """
    Sends the user's query and the retrieved context to the local LLM
    to generate a natural language answer.
    
    Args:
        query: The user's original question.
        context: A list of relevant text chunks found in the database.
    
    Returns:
        A string containing the LLM's answer.
    """
    
    # Combine the context chunks into a single string
    context_str = "\n\n".join(context)
    
    # This is the prompt template. It instructs the LLM how to behave.
    prompt = f"""
    You are a helpful assistant for the FileGPT project.
    Answer the user's question based ONLY on the provided context.
    If the answer is not in the context, say "I could not find an answer in the provided files."
    Do not make up information.

    --- CONTEXT ---
    {context_str}
    --- END OF CONTEXT ---

    USER'S QUESTION:
    {query}
    """
    
    print(f"\n[LLM Handler] Sending prompt to {LLM_MODEL}...")
    
    try:
        # Send the complete prompt to Ollama
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {'role': 'user', 'content': prompt}
            ]
        )
        
        return response['message']['content']
        
    except Exception as e:
        print(f"[LLM Handler] Error communicating with Ollama: {e}")
        # This could happen if Ollama isn't running
        return "Error: Could not connect to the local AI model. Please ensure Ollama is running."

# --- Example Usage (for testing this file directly) ---
if __name__ == "__main__":
    
    # Make sure Ollama is running and you have pulled the model:
    # ollama run llama3:8b
    
    print("--- Testing LLM Handler ---")
    test_query = "What is FileGPT?"
    test_context = [
        "The FileGPT project aims to build a local-first AI file manager.",
        "It uses ChromaDB for vector storage and React for the frontend."
    ]
    
    answer = get_answer_from_llm(test_query, test_context)
    print(f"\nQuery: {test_query}")
    print(f"Answer: {answer}")