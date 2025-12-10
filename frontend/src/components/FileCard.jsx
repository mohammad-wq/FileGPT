import { useState, useRef, useEffect } from "react";
import hljs from 'highlight.js/lib/common';
import { getFileIcon, getFileName } from "../utils/fileIcons";
import { Command } from "@tauri-apps/plugin-shell";
import { openUrl } from "@tauri-apps/plugin-opener";
import apiClient from "../api/client";
import toast from "../utils/toast";

/**
 * FileCard Component - Professional Search Result Display
 * Displays file with scrollable content, summary, confidence score, and inline action buttons
 */
export default function FileCard({ file, onClick }) {
    const [showActions, setShowActions] = useState(false);
    const [isOpening, setIsOpening] = useState(false);
    const [expanded, setExpanded] = useState(false);
    const codeRef = useRef(null);
    const [isSummarizing, setIsSummarizing] = useState(false);
    const [summaryFromAI, setSummaryFromAI] = useState(null);

    const handleRevealInExplorer = async (e) => {
        e.stopPropagation();
        setIsOpening(true);
        try {
            const command = Command.create('explorer', ['/select,', file.path]);
            await command.execute();
        } catch (error) {
            console.error("Error revealing file:", error);
            try {
                const folderPath = file.path.substring(0, file.path.lastIndexOf('\\'));
                const command = Command.create('explorer', [folderPath]);
                await command.execute();
            } catch (fallbackError) {
                console.error("Fallback error:", fallbackError);
                alert("Could not open file location.");
            }
        } finally {
            setIsOpening(false);
        }
    };

    const handleOpenFile = async (e) => {
        e.stopPropagation();
        setIsOpening(true);
        try {
            // Method 1: Try openUrl first (works for many file types)
            try {
                await openUrl(`file:///${file.path.replace(/\\/g, '/')}`);
                setIsOpening(false);
                return;
            } catch (err) {
                console.log("openUrl failed, trying cmd...");
            }

            // Method 2: Use cmd to open file with default application
            try {
                const command = Command.create('cmd', ['/c', 'start', '', file.path]);
                await command.execute();
                setIsOpening(false);
                return;
            } catch (err) {
                console.error("Failed to open file:", err);
                alert("Could not open file. Try 'Reveal in Explorer' instead.");
            }
        } catch (error) {
            console.error("Error opening file:", error);
            alert("Could not open file. Try 'Reveal in Explorer' instead.");
        } finally {
            setIsOpening(false);
        }
    };

    const handleToggleExpand = (e) => {
        e?.stopPropagation();
        setExpanded((s) => !s);
    };

    // Highlight code after expanding (uses global hljs from CDN)
    useEffect(() => {
        if (expanded) {
            // small timeout to ensure DOM updated
            setTimeout(() => {
                try {
                    const el = codeRef.current;
                    if (el && hljs && typeof hljs.highlightElement === 'function') {
                        hljs.highlightElement(el);
                    }
                } catch (err) {
                    // fail silently
                    console.error('Highlighting failed', err);
                }
            }, 0);
        }
    }, [expanded]);

    const handleCopyContent = async (e) => {
        e?.stopPropagation();
        const text = file.content || file.summary || '';
        try {
            if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
                // small visual feedback could be toast; avoid import cycle
            } else {
                // fallback
                const area = document.createElement('textarea');
                area.value = text;
                document.body.appendChild(area);
                area.select();
                document.execCommand('copy');
                document.body.removeChild(area);
            }
        } catch (err) {
            console.error('Copy failed', err);
        }
    };

    const confidencePercent = file.relevance_score !== undefined
        ? Math.min(100, Math.round(file.relevance_score * 100))
        : 0;

    const processingStatus = file.processing_status || 'unknown';
    const isPending = processingStatus === 'pending_summary' || processingStatus === 'pending_embedding';

    return (
        <>
            <div className="file-card-professional">
                {/* Compact Header - Icon + Name + Badge */}
                <div className="file-card-pro-header">
                    <div className="file-card-pro-header-left">
                        <span className="file-card-pro-icon">{getFileIcon(file.path)}</span>
                        <div className="file-card-pro-header-text">
                            <div className="file-card-pro-name">{getFileName(file.path)}</div>
                        </div>
                    </div>

                    {/* Confidence Badge */}
                    {file.relevance_score !== undefined && (
                        <div className="confidence-badge">{confidencePercent}%</div>
                    )}
                </div>

                {/* Path - Subtle secondary info */}
                <div className="file-card-pro-path-bar">
                    <span className="path-icon">📍</span>
                    <span className="file-card-pro-path" title={file.path}>{file.path}</span>
                </div>

                {/* Content Area - Show only summary for cleaner look */}
                <div className="file-card-pro-content-wrapper">
                    {/* Summary Section */}

                        {/* Summary or fallback */}
                        {file.summary && !file.summary.toLowerCase().includes('pending') ? (
                            <div className="file-card-pro-summary-section" onClick={handleToggleExpand}>
                                <div className="file-card-pro-summary">{file.summary}</div>
                            </div>
                        ) : (
                            <div className="file-card-pro-summary-section file-card-pro-summary-fallback">
                                <div className="file-card-pro-summary">No summary available yet.</div>
                            </div>
                        )}

                        {/* Expanded content - show code or full text */}
                        {expanded && (
                            <div className="file-card-pro-content-section" role="region" aria-label={`Expanded content for ${getFileName(file.path)}`}>
                                <div className="file-code-block">
                                    <div className="code-toolbar">
                                        <div className="code-filename">{getFileName(file.path)}</div>
                                        <div className="code-actions">
                                            <button aria-label="Copy file content" className="copy-btn" onClick={handleCopyContent}>Copy</button>
                                            <button aria-label="Generate AI summary" className="ai-summary-btn" onClick={async (e) => {
                                                e?.stopPropagation();
                                                if (isSummarizing) return;
                                                setIsSummarizing(true);
                                                try {
                                                    const content = (file.content || file.summary || '').trim();
                                                    if (!content) {
                                                        toast.warning('No file content available to summarize');
                                                        setIsSummarizing(false);
                                                        return;
                                                    }

                                                    const prompt = `You are a concise code summarizer. Provide a short (2-4 sentence) summary of what this file does. If it contains code, list up to 3 key functions or components found (name and 1-line description). Respond in Markdown.\n\nFile path: ${file.path}\n\nContent:\n${content}`;

                                                    const resp = await apiClient.ask(prompt, 0);
                                                    if (resp && (resp.answer || resp.content)) {
                                                        setSummaryFromAI(resp.answer || resp.content);
                                                        setExpanded(true);
                                                    } else if (resp && resp.results && resp.results.length > 0) {
                                                        setSummaryFromAI(resp.results[0].summary || resp.results[0].content || null);
                                                        setExpanded(true);
                                                    } else {
                                                        toast.error('No summary returned');
                                                    }
                                                } catch (err) {
                                                    console.error('Summary generation failed', err);
                                                    toast.error(err.message || 'Failed to generate summary');
                                                } finally {
                                                    setIsSummarizing(false);
                                                }
                                            }} disabled={isSummarizing}>
                                                {isSummarizing ? 'Summarizing...' : 'AI Summary'}
                                            </button>
                                        </div>
                                    </div>
                                    <pre className="code-pre"><code ref={codeRef} className="hljs">{file.content || file.summary || ''}</code></pre>
                                    {summaryFromAI && (
                                        <div className="ai-summary-block">
                                            <div className="ai-summary-label">AI Summary</div>
                                            <div className="ai-summary-content" style={{marginTop:8}} dangerouslySetInnerHTML={{__html: (summaryFromAI || '').replace(/\n/g,'<br/>') }} />
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                    {/* Status Section */}
                    {isPending && (
                        <div className="file-card-pro-status-section">
                            <span className="status-dot"></span>
                            <span>Processing summary...</span>
                        </div>
                    )}
                </div>

                {/* Footer with Action Buttons */}
                <div className="file-card-pro-footer">
                    <button
                        className="file-action-btn file-action-btn-primary"
                        onClick={handleOpenFile}
                        disabled={isOpening}
                        title="Open file"
                    >
                        <span>📄 Open</span>
                    </button>
                    <button
                        className="file-action-btn file-action-btn-secondary"
                        onClick={handleRevealInExplorer}
                        disabled={isOpening}
                        title="Show in Folder"
                    >
                        <span>📁 Folder</span>
                    </button>
                </div>
            </div>

            {showActions && (
                <div className="file-action-overlay" onClick={() => setShowActions(false)}>
                    <div className="file-action-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="file-action-title">File Actions</div>
                        <div className="file-action-path">{getFileName(file.path)}</div>

                        <div className="file-action-buttons">
                            <button className="action-btn secondary" onClick={handleOpenFile}>
                                📄 Open File
                            </button>
                            <button className="action-btn secondary" onClick={handleRevealInExplorer}>
                                📂 Reveal in Explorer
                            </button>
                            <button className="action-btn cancel" onClick={() => setShowActions(false)}>
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
