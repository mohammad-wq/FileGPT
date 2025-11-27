import { useState } from "react";
import { getFileIcon, getFileName } from "../utils/fileIcons";
import apiClient from "../api/client";
import toast from "../utils/toast";

/**
 * OrganizationApprovalModal Component
 * Shows a plan for file organization that user can accept or reject
 */
export default function OrganizationApprovalModal({
    plan,
    onAccept,
    onReject,
    onClose,
}) {
    const [isExecuting, setIsExecuting] = useState(false);

    if (!plan) return null;

    const handleAccept = async () => {
        setIsExecuting(true);
        try {
            // First, create the destination folder
            await apiClient.createFolder(plan.destinationFolder);

            // Then move each file
            const movePromises = plan.files.map((file) =>
                apiClient.move(
                    file.path,
                    `${plan.destinationFolder}\\${getFileName(file.path)}`
                )
            );

            await Promise.all(movePromises);

            toast.success(
                `Successfully organized ${plan.files.length} files into ${getFileName(plan.destinationFolder)}`
            );

            if (onAccept) onAccept();
        } catch (error) {
            console.error("Error organizing files:", error);
            toast.error(`Failed to organize files: ${error.message}`);
        } finally {
            setIsExecuting(false);
        }
    };

    const handleReject = () => {
        if (onReject) onReject();
        onClose();
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>📁 Organization Plan</h2>
                    <button className="modal-close" onClick={onClose}>
                        ✕
                    </button>
                </div>

                <div className="modal-body">
                    <div className="plan-section">
                        <div className="plan-label">Destination Folder:</div>
                        <div className="plan-destination">{plan.destinationFolder}</div>
                    </div>

                    <div className="plan-section">
                        <div className="plan-label">
                            Files to Move ({plan.files.length}):
                        </div>
                        <div className="plan-files">
                            {plan.files.map((file, idx) => (
                                <div key={idx} className="plan-file-item">
                                    <span className="plan-file-icon">
                                        {getFileIcon(file.path)}
                                    </span>
                                    <div className="plan-file-info">
                                        <div className="plan-file-name">{getFileName(file.path)}</div>
                                        <div className="plan-file-path">{file.path}</div>
                                        {file.summary && (
                                            <div className="plan-file-summary">{file.summary}</div>
                                        )}
                                        {file.confidence !== undefined && (
                                            <div className="plan-file-confidence">
                                                Confidence: {Math.round(file.confidence * 100)}%
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {plan.category && (
                        <div className="plan-section">
                            <div className="plan-label">Category:</div>
                            <div className="plan-category">{plan.category}</div>
                        </div>
                    )}
                </div>

                <div className="modal-footer">
                    <button
                        className="btn btn-secondary"
                        onClick={handleReject}
                        disabled={isExecuting}
                    >
                        ❌ Reject
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={handleAccept}
                        disabled={isExecuting}
                    >
                        {isExecuting ? "Organizing..." : "✅ Accept & Organize"}
                    </button>
                </div>
            </div>
        </div>
    );
}
