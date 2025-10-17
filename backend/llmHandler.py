# llm_handler.py

import ollama

def get_answer_from_llm(context, query):
    """
    Sends the context and query to the local LLM to generate an answer.
    """
    # This is a simple prompt template. You can refine it.
    prompt = f"""
    Using only the following context, answer the user's question.
    If the answer is not available in the context, say "I don't have enough information to answer that."

    Context:
    {context}

    Question:
    {query}
    """
    
    print("Sending prompt to LLM...")
    
    # Stream the response from the LLM
    response = ollama.chat(
        model='llama3:8b',
        messages=[{'role': 'user', 'content': prompt}],
        stream=True
    )
    
    full_answer = ""
    print("\n--- Generated Answer ---")
    for chunk in response:
        # Print each chunk as it arrives
        part = chunk['message']['content']
        print(part, end='', flush=True)
        full_answer += part
    
    print("\n------------------------\n")
    return full_answer

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # This is the context we "found" in the previous step
    sample_context = "Key features include semantic search, summarization, and file Q&A.\nThe project, named FileGPT, aims to solve file management issues."
    user_query = "What features does FileGPT have?"

    get_answer_from_llm(sample_context, user_query)