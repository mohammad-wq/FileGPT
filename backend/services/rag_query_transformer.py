"""
Query Transformer Service
Rewrites vague or poorly-matched queries to improve search results.
Used when initial retrieval returns zero relevant documents.
"""

from typing import Optional
import ollama
from services import summary_service


class QueryTransformer:
    """
    Transforms user queries to be more optimized for search.
    Triggered when grading results in zero relevant documents.
    """
    
    def __init__(self):
        self.model = summary_service.get_available_model()
    
    def transform_query(self, original_query: str) -> Optional[str]:
        """
        Rewrite query to be more search-friendly.
        
        Args:
            original_query: User's original question
            
        Returns:
            Transformed query, or None if transformation fails
        """
        
        transform_prompt = f"""You are a search query optimization expert. The user's original query returned zero relevant results, which means the search terms are too vague or poorly matched.

Original Query: {original_query}

Your task: Rewrite this query to be MORE SPECIFIC and SEARCH-FRIENDLY for a code/document repository.
- Add specific keywords (e.g., programming language, algorithm name, file type)
- Remove vague words
- Be concise (max 15 words)

Examples:
- "find the sorting thing" → "merge sort algorithm C++ implementation"
- "show me network files" → "TCP IP networking code example"
- "that function we talked about" → "binary search tree insertion function"

Return ONLY the rewritten query, nothing else."""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": transform_prompt}],
                options={"temperature": 0.3, "num_predict": 50}
            )
            
            transformed = response['message']['content'].strip()
            
            if transformed and transformed != original_query:
                print(f"🔄 Query Transformation: '{original_query}' → '{transformed}'")
                return transformed
            
            return None
            
        except Exception as e:
            print(f"⚠️  Query transformation failed: {e}")
            return None


def get_transformer() -> QueryTransformer:
    """Get or create global transformer instance."""
    global _transformer
    if '_transformer' not in globals():
        _transformer = QueryTransformer()
    return _transformer
