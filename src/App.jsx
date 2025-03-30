import React, { useState, useEffect } from "react";
import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
  Outlet,
} from "react-router-dom";
import "./index.css";
import { healthCheck } from "./services/api";
import logger from "./utils/logger"; // Import the logger utility
// Import all route components from pages directory
import LandingPage from "./pages/LandingPage";
import StatusPage from "./pages/StatusPage";
import Dashboard from "./pages/Dashboard";
import BillsPage from "./pages/BillsPage";
import BillDetail from "./pages/BillDetail";
import BookmarksPage from "./pages/BookmarksPage";
import AlertsPage from "./pages/AlertsPage";
import NotFound from "./pages/NotFound";
import UserPreferences from "./pages/UserPreferences";
import ExportDashboard from "./pages/ExportDashboard";
import Layout from "./components/Layout";
import AlertTicker from "./components/alerts/AlertTicker";
import { NotificationProvider } from "./context/NotificationContext";
import { UserPreferencesProvider } from "./context/UserPreferencesContext";
import { BookmarkProvider } from "./context/BookmarkContext";
import { AccessibilityProvider } from "./context/AccessibilityContext";
import { AlertProvider, useAlerts } from "./context/AlertContext";
import { initKeyboardNavigation } from "./utils/keyboardNavigation";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

// Root component that includes AlertTicker and provides outlet for nested routes
const Root = () => {
  const { alerts, loading } = useAlerts();

  return (
    <>
      {!loading && alerts && alerts.length > 0 && (
        <AlertTicker alerts={alerts} />
      )}
      <Outlet />
    </>
  );
};

function App() {
  const [apiStatus, setApiStatus] = useState({
    isChecking: true,
    isOnline: false,
    message: "Checking API status...",
  });

  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        // Directly call healthCheck and rely on it throwing an error on failure
        logger.info("Checking API health...");
        const response = await healthCheck(); // This will now throw if it fails
        logger.info("API health check successful", { data: response.data });
        setApiStatus({
          isChecking: false,
          isOnline: true,
          message: response.data?.message || "API is online",
        });
      } catch (error) {
        // Catch the error thrown by healthCheck
        logger.error("API health check failed", { error: error.message });
        setApiStatus({
          isChecking: false,
          isOnline: false,
          // Use the error message from healthCheck if available
          message: error.message || "API is offline or unreachable",
        });
      }
    };

    checkApiHealth();
    // Set interval to check every 30 seconds
    const interval = setInterval(checkApiHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Initialize keyboard navigation
  useEffect(() => {
    initKeyboardNavigation();
  }, []);

  // Create a reusable API offline component
  const ApiOfflineMessage = ({ title }) => (
    <div className="container mx-auto mt-8 p-6 bg-red-50 dark:bg-red-900/20 rounded-lg shadow-md border border-red-200 dark:border-red-800 transform transition-all duration-300 hover:shadow-lg">
      <h2 className="text-2xl font-bold mb-4 dark:text-white">
        {title} - API Offline
      </h2>
      <p className="text-red-600 dark:text-red-400 mb-4">
        The API is currently offline. Please try again later.
      </p>
      <div className="flex space-x-4 mt-6">
        <a
          href="/"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors duration-300"
        >
          Return Home
        </a>
        <a
          href="/status"
          className="px-4 py-2 bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors duration-300"
        >
          Check Status
        </a>
      </div>
    </div>
  );

  // Create router with all routes
  const router = createBrowserRouter([
    {
      element: <Root />,
      children: [
        {
          path: "/",
          element: <LandingPage apiStatus={apiStatus} />,
        },
        {
          path: "/status",
          element: (
            <Layout apiStatus={apiStatus}>
              <StatusPage apiStatus={apiStatus} />
            </Layout>
          ),
        },
        {
          path: "/dashboard",
          element: (
            // Always render Dashboard, let it handle its own API errors
            <Layout apiStatus={apiStatus}>
              <Dashboard />
            </Layout>
          ),
        },
        {
          path: "/alerts",
          element: (
            // Always render AlertsPage, let it handle its own API errors
            <Layout apiStatus={apiStatus}>
              <AlertsPage />
            </Layout>
          ),
        },
        {
          path: "/bills",
          element: (
            // Always render BillsPage, let it handle its own API errors
            <Layout apiStatus={apiStatus}>
              <BillsPage />
            </Layout>
          ),
        },
        {
          path: "/bills/:billId",
          element: (
            // Always render BillDetail, let it handle its own API errors
            <Layout apiStatus={apiStatus}>
              <BillDetail />
            </Layout>
          ),
        },
        {
          path: "/bookmarks",
          element: (
            // Bookmarks might not need strict API online check, depends on implementation
            <Layout apiStatus={apiStatus}>
              <BookmarksPage />
            </Layout>
          ),
        },
        {
          path: "/preferences",
          element: (
            // Preferences might not need strict API online check
            <Layout apiStatus={apiStatus}>
              <UserPreferences />
            </Layout>
          ),
        },
        {
          path: "/export",
          element: (
            // Always render ExportDashboard, let it handle its own API errors
            <Layout apiStatus={apiStatus}>
              <ExportDashboard />
            </Layout>
          ),
        },
        {
          path: "/404",
          element: <NotFound />,
        },
        {
          path: "*",
          element: <Navigate to="/404" replace />,
        },
      ],
    },
  ]);

  return (
    <UserPreferencesProvider>
      <NotificationProvider>
        <BookmarkProvider>
          <AccessibilityProvider>
            <AlertProvider>
              {/* Skip to content link for keyboard users */}
              <a
                href="#main-content"
                className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded-md"
              >
                Skip to content
              </a>

              <RouterProvider router={router} />

              {/* Toast notifications container */}
              <ToastContainer
                position="bottom-right"
                autoClose={5000}
                hideProgressBar={false}
                newestOnTop
                closeOnClick
                rtl={false}
                pauseOnFocusLoss
                draggable
                pauseOnHover
                theme="colored"
              />
            </AlertProvider>
          </AccessibilityProvider>
        </BookmarkProvider>
      </NotificationProvider>
    </UserPreferencesProvider>
  );
}

export default App;
