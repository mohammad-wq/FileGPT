"""
RAG Document Grader Service
Filters retrieved documents to remove semantic drift and irrelevant results.
Uses batch LLM calls for efficiency.
"""

import os
import sys
from typing import List, Dict, Tuple
import ollama

# Add parent directory to path for config import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import get_logger
from services import summary_service

logger = get_logger("rag_grader")


class DocumentGrader:
    """
    Grades retrieved documents against user query using LLM.
    Removes irrelevant documents that cause semantic drift.
    """
    
    def __init__(self):
        self.model = summary_service.get_available_model()
        self.batch_size = 5  # Grade up to 5 docs per LLM call
    
    def grade_documents(self, query: str, documents: List[Dict]) -> Tuple[List[Dict], int]:
        """
        Grade documents and return only those relevant to the query.
        Processes in batches for efficiency.
        
        Args:
            query: User's original question
            documents: List of retrieved document dicts with 'content', 'source', etc.
            
        Returns:
            Tuple of (filtered_docs, original_count)
        """
        if not documents:
            return [], 0
        
        original_count = len(documents)
        filtered_docs = []
        
        # Process documents in batches
        for batch_start in range(0, len(documents), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(documents))
            batch = documents[batch_start:batch_end]
            batch_num = (batch_start // self.batch_size) + 1
            
            # Build batch grading prompt
            doc_text = "\n\n---\n\n".join([
                f"[DOC {i+1}]\nFile: {doc.get('source', 'unknown')}\nContent: {doc.get('content', '')[:500]}"
                for i, doc in enumerate(batch)
            ])
            
            # Allow multiple tolerant output formats to accommodate smaller or flaky models.
            # Preferred: JSON array. Alternatives the parser will accept:
            # - One decision per line like: "DOC 1: RELEVANT"
            # - Simple newline-separated tokens: "RELEVANT\nNOT_RELEVANT\n..."
            # - Comma-separated tokens
            grading_prompt = f"""You are a strict document relevance evaluator. Grade this batch of documents.

User Question: {query}

Documents to Grade (Batch {batch_num}/{(original_count + self.batch_size - 1) // self.batch_size}):
{doc_text}

For each document, decide: RELEVANT or NOT_RELEVANT.
RELEVANT = directly answers or provides context for the question
NOT_RELEVANT = tangentially related or about different topic

Preferred output: a JSON array, one decision per document, e.g. ["RELEVANT", "NOT_RELEVANT", ...]
If you cannot output JSON, you may instead reply in one of these formats (we will parse them):
- One decision per line (e.g. "DOC 1: RELEVANT")
- Simple newline-separated tokens ("RELEVANT\nNOT_RELEVANT\n...")
- Comma-separated tokens ("RELEVANT, NOT_RELEVANT, ...")

Respond only with the minimal decision list in one of those formats. Do not add extra explanation.
"""
            
            try:
                response = ollama.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": grading_prompt}],
                    options={"temperature": 0.0, "num_predict": 200}
                )

                response_text = response['message']['content'].strip()

                # Try several parsing strategies to be tolerant of different output formats
                decisions = None
                import json, re

                # 1) Try JSON first (preferred)
                try:
                    parsed = json.loads(response_text)
                    if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                        decisions = [x.strip().upper() for x in parsed]
                except Exception:
                    decisions = None

                # 2) Look for 'DOC <n>: DECISION' patterns
                if decisions is None:
                    doc_pattern = re.findall(r"DOC\s*(\d+)\s*[:\-]\s*(RELEVANT|NOT_RELEVANT)", response_text, flags=re.IGNORECASE)
                    if doc_pattern:
                        # Build decisions array sized to batch (default NOT_RELEVANT)
                        temp = ["NOT_RELEVANT"] * len(batch)
                        for idx_str, decision in doc_pattern:
                            try:
                                idx = int(idx_str) - 1
                                if 0 <= idx < len(batch):
                                    temp[idx] = decision.upper()
                            except Exception:
                                continue
                        decisions = temp

                # 3) Extract all RELEVANT/NOT_RELEVANT tokens in order of appearance
                if decisions is None:
                    tokens = re.findall(r"\b(RELEVANT|NOT_RELEVANT)\b", response_text, flags=re.IGNORECASE)
                    if tokens and len(tokens) == len(batch):
                        decisions = [t.upper() for t in tokens]

                # 4) Comma or newline separated fallback
                if decisions is None:
                    # Normalize separators to newline then split
                    cleaned = re.sub(r"[,;]+", "\n", response_text)
                    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
                    possible = [ln.upper() for ln in lines if ln.upper() in ("RELEVANT", "NOT_RELEVANT")]
                    if len(possible) == len(batch):
                        decisions = possible

                # If still None or length mismatch, fallback to keeping the batch (safe default)
                if decisions is None or len(decisions) != len(batch):
                    logger.warning(f"Grading parse failed or incomplete on batch {batch_num}. Keeping batch intact. Response: {response_text[:300]}")
                    filtered_docs.extend(batch)
                    continue

                # Filter batch based on parsed decisions
                for i, doc in enumerate(batch):
                    if i < len(decisions) and decisions[i].upper() == "RELEVANT":
                        filtered_docs.append(doc)
                        
            except Exception as e:
                logger.error(f"Batch {batch_num} grading failed: {e}")
                filtered_docs.extend(batch)
        
        removed_count = original_count - len(filtered_docs)
        logger.info(f"Document Grading: {original_count} → {len(filtered_docs)} docs (removed {removed_count} semantic drift)")
        
        return filtered_docs, original_count
    
    def should_transform_query(self, filtered_docs: List[Dict]) -> bool:
        """
        Decide if query needs transformation based on grading results.
        
        Returns True if no documents survived grading (zero relevant docs).
        """
        return len(filtered_docs) == 0


def get_grader() -> DocumentGrader:
    """Get or create global grader instance."""
    global _grader
    if '_grader' not in globals():
        _grader = DocumentGrader()
    return _grader
