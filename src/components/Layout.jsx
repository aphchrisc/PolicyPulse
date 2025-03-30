import React, { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import Header from "./Header";
import Sidebar from "./Sidebar";
import Footer from "./Footer";
import { useAlerts } from "../context/AlertContext";

/**
 * Main layout component that provides the application structure
 *
 * @param {Object} props - Component props
 * @param {Object} props.apiStatus - Current API status information
 * @param {React.ReactNode} props.children - Child components to render in the main content area
 */
function Layout({ apiStatus, children }) {
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { alerts, loading } = useAlerts();
  const [hasAlerts, setHasAlerts] = useState(false);

  // Check if there are active alerts
  useEffect(() => {
    if (!loading && alerts && alerts.length > 0) {
      setHasAlerts(true);
    } else {
      setHasAlerts(false);
    }
  }, [alerts, loading]);

  // Check if we're on the landing page
  const isLandingPage = location.pathname === "/";

  // Calculate content margin based on sidebar state
  const contentMargin = sidebarCollapsed ? "ml-16" : "ml-64";

  // Calculate top padding based on presence of alert ticker
  // The alert ticker is 50px tall, so add that to the padding when alerts are present
  const topPadding = isLandingPage
    ? hasAlerts
      ? "pt-[50px]"
      : "pt-0"
    : hasAlerts
    ? "pt-[124px]"
    : "pt-[74px]";

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-900 dark:text-white transition-colors duration-200">
      {/* Sidebar component */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onCollapse={setSidebarCollapsed}
        hasAlerts={hasAlerts}
      />

      {/* Main content area */}
      <div
        className={`flex-1 flex flex-col transition-all duration-300 ${contentMargin}`}
      >
        {/* Header component - only shown when not on landing page */}
        {!isLandingPage && (
          <Header
            apiStatus={apiStatus}
            sidebarCollapsed={sidebarCollapsed}
            hasAlerts={hasAlerts}
          />
        )}

        {/* Main content */}
        <main
          id="main-content"
          className={`
            flex-1 p-6 
            ${topPadding}
            bg-gray-50 dark:bg-gray-900
          `}
        >
          {children}
        </main>

        {/* Footer component */}
        <Footer />
      </div>
    </div>
  );
}

export default Layout;
