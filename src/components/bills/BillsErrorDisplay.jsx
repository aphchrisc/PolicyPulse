import React from "react";
import PropTypes from "prop-types";

/**
 * Error display component for bills page with helpful user instructions
 * @param {Object} props
 * @param {string} props.message - Error message to display
 * @param {Function} props.onRetry - Optional retry function
 */
const BillsErrorDisplay = ({ message, onRetry }) => {
  if (!message) return null;

  const isServerError = message.includes("status: 5");
  const isNetworkError = message.includes("No response received");

  return (
    <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 mb-6 dark:bg-yellow-900 dark:border-yellow-600">
      <div className="flex">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-yellow-500 dark:text-yellow-400"
            width="20"
            height="20"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3 flex-grow">
          <p className="text-sm text-yellow-700 dark:text-yellow-300 font-medium mb-2">
            {message}
          </p>

          <div className="text-xs text-yellow-600 dark:text-yellow-400">
            {isServerError && (
              <p>
                The server encountered an error. This is not your fault - please
                try again later.
              </p>
            )}

            {isNetworkError && (
              <p>
                Check your internet connection and make sure the API server is
                running.
              </p>
            )}

            <p className="mt-1">
              Suggestions:
              <ul className="list-disc ml-5 mt-1">
                <li>Make sure the backend API service is running</li>
                <li>Check your network connection</li>
                <li>Try a different search or filter</li>
                {onRetry && <li>Click the retry button below</li>}
              </ul>
            </p>
          </div>

          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 inline-flex items-center px-3 py-1 border border-transparent text-xs leading-4 font-medium rounded text-yellow-700 bg-yellow-100 hover:bg-yellow-200 dark:text-yellow-200 dark:bg-yellow-800 dark:hover:bg-yellow-700 transition"
            >
              <svg
                className="mr-1 h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

BillsErrorDisplay.propTypes = {
  message: PropTypes.string,
  onRetry: PropTypes.func,
};

BillsErrorDisplay.defaultProps = {
  message: null,
  onRetry: null,
};

export default BillsErrorDisplay;
