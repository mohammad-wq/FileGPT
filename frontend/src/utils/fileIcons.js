/**
 * File icon utilities
 * Maps file extensions to emoji icons
 */

export const getFileIcon = (path) => {
    // Return the uppercase extension as a small badge-like string instead of emojis
    const ext = path && path.includes('.') ? path.split('.').pop().toLowerCase() : '';
    if (!ext) return "FILE";
    return ext.toUpperCase();
};

/**
 * Format file size in human-readable format
 */
export const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";

    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
};

/**
 * Get file name from full path
 */
export const getFileName = (path) => {
    return path.split('\\').pop() || path.split('/').pop() || path;
};

/**
 * Get file extension
 */
export const getFileExtension = (path) => {
    const parts = path.split('.');
    return parts.length > 1 ? parts.pop().toLowerCase() : '';
};

/**
 * Check if path is a directory
 */
export const isDirectory = (path) => {
    return !getFileExtension(path);
};
