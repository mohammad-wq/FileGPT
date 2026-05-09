import { useState } from "react";
import apiClient from "../api/client";
import FileCard from "./FileCard";
import { Brain, BrainCircuitIcon, Search, SearchCheckIcon } from "lucide-react";

export default function SearchView() {
  const [searchQuery, setSearchQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState(null);
  const [showAll, setShowAll] = useState(false);
  const [minScore, setMinScore] = useState(0.25);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || isLoading) return;
    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    try {
      const response = await apiClient.search(searchQuery.trim(), 20, minScore);
      if (response.results && response.results.length > 0) {
        const mappedResults = response.results.map((r) => ({
          path: r.source,
          summary: r.summary,
          relevance_score: r.score,
        }));
        setResults(mappedResults);
        setShowAll(false);
      } else {
        setResults([]);
        setShowAll(false);
      }
    } catch (err) {
      setError(err.message || "Failed to perform search.");
      setResults([]);
    } finally { setIsLoading(false); }
  };

  const handleKeyDown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSearch(e); } };

  return (
    <div className="search-view">
      <div className="search-header">
        <h2 className="search-title"><Brain color="#3b82f6" strokeWidth={2.5} size={28}/> Semantic Explorer</h2>
        <p className="search-subtitle">Deep search through your files using natural language</p>
      </div>

      <form onSubmit={handleSearch} className="search-form">
        <div className="search-input-wrapper">
          <input
            type="text"
            className="search-input"
            placeholder="Search for files... (e.g., 'Python code', 'project docs')"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button type="submit" className="search-button" disabled={isLoading || !searchQuery.trim()}>
            {isLoading ? "Searching..." : "Search"}
          </button>
        </div>
      </form>

      <div className="search-threshold-bar">
        <div className="threshold-label-row">
          <label>Relevance Precision</label>
          <span className="threshold-value">{Math.round(minScore * 100)}%</span>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={minScore}
          onChange={(e) => setMinScore(parseFloat(e.target.value))}
          className="threshold-slider"
        />
      </div>

      <div className="search-results-area">
        {isLoading && <div className="search-loading"><p>Scanning index...</p></div>}
        {error && <div className="search-error"><p>{error}</p></div>}
        
        {hasSearched && !isLoading && results.length === 0 && (
          <div className="search-no-results"><h3>No Results</h3><p>Try lowering the precision or using different keywords.</p></div>
        )}

        {hasSearched && !isLoading && results.length > 0 && (
          <div className="search-results">
            <div className="results-grid">
              {(showAll ? results : results.slice(0, 5)).map((file, index) => (
                <FileCard key={index} file={file} />
              ))}
            </div>
            {results.length > 5 && (
              <button className="search-show-more-btn" onClick={() => setShowAll(!showAll)}>
                {showAll ? "Show Less" : `Show ${results.length - 5} More`}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
