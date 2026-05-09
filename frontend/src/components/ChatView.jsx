import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import FileCard from "./FileCard";
import SearchView from "./SearchView";
import { Zap, MessageSquare, Search, User, Bot, Send } from "lucide-react";

export default function ChatView({ 
  messages, 
  handleSendMessage, 
  query, 
  setQuery, 
  isLoading, 
  backendStatus, 
  handleKeyDown,
  setOrganizationPlan,
  showAllFilesIdx,
  setShowAllFilesIdx,
  messagesEndRef
}) {
  const [activeTab, setActiveTab] = useState("chat"); // 'chat' or 'search'

  return (
    <div className="chat-view-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="chat-tabs">
        <button 
          className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <MessageSquare size={18} /> AI Assistant
        </button>
        <button 
          className={`tab-btn ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          <Search size={18} /> Semantic Search
        </button>
      </div>

      <div className="chat-tab-content" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {activeTab === 'chat' ? (
          <div className="chat-container">
            <div className="messages-area">
              {messages.length === 0 ? (
                <div className="welcome-state">
                  <div className="welcome-icon">
                    <Zap size={48} color="var(--accent-primary)" fill="rgba(59, 130, 246, 0.2)" />
                  </div>
                  <h2>FileGPT Assistant</h2>
                  <p style={{marginTop: "-1rem"}}> Ask me about your files, content, or system status.</p>
                </div>
              ) : (
                messages.map((message, index) => (
                  <div key={index} className={`message ${message.role}`}>
                    <div className="message-avatar">
                      {message.role === "user" ? <User size={18} /> : <Bot size={18} color="var(--accent-primary)" />}
                    </div>
                    <div className="message-content">
                      <div className="message-text"><ReactMarkdown>{message.content}</ReactMarkdown></div>
                      {message.files && message.files.length > 0 && (
                        <div className="file-results">
                          {(showAllFilesIdx === index ? message.files : message.files.slice(0, 5)).map((file, idx) => (
                            <FileCard key={idx} file={file} />
                          ))}
                          {message.files.length > 5 && showAllFilesIdx !== index && (
                            <button className="search-show-more-btn" onClick={() => setShowAllFilesIdx(index)}>
                              Show {message.files.length - 5} more results
                            </button>
                          )}
                        </div>
                      )}
                      {message.type === "organize-plan" && message.plan && (
                        <div className="plan-preview">
                          <button className="btn btn-primary" onClick={() => setOrganizationPlan(message.plan)}>📋 Review Plan</button>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="input-area">
              <form onSubmit={handleSendMessage} className="input-container">
                <textarea className="query-input" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={handleKeyDown} placeholder="Ask FileGPT anything..." rows="1" disabled={isLoading || backendStatus === "offline"} />
                <button type="submit" className="send-button" disabled={isLoading || !query.trim() || backendStatus === "offline"}>
                  {isLoading ? "Thinking..." : <><Send size={18} /> Send</>}
                </button>
              </form>
            </div>
          </div>
        ) : (
          <SearchView />
        )}
      </div>
    </div>
  );
}
