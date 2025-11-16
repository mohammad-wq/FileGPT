// In frontend/src-tauri/src/main.rs

// This line prevents a console window from popping up in release builds
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// --- THIS IS THE FIX ---
// We only need the ShellExt trait to get the .shell() method
// The 'unused import' warning is gone because we removed 'tauri::Manager'
use tauri_plugin_shell::ShellExt;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init()) // <-- Initialize the shell plugin
        .setup(|app| {
            // --- THIS IS THE NEW CODE THAT RUNS YOUR BACKEND ---

            // Get a handle to the app's shell
            let shell = app.shell();

            // "filegpt_backend" must match the name in tauri.conf.json
            let sidecar_command = shell.sidecar("filegpt_backend")
                .expect("failed to create `filegpt_backend` command");

            // Spawn the sidecar process
            tauri::async_runtime::spawn(async move {
                
                let output = sidecar_command
                    .spawn()
                    .expect("Failed to spawn sidecar");

                // --- THIS IS THE FIX ---
                // The 'output' is a tuple (receiver, child)
                // We get the pid from the child, which is the second item (index 1)
                println!("[Backend] PID: {}", output.1.pid());
            });
            // --- END OF NEW CODE ---
            
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}