import { useState } from "react";
import { getFileIcon, getFileName } from "../utils/fileIcons";
import { Command } from "@tauri-apps/plugin-shell";
import { openUrl } from "@tauri-apps/plugin-opener";

/**
 * FileCard Component - Professional Search Result Display
 * Displays file with scrollable content, summary, confidence score, and inline action buttons
 */
export default function FileCard({ file, onClick }) {
    const [showActions, setShowActions] = useState(false);
    const [isOpening, setIsOpening] = useState(false);

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
                    {file.summary && !file.summary.toLowerCase().includes('pending') && (
                        <div className="file-card-pro-summary-section">
                            <div className="file-card-pro-summary">{file.summary}</div>
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
