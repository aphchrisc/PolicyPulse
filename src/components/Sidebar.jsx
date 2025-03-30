import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useBookmarks } from "../context/BookmarkContext";

function Sidebar({ collapsed = false, onCollapse, hasAlerts = false }) {
  const location = useLocation();
  const { bookmarkedBills } = useBookmarks();

  // Check if the current path matches the link
  const isActive = (path) => {
    return location.pathname === path;
  };

  // Navigation items with icons
  const navItems = [
    {
      label: "Dashboard",
      path: "/dashboard",
      icon: (
        <svg
          className="w-5 h-5"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
          />
        </svg>
      ),
    },
    {
      label: "Alerts",
      path: "/alerts",
      icon: (
        <svg
          className="w-5 h-5"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      ),
      badge: null, // This could be dynamically set based on alerts count
    },
    {
      label: "Bills",
      path: "/bills",
      icon: (
        <svg
          className="w-5 h-5"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      ),
    },
    {
      label: "Bookmarks",
      path: "/bookmarks",
      icon: (
        <svg
          className="w-5 h-5"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
          />
        </svg>
      ),
      badge: bookmarkedBills.length > 0 ? bookmarkedBills.length : null,
    },
    {
      label: "Export",
      path: "/export",
      icon: (
        <svg
          className="w-5 h-5"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
      ),
    },
  ];

  // Utility navigation items
  const utilityNavItems = [
    {
      label: "Preferences",
      path: "/preferences",
      icon: (
        <svg
          className="w-5 h-5"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      ),
    },
    {
      label: "System Status",
      path: "/status",
      icon: (
        <svg
          className="w-5 h-5"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
    },
  ];

  // Calculate the top position based on whether alerts are present
  const sidebarTopClass = hasAlerts ? "top-[50px]" : "top-0";

  return (
    <aside
      className={`
        fixed left-0 ${sidebarTopClass} h-full bg-gray-800 text-white 
        transition-all duration-300 ease-in-out z-40
        ${collapsed ? "w-16" : "w-64"}
        flex flex-col
      `}
    >
      {/* Logo and toggle */}
      <div
        className={`flex items-center justify-between h-16 px-4 border-b border-blue-800`}
      >
        <div className="flex items-center">
          <img src="/logo.svg" alt="PolicyPulse" className="h-8 w-8" />
          {!collapsed && (
            <span className="ml-3 font-semibold text-lg text-white">
              PolicyPulse
            </span>
          )}
        </div>
        <button
          onClick={() => onCollapse(!collapsed)}
          className="p-1 rounded-full hover:bg-blue-800 focus:outline-none"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <svg
            className="w-5 h-5 text-blue-100"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            {collapsed ? (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 5l7 7-7 7M5 5l7 7-7 7"
              />
            ) : (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
              />
            )}
          </svg>
        </button>
      </div>

      {/* Navigation */}
      <nav className="h-full pt-5 pb-16 overflow-y-auto scrollbar-thin scrollbar-thumb-blue-800 scrollbar-track-transparent">
        {/* Main Navigation */}
        <div className={`${!collapsed && "px-4"}`}>
          {!collapsed && (
            <h2 className="text-xs uppercase tracking-wider text-blue-300 font-semibold mb-2">
              Navigation
            </h2>
          )}
          <ul>
            {navItems.map((item) => (
              <li key={item.path} className="mb-1">
                <Link
                  to={item.path}
                  className={`flex items-center py-2 px-4 rounded-lg transition-colors ${
                    isActive(item.path)
                      ? "bg-blue-800 text-white"
                      : "text-blue-100 hover:bg-blue-800/50"
                  } relative`}
                >
                  <span className="mr-3 flex-shrink-0">{item.icon}</span>
                  {!collapsed && <span>{item.label}</span>}
                  {!collapsed && item.badge && (
                    <span className="ml-auto bg-blue-600 text-white text-xs font-semibold px-2 py-0.5 rounded-full">
                      {item.badge}
                    </span>
                  )}
                  {collapsed && item.badge && (
                    <span className="absolute top-0 right-0 bg-blue-600 text-white text-xs font-semibold w-4 h-4 flex items-center justify-center rounded-full">
                      {item.badge}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Utility Navigation */}
        <div className={`${!collapsed && "px-4"} mt-8`}>
          {!collapsed && (
            <h2 className="text-xs uppercase tracking-wider text-blue-300 font-semibold mb-2">
              Utilities
            </h2>
          )}
          <ul>
            {utilityNavItems.map((item) => (
              <li key={item.path} className="mb-1">
                <Link
                  to={item.path}
                  className={`flex items-center py-2 px-4 rounded-lg transition-colors ${
                    isActive(item.path)
                      ? "bg-blue-800 text-white"
                      : "text-blue-100 hover:bg-blue-800/50"
                  }`}
                >
                  <span className="mr-3 flex-shrink-0">{item.icon}</span>
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </nav>

      {/* API Status Indicator */}
      {!collapsed && (
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-blue-800">
          <div className="flex items-center text-xs font-medium">
            <span className="flex items-center">
              <span className="h-2 w-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
              <span className="text-blue-200">API: Operational</span>
            </span>
          </div>
        </div>
      )}
    </aside>
  );
}

export default Sidebar;
