import { useState } from "react";
import { getFileIcon, getFileName } from "../utils/fileIcons";
import { Command } from "@tauri-apps/plugin-shell";
import { openUrl } from "@tauri-apps/plugin-opener";

/**
 * FileCard Component
 * Displays a single file result with icon, name, path, and summary
 * Clickable to show actions: Open File or Reveal in Explorer
 */
export default function FileCard({ file, onClick }) {
    const [showActions, setShowActions] = useState(false);

    const handleClick = () => {
        if (onClick) {
            onClick(file);
        } else {
            setShowActions(true);
        }
    };

    const handleRevealInExplorer = async (e) => {
        e.stopPropagation();
        try {
            // Use explorer.exe /select to open Explorer and select the file
            const command = Command.create('explorer', ['/select,', file.path]);
            await command.execute();
            setShowActions(false);
        } catch (error) {
            console.error("Error opening file location:", error);
            // Fallback: try to just open the folder containing the file
            try {
                const folderPath = file.path.substring(0, file.path.lastIndexOf('\\'));
                const command = Command.create('explorer', [folderPath]);
                await command.execute();
                setShowActions(false);
            } catch (fallbackError) {
                console.error("Fallback error:", fallbackError);
            }
        }
    };

    const handleOpenFile = async (e) => {
        e.stopPropagation();
        try {
            // Try method 1: openUrl with file:// protocol
            try {
                await openUrl(`file:///${file.path.replace(/\\/g, '/')}`);
                setShowActions(false);
                return;
            } catch (err) {
                console.log("Method 1 failed, trying method 2...");
            }

            // Try method 2: Use Windows 'start' command
            try {
                const command = Command.create('cmd', ['/c', 'start', '', file.path]);
                await command.execute();
                setShowActions(false);
                return;
            } catch (err) {
                console.log("Method 2 failed, trying method 3...");
            }

            // Try method 3: Direct shell open
            try {
                const command = Command.create('explorer', [file.path]);
                await command.execute();
                setShowActions(false);
            } catch (err) {
                console.error("All file opening methods failed:", err);
                alert("Could not open file. Try 'Reveal in Explorer' instead.");
            }
        } catch (error) {
            console.error("Error opening file:", error);
            alert("Could not open file. Try 'Reveal in Explorer' instead.");
        }
    };

    return (
        <>
            <div className="file-card" onClick={handleClick} title={file.path}>
                <span className="file-card-icon">{getFileIcon(file.path)}</span>
                <div className="file-card-info">
                    <div className="file-card-name">{getFileName(file.path)}</div>
                    <div className="file-card-path">{file.path}</div>
                    {file.summary && (
                        <div className="file-card-summary">{file.summary}</div>
                    )}
                    {file.relevance_score !== undefined && (
                        <div className="file-card-score">
                            Confidence: {Math.min(100, Math.round(file.relevance_score * 100))}%
                        </div>
                    )}
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
