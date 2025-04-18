// Debug helper for React application
console.log("Debug helper loaded");

// Track errors during React rendering
window.addEventListener("error", (event) => {
  console.error("Global error caught:", event.error);

  // Create error display element if not exists
  if (!document.getElementById("error-display")) {
    const errorDisplay = document.createElement("div");
    errorDisplay.id = "error-display";
    errorDisplay.style.position = "fixed";
    errorDisplay.style.top = "0";
    errorDisplay.style.left = "0";
    errorDisplay.style.right = "0";
    errorDisplay.style.backgroundColor = "#ffebee";
    errorDisplay.style.color = "#d32f2f";
    errorDisplay.style.padding = "1rem";
    errorDisplay.style.zIndex = "9999";
    errorDisplay.style.fontFamily = "monospace";
    errorDisplay.style.fontSize = "14px";
    errorDisplay.style.overflow = "auto";
    errorDisplay.style.maxHeight = "50vh";
    document.body.appendChild(errorDisplay);
  }

  // Add error to display
  const errorDisplay = document.getElementById("error-display");
  const errorItem = document.createElement("div");
  errorItem.style.marginBottom = "0.5rem";
  errorItem.style.borderBottom = "1px solid #f44336";
  errorItem.style.paddingBottom = "0.5rem";

  // Format the error message
  let errorMessage = `Error: ${event.error.message || "Unknown error"}`;
  if (event.error.stack) {
    errorMessage += `<br/><pre>${event.error.stack}</pre>`;
  }

  errorItem.innerHTML = errorMessage;
  errorDisplay.appendChild(errorItem);
});

// Monitor React initialization
const originalCreateRoot = window.ReactDOM?.createRoot;
if (originalCreateRoot) {
  window.ReactDOM.createRoot = function (container, options) {
    console.log("React attempting to render in:", container);
    try {
      return originalCreateRoot.call(this, container, options);
    } catch (err) {
      console.error("Error during React.createRoot:", err);
      return originalCreateRoot.call(this, container, options);
    }
  };
}

// Check if root element exists
window.addEventListener("DOMContentLoaded", () => {
  console.log("DOM loaded, checking root element...");
  const rootElement = document.getElementById("root");
  console.log("Root element exists:", !!rootElement);

  // Check what gets rendered to the root after a delay
  setTimeout(() => {
    const rootElement = document.getElementById("root");
    console.log(
      "Root element children count after 2s:",
      rootElement?.childNodes?.length || 0
    );
    console.log("Root element content:", rootElement?.innerHTML || "empty");
  }, 2000);
});
