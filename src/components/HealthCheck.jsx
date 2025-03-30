import React, { useState, useEffect } from "react";
import axios from "axios";
import logger from "../utils/logger";

const HealthCheck = () => {
  const [status, setStatus] = useState("checking");
  const [error, setError] = useState(null);
  const [apiUrl, setApiUrl] = useState("");
  const [lastChecked, setLastChecked] = useState(null);
  const [message, setMessage] = useState("Checking API health...");

  useEffect(() => {
    // Get the API URL from environment or config for display purposes
    const displayUrl = import.meta.env.VITE_API_URL || "/api";
    setApiUrl(displayUrl);

    const checkHealth = async () => {
      try {
        logger.info("Checking API health...");
        const response = await axios.get("/api/health");

        if (response.status === 200 && response.data) {
          logger.info("API health check successful", { data: response.data });
          setStatus("online");
          setError(null);
          setLastChecked(new Date());
          setMessage(response.data.message || "API is online");
        } else {
          logger.warning("Unexpected API health response", { response });
          setStatus("unknown");
          setError("Received unexpected response from API");
          setMessage("Received unexpected response from API");
        }
      } catch (err) {
        logger.error("Health check error", { error: err });
        setStatus("offline");
        setError("API is offline or unreachable");
        setMessage("API is offline or unreachable");
      }
    };

    // Initial check
    checkHealth();

    // Set up periodic health checks with a longer interval to reduce console spam
    const intervalId = setInterval(checkHealth, 60000); // Check every minute

    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="health-check p-4 bg-white rounded-lg shadow mb-6">
      <h2 className="text-xl font-semibold mb-2">API Connection Status</h2>
      <div className="status-indicator flex items-center mb-3">
        <div
          className={`h-4 w-4 rounded-full mr-2 ${
            status === "online"
              ? "bg-green-500"
              : status === "checking"
              ? "bg-yellow-400"
              : "bg-red-500"
          }`}
        ></div>
        <span className="font-medium">
          {status === "online"
            ? "Connected"
            : status === "checking"
            ? "Checking Connection..."
            : "Connection Error"}
        </span>
        {lastChecked && status === "online" && (
          <span className="text-xs text-gray-500 ml-2">
            Last checked: {lastChecked.toLocaleTimeString()}
          </span>
        )}
      </div>

      {status === "online" ? (
        <p className="text-green-600">{message}</p>
      ) : (
        <div className="error-details mt-2">
          <p className="text-red-600">{message}</p>
          {error && (
            <div className="p-2 bg-red-50 border border-red-200 rounded mt-1">
              <p className="text-red-500 text-sm font-mono overflow-auto">
                {error}
              </p>
            </div>
          )}
          <p className="text-sm mt-2">
            Please ensure the backend server is running and accessible.
          </p>
        </div>
      )}
    </div>
  );
};

export default HealthCheck;
