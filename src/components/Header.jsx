import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import ThemeToggle from "./ThemeToggle";
import AccessibilityButton from "./accessibility/AccessibilityButton";

const Header = ({ apiStatus, sidebarCollapsed, hasAlerts = false }) => {
  const [scrolled, setScrolled] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();

  // Add scroll effect
  useEffect(() => {
    const handleScroll = () => {
      const isScrolled = window.scrollY > 10;
      if (isScrolled !== scrolled) {
        setScrolled(isScrolled);
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, [scrolled]);

  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showNotifications || showUserMenu) {
        if (
          !event.target.closest(".notifications-menu") &&
          !event.target.closest(".notifications-button")
        ) {
          setShowNotifications(false);
        }
        if (
          !event.target.closest(".user-menu") &&
          !event.target.closest(".user-menu-button")
        ) {
          setShowUserMenu(false);
        }
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showNotifications, showUserMenu]);

  // Handle search form submission
  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/bills?search=${encodeURIComponent(searchQuery.trim())}`);
      setSearchQuery("");
    }
  };

  return (
    <header
      className={`sticky z-40 transition-all duration-300 ${
        scrolled
          ? "bg-white/95 dark:bg-gray-900/95 backdrop-blur-md shadow-md"
          : "bg-white dark:bg-gray-900"
      } ${sidebarCollapsed ? "left-16" : "left-64"} ${
        hasAlerts ? "top-[50px]" : "top-0"
      }`}
    >
      <div className="px-6 py-3 flex justify-between items-center">
        <div className="flex items-center">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
            Dashboard
          </h2>
        </div>

        <div className="flex items-center space-x-4">
          {/* Search bar */}
          <div className="relative hidden md:block">
            <form onSubmit={handleSearch}>
              <input
                type="text"
                placeholder="Search bills, topics, pages..."
                className="w-64 px-4 py-2 pl-10 rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Site-wide search"
              />
              <button
                type="submit"
                className="absolute left-3 top-2.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                aria-label="Search"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </button>
            </form>
          </div>

          {/* Notifications */}
          <div className="relative">
            <button
              className="notifications-button p-2 rounded-full text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none"
              onClick={() => setShowNotifications(!showNotifications)}
              aria-label="Notifications"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                />
              </svg>
              <span className="absolute top-0 right-0 h-4 w-4 bg-red-500 rounded-full text-xs text-white flex items-center justify-center">
                3
              </span>
            </button>

            {showNotifications && (
              <div className="notifications-menu absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg py-2 z-50 border border-gray-200 dark:border-gray-700">
                <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                  <h3 className="font-medium text-gray-800 dark:text-white">
                    Notifications
                  </h3>
                  <button className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
                    Mark all as read
                  </button>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {[
                    {
                      id: 1,
                      title: "New policy analysis complete",
                      time: "5 min ago",
                      read: false,
                    },
                    {
                      id: 2,
                      title: "API update scheduled",
                      time: "1 hour ago",
                      read: false,
                    },
                    {
                      id: 3,
                      title: "New bill added to watchlist",
                      time: "3 hours ago",
                      read: false,
                    },
                    {
                      id: 4,
                      title: "System maintenance completed",
                      time: "Yesterday",
                      read: true,
                    },
                  ].map((notification) => (
                    <div
                      key={notification.id}
                      className={`px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 ${
                        notification.read ? "opacity-60" : ""
                      }`}
                    >
                      <div className="flex items-start">
                        <div
                          className={`h-2 w-2 mt-1.5 rounded-full ${
                            notification.read ? "bg-gray-400" : "bg-blue-600"
                          } mr-2 flex-shrink-0`}
                        ></div>
                        <div>
                          <p className="text-sm font-medium text-gray-800 dark:text-white">
                            {notification.title}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {notification.time}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700">
                  <a
                    href="/notifications"
                    className="text-sm text-center block text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    View all notifications
                  </a>
                </div>
              </div>
            )}
          </div>

          {/* API Status Indicator */}
          <div className="flex items-center text-xs font-medium">
            {apiStatus.isChecking ? (
              <span className="flex items-center bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 px-2 py-1 rounded-full">
                <span className="h-2 w-2 rounded-full bg-yellow-400 mr-1.5 animate-pulse"></span>
                Checking...
              </span>
            ) : (
              <span
                className={`flex items-center px-2 py-1 rounded-full ${
                  apiStatus.isOnline
                    ? "bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200"
                    : "bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200"
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${
                    apiStatus.isOnline ? "bg-green-500" : "bg-red-500"
                  } mr-1.5 ${apiStatus.isOnline ? "animate-pulse" : ""}`}
                ></span>
                {apiStatus.isOnline ? "Operational" : "Offline"}
              </span>
            )}
          </div>

          {/* Theme toggle and accessibility */}
          <div className="flex items-center space-x-2">
            <AccessibilityButton />
            <ThemeToggle />
          </div>

          {/* User profile */}
          <div className="relative">
            <button
              className="user-menu-button flex items-center space-x-2 focus:outline-none"
              onClick={() => setShowUserMenu(!showUserMenu)}
            >
              <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white">
                <span className="text-sm font-medium">JP</span>
              </div>
            </button>

            {showUserMenu && (
              <div className="user-menu absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg py-2 z-50 border border-gray-200 dark:border-gray-700">
                <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                  <p className="text-sm font-medium text-gray-800 dark:text-white">
                    John Policymaker
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    john@example.com
                  </p>
                </div>
                <div className="py-1">
                  <Link
                    to="/preferences"
                    className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    Your Profile
                  </Link>
                  <Link
                    to="/preferences"
                    className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    Settings
                  </Link>
                  <Link
                    to="/status"
                    className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    Support
                  </Link>
                </div>
                <div className="py-1 border-t border-gray-200 dark:border-gray-700">
                  <Link
                    to="/"
                    className="block px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    Sign out
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
