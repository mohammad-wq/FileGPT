//! FileGPT Linux Real-Time File Monitor
//!
//! Uses the `notify` crate (inotify on Linux) to watch directories for changes
//! and sends events to the Python backend via HTTP POST for automatic indexing.

use std::collections::HashSet;
use std::env;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;

use chrono::Local;
use clap::Parser;
use notify::{Config, Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use reqwest::Client;
use serde::Serialize;
use tokio::sync::mpsc;

#[derive(Parser, Debug)]
#[command(name = "linux_monitor")]
#[command(about = "Real-time file system monitor for FileGPT")]
struct Args {
    /// Directories to watch (can specify multiple). If omitted, defaults to environment variable FILEGPT_WATCH_PATHS or root "/".
    #[arg(short, long, required = false, default_values_t = Vec::<String>::new())]
    watch: Vec<String>,

    /// Backend URL to POST events to
    #[arg(short, long, default_value = "http://127.0.0.1:8000")]
    backend_url: String,

    /// Enable verbose output
    #[arg(short, long, default_value_t = false)]
    verbose: bool,
}

// ============================================================================
// Event Types
// ============================================================================

#[derive(Debug, Clone, Serialize)]
struct FileEvent {
    /// Event type: "create", "modify", "delete", "rename"
    event_type: String,
    /// Absolute path to the file
    path: String,
    /// File extension (e.g. ".py", ".pdf")
    extension: String,
    /// File type category (e.g. "Code", "Document")
    file_type: String,
    /// ISO 8601 timestamp
    timestamp: String,
}

// ============================================================================
// File Classification
// ============================================================================

fn get_file_extension(path: &Path) -> String {
    path.extension()
        .and_then(|ext| ext.to_str())
        .map(|ext| format!(".{}", ext))
        .unwrap_or_else(|| "[no extension]".to_string())
}

fn get_file_type(path: &Path) -> &'static str {
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");

    match ext.to_lowercase().as_str() {
        // Documents
        "txt" | "doc" | "docx" | "pdf" | "rtf" | "odt" | "md" => "Document",
        "xls" | "xlsx" | "csv" | "ods" => "Spreadsheet",
        "ppt" | "pptx" | "odp" => "Presentation",

        // Images
        "jpg" | "jpeg" | "png" | "gif" | "bmp" | "svg" | "webp" | "ico" => "Image",

        // Videos
        "mp4" | "avi" | "mkv" | "mov" | "wmv" | "flv" | "webm" => "Video",

        // Audio
        "mp3" | "wav" | "flac" | "aac" | "ogg" | "wma" | "m4a" => "Audio",

        // Archives
        "zip" | "rar" | "7z" | "tar" | "gz" | "bz2" | "xz" => "Archive",

        // Code
        "rs" | "py" | "js" | "ts" | "java" | "cpp" | "c" | "h" | "cs" | "go" | "rb" => "Code",
        "html" | "css" | "json" | "xml" | "yaml" | "yml" | "toml" => "Markup",

        // Executables
        "sh" | "bash" | "bin" | "AppImage" => "Executable",

        // System
        "ini" | "cfg" | "conf" | "log" => "Config",
        "db" | "sqlite" | "mdb" => "Database",

        "" => "No Extension",
        _ => "Other",
    }
}

// ============================================================================
// Filtering
// ============================================================================

/// Directories that should be completely ignored
static IGNORE_DIRS: &[&str] = &[
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "dist",
    "build",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    ".vs",
    "bin",
    "obj",
    "target",
    ".Trash",
    ".local",
    ".config",
    "snap",
    // System virtual/privileged paths – ignore to avoid permission errors
    "proc",
    "sys",
    "dev",
    "run",
    "tmp",
    "root",
    "boot",
    "lost+found",
    "var",
];

/// Individual files to ignore
static IGNORE_FILES: &[&str] = &[".DS_Store", "Thumbs.db", ".gitignore", ".gitattributes"];

fn is_ignored_path(path: &Path) -> bool {
    // Check if any path component is in the ignore list
    for component in path.components() {
        let comp = component.as_os_str().to_string_lossy();
        if IGNORE_DIRS.contains(&comp.as_ref()) {
            return true;
        }
        // Skip hidden directories (starting with '.')
        if comp.starts_with('.') && comp.len() > 1 {
            return true;
        }
    }

    // Check filename
    if let Some(filename) = path.file_name() {
        let name = filename.to_string_lossy();

        // Ignored files
        if IGNORE_FILES.contains(&name.as_ref()) {
            return true;
        }

        // Temporary files
        let name_lower = name.to_lowercase();
        if name_lower.starts_with('~')
            || name_lower.ends_with(".tmp")
            || name_lower.ends_with(".temp")
            || name_lower.ends_with(".swp")
            || name_lower.ends_with(".swo")
            || name_lower.ends_with(".lock")
            || name_lower.ends_with(".lck")
            || name_lower.contains("~$")
            || name_lower.ends_with(".part")
            || name_lower.ends_with(".crdownload")
        {
            return true;
        }
    }

    // Skip non-regular files (symlinks, sockets, etc.) if path exists
    if path.exists() && !path.is_file() && !path.is_dir() {
        return true;
    }

    false
}

/// Supported file extensions for indexing (matches Python backend's fileParser)
fn is_supported_extension(path: &Path) -> bool {
    let supported: HashSet<&str> = [
        "txt", "md", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "csv", "json", "xml",
        "yaml", "yml", "toml", "html", "htm", "py", "rs", "js", "ts", "java", "cpp", "c", "h", "cs",
        "go", "rb", "php", "sh", "bash", "css", "sql", "r", "m", "swift", "kt", "scala", "pl",
        "lua", "hs",
    ]
    .iter()
    .copied()
    .collect();

    path.extension()
        .and_then(|ext| ext.to_str())
        .map(|ext| supported.contains(ext.to_lowercase().as_str()))
        .unwrap_or(false)
}

// ============================================================================
// Backend Communication
// ============================================================================

async fn send_event_to_backend(client: &Client, backend_url: &str, event: &FileEvent) {
    let url = format!("{}/monitor/event", backend_url);

    match client
        .post(&url)
        .json(event)
        .timeout(Duration::from_secs(5))
        .send()
        .await
    {
        Ok(resp) => {
            if !resp.status().is_success() {
                eprintln!(
                    "  ⚠ Backend returned {}: {}",
                    resp.status(),
                    resp.text().await.unwrap_or_default()
                );
            }
        }
        Err(e) => {
            eprintln!("  ⚠ Failed to reach backend: {}", e);
        }
    }
}

// ============================================================================
// Event Processing
// ============================================================================

fn classify_event(kind: &EventKind) -> Option<&'static str> {
    match kind {
        EventKind::Create(_) => Some("create"),
        EventKind::Modify(_) => Some("modify"),
        EventKind::Remove(_) => Some("delete"),
        _ => None, // Ignore Access, Other events
    }
}

fn format_timestamp() -> String {
    Local::now().format("%Y-%m-%dT%H:%M:%S%.3f%:z").to_string()
}

// ============================================================================
// Gracious Watching
// ============================================================================

/// Adds a recursive watch but gracefully skips directories with permission errors.
fn watch_recursive_gracious(watcher: &mut RecommendedWatcher, path: &Path, verbose: bool) {
    if is_ignored_path(path) {
        return;
    }

    // Try to watch this directory non-recursively
    match watcher.watch(path, RecursiveMode::NonRecursive) {
        Ok(_) => {
            if verbose {
                println!("  ✓ Watching: {}", path.display());
            }
        }
        Err(e) => {
            // If we can't watch this directory, skip it and its children
            if verbose {
                eprintln!("  ! Skipping {}: {}", path.display(), e);
            }
            return;
        }
    }

    // If it's a directory, try to recurse into children
    if path.is_dir() {
        if let Ok(entries) = std::fs::read_dir(path) {
            for entry in entries.flatten() {
                let child_path = entry.path();
                if child_path.is_dir() {
                    watch_recursive_gracious(watcher, &child_path, verbose);
                }
            }
        }
    }
}

// ============================================================================
// Main
// ============================================================================

#[tokio::main]
async fn main() {
    let args = Args::parse();

    // Determine watch directories:
    // 1. Command-line args if provided
    // 2. Else, check FILEGPT_WATCH_PATHS env var (colon-separated list)
    // 3. Fallback to root '/' for full system monitoring
    let watch_dirs: Vec<String> = if !args.watch.is_empty() {
        args.watch.clone()
    } else if let Ok(env_paths) = env::var("FILEGPT_WATCH_PATHS") {
        if !env_paths.trim().is_empty() {
            env_paths.split(':').map(|s| s.to_string()).collect()
        } else {
            vec!["/".to_string()]
        }
    } else {
        vec!["/".to_string()]
    };

    // Validate top-level watch paths
    let mut watch_paths: Vec<PathBuf> = Vec::new();
    for path_str in &watch_dirs {
        let path = PathBuf::from(path_str);
        if path.exists() && path.is_dir() {
            watch_paths.push(path);
        } else {
            eprintln!("  ✗ skipping (invalid path): {}", path_str);
        }
    }

    if watch_paths.is_empty() {
        eprintln!("\nError: No valid directories to watch. Exiting.");
        std::process::exit(1);
    }

    println!("\n╔══════════════════════════════════════════════════════════╗");
    println!("║     FileGPT Linux Real-Time Monitor (Gracious)         ║");
    println!("╚══════════════════════════════════════════════════════════╝\n");

    println!("  Backend: {}", args.backend_url);
    println!("  Verbose: {}", args.verbose);
    println!();
    println!("⏳ Initializing watches (this may take a moment for system-wide)...");

    // Create async channel for events
    let (tx, mut rx) = mpsc::channel::<Event>(1024);

    // Create watcher
    let tx_clone = tx.clone();
    let mut watcher = RecommendedWatcher::new(
        move |res: Result<Event, notify::Error>| {
            if let Ok(event) = res {
                let _ = tx_clone.blocking_send(event);
            }
        },
        Config::default().with_poll_interval(Duration::from_secs(1)),
    )
    .expect("Failed to create file watcher");

    // Add watch paths graciously
    for path in &watch_paths {
        watch_recursive_gracious(&mut watcher, path, args.verbose);
    }

    println!("✓ Setup complete. Waiting for changes...\n");

    // HTTP client for backend communication
    let client = Client::new();
    let backend_url = Arc::new(args.backend_url.clone());
    let verbose = args.verbose;

    // Process events
    while let Some(event) = rx.recv().await {
        let event_type = match classify_event(&event.kind) {
            Some(t) => t,
            None => continue, // Skip uninteresting events
        };

        for path in &event.paths {
            // Apply filtering
            if is_ignored_path(path) {
                if verbose {
                    println!("  [skip] Ignored: {}", path.display());
                }
                continue;
            }

            // For create/modify, only process supported file types
            if event_type != "delete" && !is_supported_extension(path) {
                if verbose {
                    println!("  [skip] Unsupported extension: {}", path.display());
                }
                continue;
            }

            let file_ext = get_file_extension(path);
            let file_type = get_file_type(path);
            let timestamp = format_timestamp();

            let file_event = FileEvent {
                event_type: event_type.to_string(),
                path: path.to_string_lossy().to_string(),
                extension: file_ext.clone(),
                file_type: file_type.to_string(),
                timestamp: timestamp.clone(),
            };

            // Color-coded console output
            let icon = match event_type {
                "create" => "🟢 CREATE",
                "modify" => "🟡 MODIFY",
                "delete" => "🔴 DELETE",
                _ => "⚪ CHANGE",
            };

            println!(
                "[{}] {} | {} | Type: {} | Ext: {}",
                &timestamp[11..23], // HH:MM:SS.mmm
                icon,
                path.display(),
                file_type,
                file_ext,
            );

            // Send to backend asynchronously
            let client = client.clone();
            let backend_url = backend_url.clone();
            let event_clone = file_event.clone();
            tokio::spawn(async move {
                send_event_to_backend(&client, &backend_url, &event_clone).await;
            });
        }
    }
}
