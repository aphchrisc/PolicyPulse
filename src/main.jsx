import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import "./styles/screenReaderOptimizations.css";
import logger from "./utils/logger";

// Add error boundary to catch and log rendering errors
window.addEventListener("error", (event) => {
  logger.error("Global error caught", event.error);
});

// Add unhandled promise rejection handler
window.addEventListener("unhandledrejection", (event) => {
  logger.error("Unhandled promise rejection", event.reason);
});

// Track React errors
const originalError = console.error;
console.error = function () {
  originalError.apply(console, arguments);
  if (
    arguments[0]?.includes?.("React Router") ||
    arguments[0]?.includes?.("RouterProvider") ||
    (typeof arguments[0] === "object" &&
      arguments[0]?.message?.includes?.("React"))
  ) {
    logger.error("React Router Error Details", {
      args: Array.from(arguments),
    });
  }
};

// Log application start for debugging
logger.info("Application initializing...");

try {
  ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
  logger.info("React has rendered the application");
} catch (error) {
  logger.error("Failed to render application", error);
  // Add fallback UI for catastrophic errors
  document.getElementById("root").innerHTML = `
    <div style="padding: 20px; background: #ffebee; border: 1px solid #f44336; border-radius: 4px; margin: 20px;">
      <h2 style="color: #d32f2f;">Application Error</h2>
      <p>There was a problem loading the application. Please try refreshing the page.</p>
      <pre style="background: #f5f5f5; padding: 10px; overflow: auto;">${
        error?.message || "Unknown error"
      }</pre>
    </div>
  `;
}
