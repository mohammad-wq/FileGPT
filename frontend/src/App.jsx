import { useState, useEffect, useRef } from "react";
import "./App.css";
import "./components/components.css";
import apiClient from "./api/client";
import toast from "./utils/toast";
import FileCard from "./components/FileCard";
import OrganizationApprovalModal from "./components/OrganizationApprovalModal";
import SearchView from "./components/SearchView";
import ReactMarkdown from "react-markdown";
import { parseDestinationPath, parseCategoryDescription } from "./utils/pathUtils";

function App() {
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState("offline");
  const [stats, setStats] = useState(null);
  const [organizationPlan, setOrganizationPlan] = useState(null);
  const [currentView, setCurrentView] = useState("chat"); // 'chat' or 'search'
  const messagesEndRef = useRef(null);

  // Check backend status on mount
  useEffect(() => {
    checkBackendStatus();
    const interval = setInterval(checkBackendStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const checkBackendStatus = async () => {
    try {
      const response = await apiClient.checkHealth();
      setBackendStatus("online");
      if (response.stats) {
        setStats(response.stats);
      }
    } catch (error) {
      setBackendStatus("offline");
    }
  };

  /**
   * Intelligent query parser with semantic search detection
   * Detects if query is for file organization, explicit search, or Q&A
   */
  const parseQuery = (query) => {
    const lowerQuery = query.toLowerCase();

    // Organization keywords
    const organizationKeywords = [
      "put all",
      "move all",
      "organize",
      "collect all",
      "gather all",
      "move files",
      "sort files",
      "create folder",
    ];

    const isOrganization = organizationKeywords.some((keyword) =>
      lowerQuery.includes(keyword)
    );

    if (isOrganization) {
      return { type: "organize", query };
    }

    // Enhanced search keywords - more comprehensive for semantic search
    const searchKeywords = [
      "show me",
      "find",
      "search",
      "list",
      "display",
      "get all",
      "where are",
      "locate",
      "files about",
      "files on",
      "documents about",
      "look for",
      "all my",
      "my files",
    ];

    const isSearch = searchKeywords.some((keyword) =>
      lowerQuery.includes(keyword)
    );

    // Also check for file type queries (semantic search is great for these)
    const fileTypePatterns = [
      /\b(python|java|javascript|c\+\+|typescript|html|css)\s+(files?|scripts?|code)\b/i,
      /\b(pdf|docx?|xlsx?|pptx?|txt|csv)\s+(files?|documents?)\b/i,
      /\.(py|js|java|cpp|ts|html|css|pdf|docx?|xlsx?|txt)\b/i,
    ];

    const isFileTypeQuery = fileTypePatterns.some((pattern) =>
      pattern.test(query)
    );

    if (isSearch || isFileTypeQuery) {
      return { type: "search", query };
    }

    // Default: treat as Q&A (which also uses semantic search via RAG)
    return { type: "ask", query };
  };

  /**
   * Handle file search with semantic understanding
   */

  const handleSearch = async (query) => {
    try {
      // Perform semantic search - limit to top 5 results
      const response = await apiClient.search(query, 5);

      if (response.results && response.results.length > 0) {
        // Generate intelligent summary of search results using AI
        const topResults = response.results.slice(0, 5);
        const contextParts = [];

        for (const result of topResults) {
          contextParts.push(`File: ${result.source}`);
          if (result.summary) {
            contextParts.push(`Summary: ${result.summary}`);
          }
        }

        // Create AI response about the search results
        let aiSummary = "";
        try {
          const summaryPrompt = `Based on the user's search for "${query}", I found ${response.results.length} files. Here are the top matches:

${contextParts.join('\n')}

Generate a response in MARKDOWN format with the following structure:
1. Start with a brief introductory sentence
2. Use "## 📁 Search Results" as a heading
3. List each file as a numbered item with:
   - **File path** in bold (use full path)
   - Summary on the next line (indented)
4. Keep it concise

Example format:
I found ${response.results.length} Python files related to your search.

## 📁 Search Results

1. **C:\\path\\to\\file.py**
   Summary of what this file does...

2. **C:\\path\\to\\another.py**
   Summary of this file...`;

          const summaryResponse = await fetch("http://127.0.0.1:8000/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: summaryPrompt, k: 0 }),
          });

          if (summaryResponse.ok) {
            const summaryData = await summaryResponse.json();
            aiSummary = summaryData.answer;
          }
        } catch (aiError) {
          console.log("AI summary generation failed, using default message");
          // Fallback to markdown formatted message
          aiSummary = `I found **${response.results.length}** files matching "${query}".\n\n## 📁 Search Results\n\nHere are the most relevant results:`;
        }

        const assistantMessage = {
          role: "assistant",
          content: aiSummary || `Found ${response.results.length} files matching "${query}":`,
          files: response.results.map((r) => ({
            path: r.source,
            summary: r.summary,
            relevance_score: r.score,
          })),
          type: "search",
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        // No results - provide helpful AI-generated suggestions
        let noResultsMessage = "";
        try {
          const suggestionPrompt = `The user searched for "${query}" but no files were found. Suggest 2-3 alternative search terms or keywords they could try, or explain why their search might not have found results. Be helpful and concise.`;

          const suggestionResponse = await fetch("http://127.0.0.1:8000/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: suggestionPrompt, k: 0 }),
          });

          if (suggestionResponse.ok) {
            const suggestionData = await suggestionResponse.json();
            noResultsMessage = suggestionData.answer;
          }
        } catch (aiError) {
          noResultsMessage = "No files found matching your search. Try adding more folders to index or using different keywords.";
        }

        const assistantMessage = {
          role: "assistant",
          content: noResultsMessage,
          type: "search",
        };

        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      throw error;
    }
  };

  /**
   * Handle AI Q&A
   */
  const handleAsk = async (query) => {
    try {
      const response = await apiClient.ask(query, 5);

      const assistantMessage = {
        role: "assistant",
        content: response.answer,
        files: response.sources
          ? response.sources.map((s) => ({
            path: s.path,
            summary: s.summary,
            relevance_score: s.relevance_score,
          }))
          : [],
        type: "ask",
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      throw error;
    }
  };

  /**
   * Handle file organization request
   */
  const handleOrganize = async (query) => {
    try {
      // Parse destination and category from query using utilities
      const destinationPath = parseDestinationPath(query);
      const categoryDescription = parseCategoryDescription(query);

      // First, categorize to find matching files
      const categorizeResponse = await apiClient.categorize(
        categoryDescription,
        null,
        100
      );

      if (!categorizeResponse.results || categorizeResponse.results.length === 0) {
        const assistantMessage = {
          role: "assistant",
          content: `I couldn't find any files matching "${categoryDescription}". Try being more specific or check if the files are indexed.`,
          type: "organize",
        };

        setMessages((prev) => [...prev, assistantMessage]);
        return;
      }

      // Create organization plan
      const plan = {
        category: categoryDescription,
        destinationFolder: destinationPath || `C:\\Users\\User\\Desktop\\${categoryDescription}`,
        files: categorizeResponse.results.map((r) => ({
          path: r.file_path,
          summary: r.summary,
          confidence: r.confidence,
        })),
      };

      // Show plan to user
      const planMessage = {
        role: "assistant",
        content: `I found ${plan.files.length} files matching "${categoryDescription}". Review the organization plan below:`,
        type: "organize-plan",
        plan: plan,
      };

      setMessages((prev) => [...prev, planMessage]);
      setOrganizationPlan(plan);

    } catch (error) {
      throw error;
    }
  };

  /**
   * Main message handler
   */
  const handleSendMessage = async (e) => {
    e.preventDefault();

    if (!query.trim() || isLoading) return;

    const userMessage = {
      role: "user",
      content: query.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentQuery = query.trim();
    setQuery("");
    setIsLoading(true);

    try {
      // Parse query intent
      const intent = parseQuery(currentQuery);

      if (intent.type === "search") {
        await handleSearch(currentQuery);
      } else if (intent.type === "organize") {
        await handleOrganize(currentQuery);
      } else {
        await handleAsk(currentQuery);
      }

    } catch (error) {
      const errorMessage = {
        role: "assistant",
        content: "Sorry, I encountered an error. Please make sure the FileGPT backend is running.",
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
      console.error("Error:", error);
      toast.error(error.message || "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  const handleOrganizationAccept = () => {
    setOrganizationPlan(null);
    toast.success("Files organized successfully!");

    // Reload stats
    checkBackendStatus();
  };

  const handleOrganizationReject = () => {
    setOrganizationPlan(null);
    const rejectMessage = {
      role: "assistant",
      content: "Organization plan rejected. No files were moved.",
      type: "info",
    };
    setMessages((prev) => [...prev, rejectMessage]);
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-title">
          <h1>FileGPT</h1>
          <div className={`status-badge ${backendStatus}`}>
            <span className="status-dot"></span>
            {backendStatus === "online" ? "Connected" : "Disconnected"}
          </div>
        </div>
        {stats && (
          <div className="header-stats">
            <span className="stat-item">
              📄 {stats.total_documents || 0} files indexed
            </span>
          </div>
        )}
      </header>

      {/* View Toggle */}
      <div className="view-toggle">
        <button
          className={`view-toggle-btn ${currentView === "chat" ? "active" : ""}`}
          onClick={() => setCurrentView("chat")}
        >
          💬 Chat
        </button>
        <button
          className={`view-toggle-btn ${currentView === "search" ? "active" : ""}`}
          onClick={() => setCurrentView("search")}
        >
          🔍 Search
        </button>
      </div>

      {/* Conditional View Rendering */}
      {currentView === "search" ? (
        <SearchView />
      ) : (
        <div className="chat-container">
          <div className="messages-area">
            {messages.length === 0 ? (
              <div className="welcome-state">
                <div className="welcome-icon">🚀</div>
                <h2>Welcome to FileGPT</h2>
                <p>
                  Your AI-powered file assistant with semantic search. Try these:
                </p>
                <div className="example-queries">
                  <div className="example-query">� Semantic Search: "Find Python files about sorting"</div>
                  <div className="example-query">� Ask Questions: "What files do I have about machine learning?"</div>
                  <div className="example-query">📁 Organize: "Put all PDF documents in a folder"</div>
                  <div className="example-query">🎯 Smart Search: "Locate all JavaScript code"</div>
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <div key={index} className={`message ${message.role}`}>
                  <div className="message-avatar">
                    {message.role === "user" ? "👤" : "🤖"}
                  </div>
                  <div className="message-content">
                    <div className="message-text">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>

                    {message.files && message.files.length > 0 && (
                      <div className="file-results">
                        {message.files.map((file, idx) => (
                          <FileCard key={idx} file={file} />
                        ))}
                      </div>
                    )}

                    {message.type === "organize-plan" && message.plan && (
                      <div className="plan-preview">
                        <button
                          className="btn btn-primary"
                          onClick={() => setOrganizationPlan(message.plan)}
                        >
                          📋 Review Organization Plan
                        </button>
                      </div>
                    )}

                    {message.error && (
                      <div className="error-message">
                        Make sure the backend is running: <code>python backend/start.py</code>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {isLoading && (
              <div className="loading-message">
                <div className="message-avatar">🤖</div>
                <div className="loading-dots">
                  <div className="loading-dot"></div>
                  <div className="loading-dot"></div>
                  <div className="loading-dot"></div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="input-area">
            <form onSubmit={handleSendMessage} className="input-container">
              <div className="input-wrapper">
                <textarea
                  className="query-input"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about your files, search, or organize..."
                  rows="1"
                  disabled={isLoading || backendStatus === "offline"}
                />
              </div>
              <button
                type="submit"
                className="send-button"
                disabled={isLoading || !query.trim() || backendStatus === "offline"}
              >
                {isLoading ? "Sending..." : "Send 🚀"}
              </button>
            </form>
          </div>
        </div>
      )}

      {organizationPlan && (
        <OrganizationApprovalModal
          plan={organizationPlan}
          onAccept={handleOrganizationAccept}
          onReject={handleOrganizationReject}
          onClose={() => setOrganizationPlan(null)}
        />
      )}
    </div>
  );
}

export default App;

