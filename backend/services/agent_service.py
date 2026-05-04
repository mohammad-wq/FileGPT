"""
Agentic Service for FileGPT using LangGraph ReAct pattern.

Implements a true agentic loop where the LLM can autonomously:
1. Decide which tool to call
2. Execute the tool
3. Observe the result
4. Decide next action or provide final answer

Falls back to the simple router for models that don't support tool calling.
"""

from typing import Dict, Any, List, Optional, Annotated, TypedDict, Sequence
from langchain_ollama import ChatOllama
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    ToolMessage,
    BaseMessage,
)
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import json
import operator

from config import OllamaConfig, get_logger

logger = get_logger("agent_service")

# Import tools
from services import tools as tool_module


# ============================================================================
# AGENT STATE
# ============================================================================

class AgentState(TypedDict):
    """State passed through the LangGraph agent loop."""
    messages: Annotated[Sequence[BaseMessage], operator.add]


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """You are FileGPT, an AI-powered file management assistant running locally on the user's machine.

You have access to the following tools:

1. **search_files(query, k)** - Search for files using semantic + keyword search.
   Use when the user wants to find files by content, name, or topic.

2. **read_file(file_path)** - Read the complete content of a specific file.
   Use when the user asks to view or analyze a file's content. Requires an absolute path.

3. **list_directory(path)** - List all files and folders in a directory.
   Use when the user wants to see what's in a folder.

4. **move_file(source, destination)** - Move or rename files/directories.
   Use when the user wants to relocate or rename items. Use with caution.

**Guidelines:**
- For file-related queries, ALWAYS use tools first before answering.
- If you need to find a file first and then read it, do it in two steps: search first, then read.
- When search returns results, reference the actual file paths from the results.
- For general conversation (greetings, explanations, opinions), respond directly without tools.
- Always use absolute paths when calling tools.
- Be concise in your final answers and cite file sources.
"""


# ============================================================================
# LLM INITIALIZATION
# ============================================================================

def get_agent_llm():
    """Get LLM configured for tool calling."""
    return ChatOllama(
        model=OllamaConfig.MODEL,
        temperature=0.0,
        base_url=OllamaConfig.HOST,
    )


def get_tools():
    """Get the list of LangChain tools for the agent."""
    return [
        tool_module.search_files,
        tool_module.read_file,
        tool_module.list_directory,
        tool_module.move_file,
    ]


# ============================================================================
# AGENT NODE (LLM decides next action)
# ============================================================================

def agent_node(state: AgentState) -> dict:
    """
    The agent node: calls the LLM with the current messages.
    The LLM either produces a tool call or a final text response.
    """
    messages = state["messages"]
    llm = get_agent_llm()
    available_tools = get_tools()

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(available_tools)

    # Invoke LLM
    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


# ============================================================================
# TOOL EXECUTION NODE
# ============================================================================

def tool_node(state: AgentState) -> dict:
    """
    Execute the tool calls from the last AI message.
    Returns ToolMessage results back into the conversation.
    """
    messages = state["messages"]
    last_message = messages[-1]

    tool_results = []
    available_tools = {t.name: t for t in get_tools()}

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call.get("id", tool_name)

            logger.info(f"Executing tool: {tool_name}({tool_args})")

            if tool_name in available_tools:
                try:
                    result = available_tools[tool_name].invoke(tool_args)
                    # Convert result to string if needed
                    if isinstance(result, (list, dict)):
                        result_str = json.dumps(result, indent=2, default=str)
                    else:
                        result_str = str(result)
                except Exception as e:
                    result_str = f"Error executing {tool_name}: {str(e)}"
                    logger.error(f"Tool execution error: {e}", exc_info=True)
            else:
                result_str = f"Error: Unknown tool '{tool_name}'"

            tool_results.append(
                ToolMessage(content=result_str, tool_call_id=tool_id)
            )

    return {"messages": tool_results}


# ============================================================================
# ROUTING LOGIC
# ============================================================================

def should_continue(state: AgentState) -> str:
    """
    Decide whether to continue the agent loop or end.
    If the last message has tool calls → execute tools.
    Otherwise → end (the LLM gave a final answer).
    """
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"


# ============================================================================
# BUILD THE AGENT GRAPH
# ============================================================================

def build_agent_graph():
    """
    Build the ReAct agent graph:

    ┌─────────┐     tool_calls?     ┌───────────┐
    │  Agent  │ ──── YES ──────────▶│   Tools   │
    │  (LLM)  │◀────────────────────│ (execute) │
    └────┬────┘                     └───────────┘
         │ NO (final answer)
         ▼
       [END]
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Conditional edge: agent → tools or END
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    # After tools, always go back to agent
    workflow.add_edge("tools", "agent")

    return workflow.compile()


# ============================================================================
# FALLBACK: Simple Router (for models without tool calling)
# ============================================================================

def run_router_fallback(user_query: str, session_history: List[Dict] = None) -> Dict[str, Any]:
    """
    Fallback router for models that don't support tool calling (e.g. qwen2.5:0.5b).
    Uses simple keyword-based intent classification.
    """
    logger.info("Using router fallback (model may not support tool calling)")
    llm = get_agent_llm()
    q_lower = user_query.strip().lower()

    # Simple keyword-based intent detection
    import re
    search_triggers = [
        "find ", "find the ", "show ", "show me ", "search ", "search for ",
        "where is ", "open ", "find file", "find code", "show code", "show file",
        "do i have", "list files", "any ", "find my ", "resume", "cv",
        "document", "pdf", "txt", "docx", "file", "files",
    ]

    is_search = (
        any(trigger in q_lower for trigger in search_triggers)
        or re.search(r"\.(py|cpp|c|js|java|txt|md|docx|pdf|xlsx|pptx|html)\b", q_lower)
    )

    if is_search:
        k = 10 if "all" in q_lower else 5
        tool_result = tool_module.search_files.invoke({"query": user_query, "k": k})
        results = []
        if isinstance(tool_result, list):
            for r in tool_result:
                results.append({
                    "path": r.get("source", ""),
                    "source": r.get("source", ""),
                    "summary": r.get("summary", ""),
                    "relevance_score": r.get("score", 0),
                    "processing_status": r.get("processing_status", "unknown"),
                    "content": r.get("content", ""),
                })
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        answer = f"I found {len(results)} files matching '{user_query}'."
        return {
            "answer": answer,
            "tool_used": "search_files",
            "sources": results,
            "tool_calls": 1,
            "intent": "AGENT",
            "agent_type": "router_fallback",
        }
    else:
        # General chat
        prompt = f"You are a helpful assistant. Reply to the user.\nUser: {user_query}"
        response = llm.invoke([HumanMessage(content=prompt)])
        return {
            "answer": response.content,
            "tool_used": "none",
            "sources": [],
            "tool_calls": 0,
            "intent": "CHAT",
            "agent_type": "router_fallback",
        }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def run_agent_pipeline(user_query: str, session_history: List[Dict] = None) -> Dict[str, Any]:
    """
    Run the agentic pipeline. Tries the full ReAct agent first,
    falls back to the simple router if tool calling isn't supported.

    Args:
        user_query: The user's question or command.
        session_history: Previous conversation messages (optional).

    Returns:
        Dict with answer, sources, tool_used, tool_calls, intent, agent_type.
    """
    logger.info(f"Agent received: {user_query}")

    try:
        # Build the agent graph
        graph = build_agent_graph()

        # Construct message history
        messages: List[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]

        # Add session history if available
        if session_history:
            for msg in session_history[-6:]:  # Last 6 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        # Add current query
        messages.append(HumanMessage(content=user_query))

        # Run the agent graph
        initial_state = {"messages": messages}
        final_state = graph.invoke(initial_state)

        # Extract results from final state
        all_messages = final_state["messages"]

        # Find the final AI response (last AIMessage)
        final_answer = ""
        sources = []
        tool_calls_count = 0
        tools_used = set()

        for msg in all_messages:
            if isinstance(msg, AIMessage):
                # Check for tool calls
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls_count += 1
                        tools_used.add(tc["name"])
                # The last AIMessage with content is the final answer
                if msg.content and msg.content.strip():
                    final_answer = msg.content.strip()

            elif isinstance(msg, ToolMessage):
                # Try to extract sources from search results
                try:
                    content = msg.content
                    parsed = json.loads(content)
                    if isinstance(parsed, list):
                        for item in parsed:
                            if isinstance(item, dict) and item.get("source"):
                                sources.append({
                                    "path": item.get("source", ""),
                                    "source": item.get("source", ""),
                                    "summary": item.get("summary", ""),
                                    "relevance_score": item.get("score", 0),
                                    "content": item.get("content", ""),
                                })
                except (json.JSONDecodeError, TypeError):
                    pass

        tool_used_str = ", ".join(tools_used) if tools_used else "none"
        intent = "AGENT" if tool_calls_count > 0 else "CHAT"

        logger.info(
            f"Agent completed: tools_used={tool_used_str}, "
            f"tool_calls={tool_calls_count}, intent={intent}"
        )

        return {
            "answer": final_answer,
            "tool_used": tool_used_str,
            "sources": sources,
            "tool_calls": tool_calls_count,
            "intent": intent,
            "agent_type": "react_v1",
        }

    except Exception as e:
        error_msg = str(e)
        logger.warning(f"ReAct agent failed ({error_msg}), falling back to router")

        # Check if it's a tool-calling capability issue
        if any(keyword in error_msg.lower() for keyword in [
            "tool", "function", "does not support", "bind_tools",
            "invalid", "json", "parse",
        ]):
            logger.info("Model likely doesn't support tool calling, using router")
            return run_router_fallback(user_query, session_history)

        # For other errors, also try fallback
        try:
            return run_router_fallback(user_query, session_history)
        except Exception as fallback_error:
            logger.error(f"Both agent and fallback failed: {fallback_error}", exc_info=True)
            return {
                "answer": f"I encountered an error: {error_msg}",
                "tool_used": "error",
                "sources": [],
                "tool_calls": 0,
                "intent": "ERROR",
                "agent_type": "error",
            }
