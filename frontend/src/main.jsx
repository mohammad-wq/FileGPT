import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";

// Import bundled Highlight.js stylesheet and core for Tauri desktop
import 'highlight.js/styles/github-dark.min.css';
import hljs from 'highlight.js/lib/common';

// Expose hljs globally so components (or third-party libs) can access it if needed
window.hljs = hljs;

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
