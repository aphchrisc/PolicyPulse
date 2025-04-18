// Browser debugging script
// To use: Open browser console and run: fetch('/browser-debug.js').then(r => r.text()).then(eval)

(function () {
  console.log("Debug script running...");

  // Check React elements
  const root = document.getElementById("root");
  console.log("Root element exists:", !!root);
  console.log("Root children count:", root?.childNodes?.length || 0);
  console.log("Root innerHTML:", root?.innerHTML || "empty");

  // Log any errors
  const errors = [];
  const originalError = console.error;
  console.error = function (...args) {
    errors.push(args);
    originalError.apply(console, args);
  };

  // Check React Router imports
  try {
    console.log("Checking imported modules...");
    const imports = Object.keys(window).filter(
      (key) =>
        key.includes("React") ||
        key.includes("router") ||
        key.includes("Route") ||
        key.includes("Link")
    );
    console.log("Potentially relevant global imports:", imports);
  } catch (e) {
    console.error("Error checking imports:", e);
  }

  // Print out all errors collected
  setTimeout(() => {
    console.log("------------ Collected Errors ------------");
    console.log(errors.length ? errors : "No errors collected");
    console.error = originalError;
  }, 1000);

  return "Debug script completed.";
})();
