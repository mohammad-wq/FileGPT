/**
 * Simple toast notification system
 * Used for showing success/error/info messages
 */

let toastContainer = null;

// Initialize toast container
const initToastContainer = () => {
    if (!toastContainer) {
        toastContainer = document.createElement("div");
        toastContainer.id = "toast-container";
        toastContainer.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 10000;
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-width: 400px;
    `;
        document.body.appendChild(toastContainer);
    }
    return toastContainer;
};

// Create toast element
const createToast = (message, type = "info") => {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const icons = {
        success: "✅",
        error: "❌",
        info: "ℹ️",
        warning: "⚠️",
    };

    const colors = {
        success: "#10b981",
        error: "#ef4444",
        info: "#6366f1",
        warning: "#f59e0b",
    };

    toast.innerHTML = `
    <div style="display: flex; align-items: start; gap: 12px;">
      <span style="font-size: 20px; flex-shrink: 0;">${icons[type] || icons.info}</span>
      <div style="flex: 1;">
        <div style="font-weight: 600; margin-bottom: 4px;">${type.charAt(0).toUpperCase() + type.slice(1)}</div>
        <div style="font-size: 14px; opacity: 0.9;">${message}</div>
      </div>
    </div>
  `;

    toast.style.cssText = `
    background: rgba(26, 26, 46, 0.95);
    border: 1px solid ${colors[type] || colors.info};
    border-radius: 12px;
    padding: 16px;
    color: white;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    animation: slideIn 0.3s ease-out;
    backdrop-filter: blur(10px);
  `;

    return toast;
};

// Add keyframe animation
const addToastStyles = () => {
    if (!document.getElementById("toast-styles")) {
        const style = document.createElement("style");
        style.id = "toast-styles";
        style.textContent = `
      @keyframes slideIn {
        from {
          transform: translateX(400px);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
      @keyframes slideOut {
        from {
          transform: translateX(0);
          opacity: 1;
        }
        to {
          transform: translateX(400px);
          opacity: 0;
        }
      }
    `;
        document.head.appendChild(style);
    }
};

/**
 * Show a toast notification
 */
export const showToast = (message, type = "info", duration = 4000) => {
    addToastStyles();
    const container = initToastContainer();
    const toast = createToast(message, type);

    container.appendChild(toast);

    // Auto remove
    setTimeout(() => {
        toast.style.animation = "slideOut 0.3s ease-out";
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, duration);
};

// Convenience methods
export const toast = {
    success: (message, duration) => showToast(message, "success", duration),
    error: (message, duration) => showToast(message, "error", duration),
    info: (message, duration) => showToast(message, "info", duration),
    warning: (message, duration) => showToast(message, "warning", duration),
};

export default toast;
