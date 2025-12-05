"""
Conversation session management endpoints
"""

@app.post("/clear_conversation")
async def clear_conversation(session_id: str):
    """
    Clear conversation history for a specific session.
    
    Args:
        session_id: Session identifier to clear
        
    Returns:
        Status message
    """
    session_mgr = session_service.get_session_manager()
    session_mgr.clear_session(session_id)
    
    return {
        "status": "success",
        "message": f"Conversation cleared for session {session_id}"
    }


@app.get("/session_stats")
async def get_session_stats():
    """
    Get session manager statistics.
    
    Returns:
        Session statistics
    """
    session_mgr = session_service.get_session_manager()
    return session_mgr.get_stats()
