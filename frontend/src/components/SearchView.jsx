import { useState } from "react";
import apiClient from "../api/client";
import FileCard from "./FileCard";

/**
 * SearchView Component
 * Dedicated semantic search interface
 */
export default function SearchView() {
  const [searchQuery, setSearchQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!searchQuery.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const response = await apiClient.search(searchQuery.trim(), 20);
      
      if (response.results && response.results.length > 0) {
        // Map results to match FileCard format
        const mappedResults = response.results.map((r) => ({
          path: r.source,
          summary: r.summary,
          relevance_score: r.score,
        }));
        setResults(mappedResults);
      } else {
        setResults([]);
      }
    } catch (err) {
      console.error("Search error:", err);
      setError(err.message || "Failed to perform search. Make sure the backend is running.");
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSearch(e);
    }
  };

  return (
    <div className="search-view">
      {/* Search Header */}
      <div className="search-header">
        <h2 className="search-title">🔍 Semantic Search</h2>
        <p className="search-subtitle">
          Search your indexed files using natural language
        </p>
      </div>

      {/* Search Input */}
      <form onSubmit={handleSearch} className="search-form">
        <div className="search-input-wrapper">
          <input
            type="text"
            className="search-input"
            placeholder="Search for files... (e.g., 'Python sorting algorithms', 'budget spreadsheets')"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="search-button"
            disabled={isLoading || !searchQuery.trim()}
          >
            {isLoading ? (
              <>
                <span className="spinner"></span>
                Searching...
              </>
            ) : (
              <>
                <span className="search-icon">🔍</span>
                Search
              </>
            )}
          </button>
        </div>
      </form>

      {/* Results Area */}
      <div className="search-results-area">
        {/* Loading State */}
        {isLoading && (
          <div className="search-loading">
            <div className="loading-spinner-large"></div>
            <p>Searching through your files...</p>
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="search-error">
            <div className="error-icon">⚠️</div>
            <h3>Search Error</h3>
            <p>{error}</p>
          </div>
        )}

        {/* Empty State - Before Search */}
        {!hasSearched && !isLoading && (
          <div className="search-empty-state">
            <div className="empty-state-icon">📂</div>
            <h3>Start Searching</h3>
            <p>Enter a query to find files using semantic search</p>
            <div className="search-examples">
              <h4>Try searching for:</h4>
              <div className="example-chips">
                <button
                  className="example-chip"
                  onClick={() => {
                    setSearchQuery("Python files");
                    setTimeout(() => document.querySelector('.search-button')?.click(), 100);
                  }}
                >
                  Python files
                </button>
                <button
                  className="example-chip"
                  onClick={() => {
                    setSearchQuery("documents about machine learning");
                    setTimeout(() => document.querySelector('.search-button')?.click(), 100);
                  }}
                >
                  Machine learning docs
                </button>
                <button
                  className="example-chip"
                  onClick={() => {
                    setSearchQuery("spreadsheets");
                    setTimeout(() => document.querySelector('.search-button')?.click(), 100);
                  }}
                >
                  Spreadsheets
                </button>
              </div>
            </div>
          </div>
        )}

        {/* No Results State */}
        {hasSearched && !isLoading && !error && results.length === 0 && (
          <div className="search-no-results">
            <div className="no-results-icon">🔍</div>
            <h3>No Results Found</h3>
            <p>No files matched your search query: <strong>"{searchQuery}"</strong></p>
            <p className="hint">Try using different keywords or add more folders to index</p>
          </div>
        )}

        {/* Results Grid */}
        {hasSearched && !isLoading && !error && results.length > 0 && (
          <div className="search-results">
            <div className="results-header">
              <h3>
                Found {results.length} {results.length === 1 ? "file" : "files"}
              </h3>
              <p className="results-query">Search: "{searchQuery}"</p>
            </div>
            <div className="results-grid">
              {results.map((file, index) => (
                <FileCard key={index} file={file} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
