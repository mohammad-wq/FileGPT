"""
Self-Correcting RAG Workflow using LangGraph
Implements: Retrieve → Grade → Decide → Transform → Generate
"""

import os
import sys
from typing import List, Dict, Any, Tuple
from langgraph.graph import StateGraph, END
import ollama
import json

# Add parent directory to path for config import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import get_logger
from services import searchEngine, summary_service, rag_grader, rag_query_transformer

logger = get_logger("rag_workflow")


class RAGState:
    """State object passed through LangGraph nodes."""
    
    def __init__(self, query: str, k: int = 5):
        self.query = query
        self.k = k
        self.documents: List[Dict] = []
        self.graded_documents: List[Dict] = []
        self.should_generate = False
        self.transformed_query: str = None
        self.retrieval_count = 0
        self.generation_result = None
        self.attempts = 0
        self.max_attempts = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dict for LangGraph."""
        return {
            "query": self.query,
            "k": self.k,
            "documents": self.documents,
            "graded_documents": self.graded_documents,
            "should_generate": self.should_generate,
            "transformed_query": self.transformed_query,
            "retrieval_count": self.retrieval_count,
            "generation_result": self.generation_result,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
        }


def retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve documents from hybrid search engine.
    Uses current query (original or transformed).
    """
    query_to_use = state.get("transformed_query") or state["query"]
    
    logger.info(f"Retrieve: Query='{query_to_use}', k={state['k']}")
    
    documents = searchEngine.hybrid_search(query_to_use, k=state["k"])
    
    state["documents"] = documents
    state["retrieval_count"] = len(documents)
    
    logger.debug(f"   Found {len(documents)} documents")
    
    return state


def grade_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grade retrieved documents for relevance.
    Removes semantic drift.
    """
    if not state["documents"]:
        state["graded_documents"] = []
        return state
    
    grader = rag_grader.get_grader()
    original_query = state["query"]  # Always grade against original query
    
    graded_docs, _ = grader.grade_documents(original_query, state["documents"])
    
    state["graded_documents"] = graded_docs
    
    return state


def decide_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decide whether to proceed to generation or transform query.
    Path A: If valid docs exist → Generate
    Path B: If zero valid docs → Transform Query
    """
    if len(state["graded_documents"]) > 0:
        logger.info(f"Decision: Valid documents found → Proceeding to Generation")
        state["should_generate"] = True
    else:
        logger.info(f"Decision: No valid documents → Query needs transformation")
        state["should_generate"] = False
    
    return state


def transform_query_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform query if grading resulted in zero docs.
    Only triggered when should_generate == False.
    """
    if state["should_generate"] or state["attempts"] >= state["max_attempts"]:
        # Don't transform if we already have docs, or if we've exceeded max attempts
        return state
    
    transformer = rag_query_transformer.get_transformer()
    new_query = transformer.transform_query(state["query"])
    
    if new_query:
        state["transformed_query"] = new_query
        state["attempts"] += 1
        logger.info(f"Attempt {state['attempts']}/{state['max_attempts']}: Transformed query")
        # Trigger retrieval again with new query by returning a loop signal
        state["_retry_retrieve"] = True
    else:
        logger.warning(f"Could not transform query. Proceeding with original or empty results.")
        state["should_generate"] = True  # Generate with what we have
    
    return state


def generate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate final answer using graded documents.
    Input is strictly filtered documents only.
    """
    model = summary_service.get_available_model()
    docs_to_use = state["graded_documents"] if state["graded_documents"] else state["documents"]
    
    if not docs_to_use:
        result = {
            "answer": "I couldn't find any relevant files to answer your question. Try rephrasing your query or adding more files to index.",
            "sources": [],
            "grading_stats": {
                "retrieved": state["retrieval_count"],
                "graded": 0,
                "attempts": state["attempts"]
            }
        }
        state["generation_result"] = result
        return state
    
    # Build context from filtered documents
    context_parts = []
    sources = []
    
    for i, doc in enumerate(docs_to_use, 1):
        context_parts.append(f"--- Source {i}: {doc.get('source', 'unknown')} ---")
        if doc.get('summary'):
            context_parts.append(f"Summary: {doc['summary']}")
        context_parts.append(f"Content:\n{doc.get('content', '')}")
        context_parts.append("")
        
        sources.append({
            "source": doc.get('source', ''),
            "path": doc.get('source', ''),
            "summary": doc.get('summary', ''),
            "score": doc.get('score', 0),
            "content": doc.get('content', '')
        })
    
    context = "\n".join(context_parts)
    
    prompt = f"""You are a helpful AI assistant. Answer the following question STRICTLY based on the provided context.
Do not use external knowledge. If the context doesn't contain enough information, say so.

Question: {state['query']}

Context from files:
{context}

Answer (be concise and cite sources):"""
    
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3, "num_predict": 500}
        )
        
        answer = response['message']['content'].strip()
        
        result = {
            "answer": answer,
            "sources": sources,
            "grading_stats": {
                "retrieved": state["retrieval_count"],
                "graded": len(state["graded_documents"]),
                "attempts": state["attempts"]
            }
        }
        
        state["generation_result"] = result
        
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        state["generation_result"] = {
            "answer": f"Error generating answer: {str(e)}",
            "sources": sources,
            "grading_stats": {
                "retrieved": state["retrieval_count"],
                "graded": len(state["graded_documents"]),
                "attempts": state["attempts"]
            }
        }
    
    return state


def build_rag_workflow():
    """
    Build the LangGraph workflow:
    Retrieve → Grade → Decide → [Transform → Retrieve] or [Generate]
    """
    workflow = StateGraph(dict)
    
    # Add nodes
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade", grade_node)
    workflow.add_node("decide", decide_node)
    workflow.add_node("transform", transform_query_node)
    workflow.add_node("generate", generate_node)
    
    # Define edges
    workflow.add_edge("retrieve", "grade")
    workflow.add_edge("grade", "decide")
    
    # Conditional: decide → generate or transform
    def should_generate(state):
        return "generate" if state["should_generate"] else "transform"
    
    workflow.add_conditional_edges("decide", should_generate)
    
    # After transform, check if we should retry retrieval
    def after_transform(state):
        return "retrieve" if state.get("_retry_retrieve") and state["attempts"] < state["max_attempts"] else "generate"
    
    workflow.add_conditional_edges("transform", after_transform)
    
    # Generate leads to end
    workflow.add_edge("generate", END)
    
    # Set entry point
    workflow.set_entry_point("retrieve")
    
    return workflow.compile()


async def run_rag_workflow(query: str, k: int = 5) -> Dict[str, Any]:
    """
    Run the self-correcting RAG workflow.
    
    Args:
        query: User's question
        k: Number of results to retrieve
        
    Returns:
        Dictionary with answer, sources, and grading stats
    """
    # Initialize state
    state = RAGState(query=query, k=k).to_dict()
    
    # Build and run workflow
    app = build_rag_workflow()
    
    logger.info(f"Starting Self-Correcting RAG Workflow for query: '{query}'")
    
    final_state = await app.ainvoke(state)
    
    result = final_state.get("generation_result", {})
    
    logger.info(
        f"Workflow Complete | Retrieved: {final_state.get('retrieval_count', 0)} | "
        f"Graded: {len(final_state.get('graded_documents', []))} | "
        f"Attempts: {final_state.get('attempts', 0)}"
    )
    
    return result


def run_rag_workflow_sync(query: str, k: int = 5) -> Dict[str, Any]:
    """
    Synchronous wrapper for the RAG workflow (for REST endpoints).
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(run_rag_workflow(query, k))
