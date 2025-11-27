/**
 * Path utilities for handling cross-platform paths
 */

/**
 * Get a safe default path for common locations
 * These are placeholders - backend will resolve to actual user paths
 */
export const getCommonPath = (location) => {
    const locations = {
        desktop: "Desktop",
        documents: "Documents",
        downloads: "Downloads",
        pictures: "Pictures",
        music: "Music",
        videos: "Videos",
    };

    return locations[location.toLowerCase()] || location;
};

/**
 * Parse destination from organization query
 * Returns a path that backend can resolve
 */
export const parseDestinationPath = (query) => {
    const destinationMatch = query.match(/(?:in|to|into|at)\s+(.+?)(?:\s|$)/i);

    if (!destinationMatch) {
        return null;
    }

    let destinationPath = destinationMatch[1].trim();

    // Handle common location shortcuts
    if (destinationPath.toLowerCase().includes("desktop")) {
        // Extract the folder name after "desktop"
        const folderName = destinationPath.replace(/.*desktop[\\/]*/i, "").trim();
        return folderName ? `Desktop\\${folderName}` : "Desktop";
    }

    if (destinationPath.toLowerCase().includes("documents")) {
        const folderName = destinationPath.replace(/.*documents[\\/]*/i, "").trim();
        return folderName ? `Documents\\${folderName}` : "Documents";
    }

    if (destinationPath.toLowerCase().includes("downloads")) {
        const folderName = destinationPath.replace(/.*downloads[\\/]*/i, "").trim();
        return folderName ? `Downloads\\${folderName}` : "Downloads";
    }

    // Return as-is if no special handling needed
    return destinationPath;
};

/**
 * Extract category description from organization query
 */
export const parseCategoryDescription = (query) => {
    return query
        .replace(/^(put all|move all|organize|collect all|gather all|move files|sort files)\s+/i, "")
        .replace(/(?:in|to|into|at)\s+.+$/i, "")
        .trim();
};
