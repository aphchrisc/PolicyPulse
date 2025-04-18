import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env variables
  const env = loadEnv(mode, process.cwd(), "");

  // Get API URL from environment variables
  // This is the URL provided by run.py
  const apiUrl = env.VITE_API_URL || "";
  console.log(`Environment VITE_API_URL: ${apiUrl}`);

  // Get backend port from environment variables
  const backendPort = env.VITE_BACKEND_PORT || "";
  console.log(`Environment VITE_BACKEND_PORT: ${backendPort}`);

  // Determine the actual target URL for the proxy
  let proxyTarget;

  if (apiUrl) {
    // If we have an API URL, use it directly
    proxyTarget = apiUrl;
  } else if (backendPort) {
    // If we have a backend port but no API URL, construct one
    proxyTarget = `http://127.0.0.1:${backendPort}`;
  } else {
    // Default fallback
    proxyTarget = "http://127.0.0.1:8000";
  }

  console.log(`Using proxy target: ${proxyTarget}`);

  return {
    plugins: [react()],
    server: {
      // Listen on all interfaces for local development
      host: "0.0.0.0",
      // Use PORT env var or fallback to 5173
      port: parseInt(env.PORT || "5173"),
      // Don't exit if port is already in use
      strictPort: false,
      // API proxy configuration
      proxy: {
        "/api": {
          // Use the determined proxy target
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
          // Strip /api prefix but keep trailing slash
          rewrite: (path) => {
            return path.replace(/^\/api/, "");
          },
          configure: (proxy, _options) => {
            proxy.on("error", (err, _req, _res) => {
              console.log("proxy error", err);
            });
            proxy.on("proxyReq", (proxyReq, req, _res) => {
              console.log(
                "Sending Request to the Target:",
                req.method,
                req.url
              );
            });
            proxy.on("proxyRes", (proxyRes, req, _res) => {
              console.log(
                "Received Response from the Target:",
                proxyRes.statusCode,
                req.url
              );
            });
          },
        },
        // Removed the redundant /api/bills proxy rule as /api handles all cases now.
      },
      // Enable CORS
      cors: true,
    },
    // Dependencies optimization configuration
    // IMPORTANT: This helps with module resolution in Replit's environment
    optimizeDeps: {
      // Pre-bundle these dependencies for faster development server start
      include: ["react", "react-dom", "react-router-dom"],
      // Force dependency pre-bundling even after server restart
      force: false,
    },
    // Production build configuration
    build: {
      // Generate source maps for debugging
      sourcemap: true,
    },
  };
});
