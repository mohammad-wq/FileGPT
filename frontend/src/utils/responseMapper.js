/**
 * Dynamic Response Mapper Utility
 * Handles various backend response formats robustly
 */

/**
 * Normalize file data from various possible formats
 */
export const normalizeFileData = (file) => {
    if (!file) return null;

    return {
        path: file.path || file.source || file.file_path || file.filePath || "",
        summary: file.summary || file.description || file.desc || "",
        relevance_score: file.relevance_score || file.score || file.confidence || 0,
        // Preserve any additional metadata
        ...file,
    };
};

/**
 * Normalize source data (same as file for consistency)
 */
export const normalizeSource = (source) => normalizeFileData(source);

/**
 * Normalize backend response to consistent format
 */
export const normalizeBackendResponse = (response) => {
    if (!response) return null;

    return {
        // Content/Answer
        content: response.answer || response.content || response.message || "",

        // Files/Sources (normalize array)
        files: (response.sources || response.files || response.results || [])
            .map(normalizeFileData)
            .filter(Boolean),

        // Metadata
        intent: response.intent || "unknown",
        session_id: response.session_id || response.sessionId || null,
        context_used: response.context_used || response.contextUsed || 0,

        // Preserve entire original response for debugging
        _raw: response,
    };
};

/**
 * Build assistant message from backend response
 */
export const buildAssistantMessage = (response, messageType = "ask") => {
    const normalized = normalizeBackendResponse(response);

    return {
        role: "assistant",
        type: messageType,
        content: normalized.content,
        files: normalized.files,
        intent: normalized.intent,
        session_id: normalized.session_id,
        context_used: normalized.context_used,
        timestamp: Date.now(),
    };
};

/**
 * Check if response indicates an error
 */
export const isErrorResponse = (response) => {
    return (
        response?.error ||
        response?.status === "error" ||
        response?.detail ||
        false
    );
};

/**
 * Extract error message from response
 */
export const getErrorMessage = (response) => {
    return (
        response?.error?.message ||
        response?.detail ||
        response?.message ||
        "An unknown error occurred"
    );
};
