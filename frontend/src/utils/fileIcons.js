/**
 * File icon utilities
 * Maps file extensions to emoji icons
 */

export const getFileIcon = (path) => {
    const ext = path.split('.').pop().toLowerCase();

    const iconMap = {
        // Documents
        pdf: "📄",
        doc: "📝",
        docx: "📝",
        txt: "📝",
        rtf: "📝",
        md: "📖",

        // Spreadsheets
        xlsx: "📊",
        xls: "📊",
        csv: "📊",

        // Presentations
        ppt: "📊",
        pptx: "📊",

        // Images
        png: "🖼️",
        jpg: "🖼️",
        jpeg: "🖼️",
        gif: "🖼️",
        svg: "🎨",
        ico: "🖼️",
        webp: "🖼️",

        // Videos
        mp4: "🎥",
        avi: "🎥",
        mov: "🎥",
        mkv: "🎥",
        webm: "🎥",

        // Audio
        mp3: "🎵",
        wav: "🎵",
        flac: "🎵",
        m4a: "🎵",

        // Archives
        zip: "📦",
        rar: "📦",
        "7z": "📦",
        tar: "📦",
        gz: "📦",

        // Programming - Python
        py: "🐍",
        pyc: "🐍",
        pyw: "🐍",

        // Programming - JavaScript/Web
        js: "💛",
        jsx: "⚛️",
        ts: "💙",
        tsx: "⚛️",
        json: "📋",

        // Programming - Web
        html: "🌐",
        htm: "🌐",
        css: "🎨",
        scss: "🎨",
        sass: "🎨",

        // Programming - C/C++
        c: "©️",
        cpp: "©️",
        cc: "©️",
        cxx: "©️",
        h: "©️",
        hpp: "©️",

        // Programming - Java
        java: "☕",
        class: "☕",
        jar: "☕",

        // Programming - Other
        go: "🐹",
        rs: "🦀",
        php: "🐘",
        rb: "💎",
        swift: "🐦",
        kt: "🟣",
        cs: "🔷",

        // Shell/Scripts
        sh: "🔧",
        bash: "🔧",
        bat: "⚙️",
        ps1: "⚙️",

        // Config
        yml: "⚙️",
        yaml: "⚙️",
        toml: "⚙️",
        ini: "⚙️",
        conf: "⚙️",

        // Database
        db: "🗄️",
        sqlite: "🗄️",
        sql: "🗄️",

        // Other
        exe: "⚡",
        dll: "📚",
        iso: "💿",
    };

    return iconMap[ext] || "📄";
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
