import React, { useState } from "react";
import { useUserPreferences } from "../context/UserPreferencesContext";
import {
  FaCog,
  FaTrash,
  FaSave,
  FaUndo,
  FaBell,
  FaList,
  FaTh,
  FaUser,
  FaQuestionCircle,
} from "react-icons/fa";
import NotificationPreferences from "../components/notifications/NotificationPreferences";

const UserPreferences = () => {
  const { preferences, updatePreference, resetPreferences, removeSavedFilter } =
    useUserPreferences();

  // Add state to handle tabs
  const [activeTab, setActiveTab] = useState("profile");

  // Mock user data - would come from user context in a real app
  const userData = {
    name: "John Policymaker",
    email: "john@example.com",
    role: "Policy Analyst",
    organization: "Health Department",
    joinDate: "2023-01-15",
    profileImage: null,
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="flex items-center mb-6">
        <FaUser className="text-blue-600 text-2xl mr-3" />
        <h1 className="text-2xl font-bold text-gray-800 dark:text-white">
          User Settings
        </h1>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
        <nav className="flex -mb-px space-x-8">
          <button
            onClick={() => setActiveTab("profile")}
            className={`pb-4 px-1 ${
              activeTab === "profile"
                ? "border-b-2 border-blue-500 font-medium text-blue-600 dark:text-blue-400"
                : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            } transition-colors`}
          >
            <div className="flex items-center">
              <FaUser className="mr-2" />
              Profile
            </div>
          </button>
          <button
            onClick={() => setActiveTab("preferences")}
            className={`pb-4 px-1 ${
              activeTab === "preferences"
                ? "border-b-2 border-blue-500 font-medium text-blue-600 dark:text-blue-400"
                : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            } transition-colors`}
          >
            <div className="flex items-center">
              <FaCog className="mr-2" />
              Preferences
            </div>
          </button>
          <button
            onClick={() => setActiveTab("notifications")}
            className={`pb-4 px-1 ${
              activeTab === "notifications"
                ? "border-b-2 border-blue-500 font-medium text-blue-600 dark:text-blue-400"
                : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            } transition-colors`}
          >
            <div className="flex items-center">
              <FaBell className="mr-2" />
              Notifications
            </div>
          </button>
          <button
            onClick={() => setActiveTab("support")}
            className={`pb-4 px-1 ${
              activeTab === "support"
                ? "border-b-2 border-blue-500 font-medium text-blue-600 dark:text-blue-400"
                : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            } transition-colors`}
          >
            <div className="flex items-center">
              <FaQuestionCircle className="mr-2" />
              Support
            </div>
          </button>
        </nav>
      </div>

      {/* Profile Tab */}
      {activeTab === "profile" && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-6 text-gray-700 dark:text-gray-200 border-b pb-2">
            Profile Information
          </h2>

          <div className="flex flex-col md:flex-row gap-8">
            <div className="md:w-1/3 flex flex-col items-center">
              <div className="w-32 h-32 bg-gray-300 dark:bg-gray-700 rounded-full mb-4 flex items-center justify-center text-gray-600 dark:text-gray-400">
                {userData.profileImage ? (
                  <img
                    src={userData.profileImage}
                    alt="Profile"
                    className="w-full h-full rounded-full object-cover"
                  />
                ) : (
                  <span className="text-4xl">{userData.name.charAt(0)}</span>
                )}
              </div>
              <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition mt-2">
                Change Photo
              </button>
            </div>

            <div className="md:w-2/3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="profile-name"
                    className="block text-gray-700 dark:text-gray-300 font-medium mb-2"
                  >
                    Name
                  </label>
                  <input
                    type="text"
                    id="profile-name"
                    value={userData.name}
                    className="w-full px-4 py-2 border dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    readOnly
                  />
                </div>

                <div>
                  <label
                    htmlFor="profile-email"
                    className="block text-gray-700 dark:text-gray-300 font-medium mb-2"
                  >
                    Email
                  </label>
                  <input
                    type="email"
                    id="profile-email"
                    value={userData.email}
                    className="w-full px-4 py-2 border dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    readOnly
                  />
                </div>

                <div>
                  <label
                    htmlFor="profile-role"
                    className="block text-gray-700 dark:text-gray-300 font-medium mb-2"
                  >
                    Role
                  </label>
                  <input
                    type="text"
                    id="profile-role"
                    value={userData.role}
                    className="w-full px-4 py-2 border dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    readOnly
                  />
                </div>

                <div>
                  <label
                    htmlFor="profile-org"
                    className="block text-gray-700 dark:text-gray-300 font-medium mb-2"
                  >
                    Organization
                  </label>
                  <input
                    type="text"
                    id="profile-org"
                    value={userData.organization}
                    className="w-full px-4 py-2 border dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    readOnly
                  />
                </div>
              </div>

              <div className="mt-6">
                <label
                  id="member-since-label"
                  className="block text-gray-700 dark:text-gray-300 font-medium mb-2"
                >
                  Member Since
                </label>
                <p
                  aria-labelledby="member-since-label"
                  className="text-gray-600 dark:text-gray-400"
                >
                  {new Date(userData.joinDate).toLocaleDateString()}
                </p>
              </div>

              <div className="mt-6 pt-6 border-t dark:border-gray-700">
                <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition">
                  Edit Profile
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preferences Tab */}
      {activeTab === "preferences" && (
        <>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-700 dark:text-gray-200 border-b pb-2">
              Display Settings
            </h2>

            <div className="mb-4">
              <label
                id="theme-label"
                className="block text-gray-700 dark:text-gray-300 font-medium mb-2"
              >
                Theme
              </label>
              <div aria-labelledby="theme-label" className="flex space-x-4">
                <button
                  onClick={() => updatePreference("theme", "light")}
                  className={`px-4 py-2 rounded-md ${
                    preferences.theme === "light"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  Light
                </button>
                <button
                  onClick={() => updatePreference("theme", "dark")}
                  className={`px-4 py-2 rounded-md ${
                    preferences.theme === "dark"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  Dark
                </button>
              </div>
            </div>

            <div className="mb-4">
              <label
                htmlFor="bills-per-page"
                className="block text-gray-700 dark:text-gray-300 font-medium mb-2"
              >
                Bills Per Page
              </label>
              <select
                id="bills-per-page"
                value={preferences.billsPerPage}
                onChange={(e) =>
                  updatePreference("billsPerPage", Number(e.target.value))
                }
                className="w-full md:w-1/3 px-4 py-2 border dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>

            <div className="mb-4">
              <label
                id="default-view-label"
                className="block text-gray-700 dark:text-gray-300 font-medium mb-2"
              >
                Default View
              </label>
              <div
                aria-labelledby="default-view-label"
                className="flex space-x-4"
              >
                <button
                  onClick={() => updatePreference("defaultView", "list")}
                  className={`flex items-center px-4 py-2 rounded-md ${
                    preferences.defaultView === "list"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  <FaList className="mr-2" /> List
                </button>
                <button
                  onClick={() => updatePreference("defaultView", "grid")}
                  className={`flex items-center px-4 py-2 rounded-md ${
                    preferences.defaultView === "grid"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  <FaTh className="mr-2" /> Grid
                </button>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-700 dark:text-gray-200 border-b pb-2">
              <div className="flex items-center">
                <FaSave className="mr-2 text-blue-600" />
                Saved Filters
              </div>
            </h2>

            {preferences.savedFilters.length > 0 ? (
              <div className="space-y-3">
                {preferences.savedFilters.map((filter) => (
                  <div
                    key={filter.id}
                    className="flex justify-between items-center p-3 bg-gray-50 rounded-md"
                  >
                    <div>
                      <h3 className="font-medium">{filter.name}</h3>
                      <p className="text-sm text-gray-600">
                        {Object.entries(filter.criteria)
                          .filter(([key, value]) => value)
                          .map(([key, value]) => `${key}: ${value}`)
                          .join(", ")}
                      </p>
                    </div>
                    <button
                      onClick={() => removeSavedFilter(filter.id)}
                      className="text-red-500 hover:text-red-700"
                      aria-label="Remove saved filter"
                    >
                      <FaTrash />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 italic">
                No saved filters yet. Save a search from the bills page to see
                it here.
              </p>
            )}
          </div>
        </>
      )}

      {/* Notifications Tab */}
      {activeTab === "notifications" && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-700 dark:text-gray-200 border-b pb-2">
            <div className="flex items-center">
              <FaBell className="mr-2 text-blue-600" />
              Notification Preferences
            </div>
          </h2>

          <NotificationPreferences />
        </div>
      )}

      {/* Support Tab */}
      {activeTab === "support" && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-700 dark:text-gray-200 border-b pb-2">
            <div className="flex items-center">
              <FaQuestionCircle className="mr-2 text-blue-600" />
              Support
            </div>
          </h2>

          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
                Get Help
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                If you&apos;re experiencing any issues with the application,
                please contact our support team.
              </p>
              <div className="flex flex-col md:flex-row gap-4">
                <a
                  href="mailto:support@policypulse.com"
                  className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
                >
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    ></path>
                  </svg>
                  Email Support
                </a>
                <button className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition">
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                    ></path>
                  </svg>
                  Live Chat
                </button>
              </div>
            </div>

            <div className="pt-4 border-t dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
                Documentation
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Access our comprehensive documentation to learn more about using
                PolicyPulse.
              </p>
              <a
                href="/documentation"
                className="inline-flex items-center px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition"
              >
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  ></path>
                </svg>
                View Documentation
              </a>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-700 dark:text-gray-200 border-b pb-2">
          Account Actions
        </h2>

        <div className="flex flex-col md:flex-row gap-4">
          <button
            onClick={resetPreferences}
            className="flex items-center px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 transition"
          >
            <FaUndo className="mr-2" /> Reset Preferences
          </button>

          <button className="flex items-center px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition">
            <FaTrash className="mr-2" /> Delete Account
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserPreferences;
