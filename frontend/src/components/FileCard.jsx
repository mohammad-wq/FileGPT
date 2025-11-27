import { getFileIcon, getFileName } from "../utils/fileIcons";
import * as opener from "@tauri-apps/plugin-opener";

/**
 * FileCard Component
 * Displays a single file result with icon, name, path, and summary
 * Clickable to open the file
 */
export default function FileCard({ file, onClick }) {
    const handleClick = async () => {
        if (onClick) {
            onClick(file);
        } else {
            // Default: open the file
            try {
                await opener.open(file.path);
            } catch (error) {
                console.error("Error opening file:", error);
            }
        }
    };

    return (
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
                        Confidence: {Math.round(file.relevance_score * 100)}%
                    </div>
                )}
            </div>
        </div>
    );
}
