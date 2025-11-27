// Minimal test - just render Hello World
console.log("main.jsx is loading...");

const root = document.getElementById("root");
if (root) {
    root.innerHTML = "\u003ch1 style='color: white; padding: 20px;'\u003eHello from FileGPT!\u003c/h1\u003e";
    console.log("Successfully wrote to #root");
} else {
    console.error("#root element not found!");
}
