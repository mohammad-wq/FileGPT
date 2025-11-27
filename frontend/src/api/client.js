/**
 * API Client for FileGPT Backend
 * Centralized service for all backend API calls
 */

const API_BASE = "http://127.0.0.1:8000";

class APIClient {
    /**
     * Make a request to the backend API
     */
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;

        try {
            const response = await fetch(url, {
                headers: {
                    "Content-Type": "application/json",
                    ...options.headers,
                },
                ...options,
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `API Error: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API request failed for ${endpoint}:`, error);
            throw error;
        }
    }

    /**
     * Check backend health status
     */
    async checkHealth() {
        return this.request("/");
    }

    /**
     * Search for files using hybrid search (semantic + keyword)
     */
    async search(query, k = 5) {
        return this.request("/search", {
            method: "POST",
            body: JSON.stringify({ query, k }),
        });
    }

    /**
     * Ask a question and get AI-generated answer with context
     */
    async ask(query, k = 5) {
        return this.request("/ask", {
            method: "POST",
            body: JSON.stringify({ query, k }),
        });
    }

    /**
     * Add a folder to watch list and index
     */
    async addFolder(path) {
        return this.request("/add_folder", {
            method: "POST",
            body: JSON.stringify({ path }),
        });
    }

    /**
     * Get list of watched folders
     */
    async getWatchedFolders() {
        return this.request("/watched_folders");
    }

    /**
     * Get system statistics
     */
    async getStats() {
        return this.request("/stats");
    }

    /**
     * List contents of a directory
     */
    async listDirectory(path) {
        return this.request("/list", {
            method: "POST",
            body: JSON.stringify({ path }),
        });
    }

    /**
     * Create a new folder
     */
    async createFolder(path) {
        return this.request("/create_folder", {
            method: "POST",
            body: JSON.stringify({ path }),
        });
    }

    /**
     * Rename a file or folder
     */
    async rename(oldPath, newPath) {
        return this.request("/rename", {
            method: "POST",
            body: JSON.stringify({ old_path: oldPath, new_path: newPath }),
        });
    }

    /**
     * Move a file or folder
     */
    async move(source, destination) {
        return this.request("/move", {
            method: "POST",
            body: JSON.stringify({ source, destination }),
        });
    }

    /**
     * Delete a file or folder
     */
    async delete(path) {
        return this.request("/delete", {
            method: "DELETE",
            body: JSON.stringify({ path }),
        });
    }

    /**
     * Categorize files based on description
     */
    async categorize(categoryDescription, searchPath = null, maxFiles = 100) {
        return this.request("/categorize", {
            method: "POST",
            body: JSON.stringify({
                category_description: categoryDescription,
                search_path: searchPath,
                max_files: maxFiles,
            }),
        });
    }

    /**
     * Auto-organize files into a folder by category
     */
    async organize(
        categoryDescription,
        destinationFolder,
        searchPath = null,
        minConfidence = 0.6,
        dryRun = false
    ) {
        return this.request("/organize", {
            method: "POST",
            body: JSON.stringify({
                category_description: categoryDescription,
                destination_folder: destinationFolder,
                search_path: searchPath,
                min_confidence: minConfidence,
                dry_run: dryRun,
            }),
        });
    }

    /**
     * Get AI-suggested categories for files
     */
    async suggestCategories(filePaths) {
        return this.request("/suggest_categories", {
            method: "POST",
            body: JSON.stringify({ file_paths: filePaths }),
        });
    }
}

// Export singleton instance
export default new APIClient();
