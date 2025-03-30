import React from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

// SVG icons with proper sizing
const LightningIcon = () => (
  <svg
    className="w-6 h-6"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    xmlns="http://www.w3.org/2000/svg"
    style={{ minWidth: "24px", minHeight: "24px" }}
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M13 10V3L4 14h7v7l9-11h-7z"
    />
  </svg>
);

const InfoIcon = () => (
  <svg
    className="w-5 h-5"
    width="20"
    height="20"
    viewBox="0 0 20 20"
    fill="currentColor"
    xmlns="http://www.w3.org/2000/svg"
    style={{ minWidth: "20px", minHeight: "20px" }}
  >
    <path
      fillRule="evenodd"
      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
      clipRule="evenodd"
    />
  </svg>
);

const FEATURES = [
  {
    id: "feature-realtime",
    title: "Real-time Monitoring",
    description:
      "Track legislation from the White House, U.S. Congress, and Texas with real-time updates.",
  },
  {
    id: "feature-search",
    title: "Advanced Search",
    description:
      "Use powerful filters and search capabilities to find relevant legislation quickly.",
  },
  {
    id: "feature-alerts",
    title: "Custom Alerts",
    description:
      "Receive customized notifications when bills of interest move through the process.",
  },
];

const LandingPage = () => {
  return (
    <div className="p-6">
      {/* Hero Section */}
      <div className="bg-gradient-to-b from-blue-900 to-indigo-900 rounded-lg shadow-lg p-8 mb-6">
        <div className="max-w-4xl">
          <h1 className="text-4xl md:text-5xl font-bold leading-tight mb-4 text-white">
            Track Legislation That Matters
          </h1>
          <p className="text-xl mb-8 text-gray-200">
            PolicyPulse provides real-time monitoring and analysis of
            legislative activities across the White House, U.S. Congress, and
            Texas, helping policy professionals stay ahead of changes that
            impact their work.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link
              to="/dashboard"
              className="px-6 py-3 bg-blue-500 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
            >
              Get Started
            </Link>
            <Link
              to="/api-status"
              className="px-6 py-3 bg-gray-300 hover:bg-gray-400 text-gray-800 font-medium rounded-lg transition-colors"
            >
              View API Status
            </Link>
          </div>
        </div>
      </div>

      {/* Dashboard Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Weekly Activity Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
              Weekly Activity
            </h2>
            <div className="text-gray-500 dark:text-gray-400">
              <InfoIcon />
            </div>
          </div>
          <div className="mb-4">
            <h3 className="text-4xl font-bold text-gray-800 dark:text-white">
              47K
            </h3>
            <div className="inline-block px-2 py-1 mt-2 bg-green-100 text-green-800 text-xs font-semibold rounded-full">
              +3.5%
            </div>
          </div>
          <div className="flex justify-between items-center space-x-2">
            <div className="h-16 w-full bg-gray-100 dark:bg-gray-700 rounded-lg flex items-end">
              <div className="w-1/7 h-12 bg-blue-500 rounded-lg mx-1"></div>
              <div className="w-1/7 h-16 bg-blue-500 rounded-lg mx-1"></div>
              <div className="w-1/7 h-10 bg-blue-500 rounded-lg mx-1"></div>
              <div className="w-1/7 h-8 bg-gray-300 dark:bg-gray-600 rounded-lg mx-1"></div>
              <div className="w-1/7 h-14 bg-gray-300 dark:bg-gray-600 rounded-lg mx-1"></div>
              <div className="w-1/7 h-10 bg-gray-300 dark:bg-gray-600 rounded-lg mx-1"></div>
              <div className="w-1/7 h-12 bg-gray-300 dark:bg-gray-600 rounded-lg mx-1"></div>
            </div>
          </div>
        </div>

        {/* Total Bills Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
              Total Bills
            </h2>
          </div>
          <div className="mb-4">
            <h3 className="text-4xl font-bold text-gray-800 dark:text-white">
              58.4K
            </h3>
            <div className="inline-block px-2 py-1 mt-2 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full">
              +13.6%
            </div>
          </div>
          <div className="h-16 w-full bg-blue-50 dark:bg-blue-900/20 rounded-lg relative overflow-hidden">
            <div className="absolute inset-0 flex items-end">
              <div className="w-full h-12 bg-gradient-to-r from-blue-100 to-blue-500 dark:from-blue-900 dark:to-blue-500 rounded-lg"></div>
            </div>
          </div>
        </div>
      </div>

      {/* Key Features Section */}
      <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">
        Key Features
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {FEATURES.map((feature) => (
          <div
            key={feature.id}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6"
          >
            <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/50 rounded-full flex items-center justify-center mb-4">
              <LightningIcon />
            </div>
            <h3 className="text-xl font-bold mb-2 text-gray-800 dark:text-white">
              {feature.title}
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {feature.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LandingPage;
