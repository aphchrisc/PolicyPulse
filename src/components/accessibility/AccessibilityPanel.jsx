import React, { useState, useRef, useEffect } from "react";
import PropTypes from "prop-types";
import { useAccessibility } from "../../context/AccessibilityContext";

/**
 * Accessibility settings panel component
 *
 * @param {Object} props - Component props
 * @param {boolean} props.isOpen - Whether the panel is open
 * @param {Function} props.onClose - Callback when the panel is closed
 * @param {string} props.className - Additional CSS classes
 */
const AccessibilityPanel = ({ isOpen, onClose, className = "" }) => {
  const { settings, toggleSetting, resetSettings } = useAccessibility();
  const [showConfirmReset, setShowConfirmReset] = useState(false);
  const dialogRef = useRef(null);

  // Dialog management
  useEffect(() => {
    // Only handle the dialog if it exists in the DOM
    if (!dialogRef.current) return;

    // Handle opening
    if (isOpen) {
      try {
        dialogRef.current.showModal();
      } catch (e) {
        // Dialog might already be open
        console.error("Error opening dialog:", e);
      }
    } else {
      try {
        dialogRef.current.close();
      } catch (e) {
        // Dialog might already be closed
        console.error("Error closing dialog:", e);
      }
    }
  }, [isOpen]);

  // Event handlers setup - separate useEffect to avoid race conditions
  useEffect(() => {
    // Only set up handlers if the dialog is open
    if (!isOpen || !dialogRef.current) return;

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        e.preventDefault(); // Prevent default dialog close
        onClose();
      }
    };

    const handleDialogClick = (e) => {
      // Close when clicking the backdrop (the dialog element itself)
      if (e.target === dialogRef.current) {
        onClose();
      }
    };

    // Add event listeners
    document.addEventListener("keydown", handleKeyDown);
    dialogRef.current.addEventListener("click", handleDialogClick);

    // Cleanup function
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      if (dialogRef.current) {
        dialogRef.current.removeEventListener("click", handleDialogClick);
      }
    };
  }, [isOpen, onClose]);

  const handleResetClick = () => {
    setShowConfirmReset(true);
  };

  const handleConfirmReset = () => {
    resetSettings();
    setShowConfirmReset(false);
  };

  const handleCancelReset = () => {
    setShowConfirmReset(false);
  };

  // If panel is not open, don't render anything
  if (!isOpen) {
    return null;
  }

  return (
    <dialog
      ref={dialogRef}
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-0 m-0 w-full h-full ${className}`}
      aria-labelledby="accessibility-title"
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto"
        tabIndex="-1"
      >
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <h2
            id="accessibility-title"
            className="text-lg font-semibold text-gray-900 dark:text-white"
          >
            Accessibility Settings
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            aria-label="Close"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="p-4 space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Customize your experience with these accessibility options. Settings
            are saved automatically.
          </p>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <label
                  htmlFor="high-contrast"
                  className="font-medium text-gray-900 dark:text-white"
                >
                  High Contrast Mode
                </label>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Increases contrast for better readability
                </p>
              </div>
              <div className="relative inline-block w-10 mr-2 align-middle select-none">
                <input
                  id="high-contrast"
                  type="checkbox"
                  checked={settings.highContrast}
                  onChange={() => toggleSetting("highContrast")}
                  className="sr-only"
                />
                <label
                  htmlFor="high-contrast"
                  className={`block overflow-hidden h-6 rounded-full cursor-pointer ${
                    settings.highContrast
                      ? "bg-blue-600"
                      : "bg-gray-300 dark:bg-gray-600"
                  }`}
                  aria-label="Toggle high contrast mode"
                >
                  <span
                    className={`block h-6 w-6 rounded-full bg-white shadow transform transition-transform duration-200 ease-in-out ${
                      settings.highContrast ? "translate-x-4" : "translate-x-0"
                    }`}
                  ></span>
                </label>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label
                  htmlFor="large-text"
                  className="font-medium text-gray-900 dark:text-white"
                >
                  Larger Text
                </label>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Increases font size throughout the application
                </p>
              </div>
              <div className="relative inline-block w-10 mr-2 align-middle select-none">
                <input
                  id="large-text"
                  type="checkbox"
                  checked={settings.largeText}
                  onChange={() => toggleSetting("largeText")}
                  className="sr-only"
                />
                <label
                  htmlFor="large-text"
                  className={`block overflow-hidden h-6 rounded-full cursor-pointer ${
                    settings.largeText
                      ? "bg-blue-600"
                      : "bg-gray-300 dark:bg-gray-600"
                  }`}
                  aria-label="Toggle larger text"
                >
                  <span
                    className={`block h-6 w-6 rounded-full bg-white shadow transform transition-transform duration-200 ease-in-out ${
                      settings.largeText ? "translate-x-4" : "translate-x-0"
                    }`}
                  ></span>
                </label>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label
                  htmlFor="reduce-motion"
                  className="font-medium text-gray-900 dark:text-white"
                >
                  Reduce Motion
                </label>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Minimizes animations and transitions
                </p>
              </div>
              <div className="relative inline-block w-10 mr-2 align-middle select-none">
                <input
                  id="reduce-motion"
                  type="checkbox"
                  checked={settings.reduceMotion}
                  onChange={() => toggleSetting("reduceMotion")}
                  className="sr-only"
                />
                <label
                  htmlFor="reduce-motion"
                  className={`block overflow-hidden h-6 rounded-full cursor-pointer ${
                    settings.reduceMotion
                      ? "bg-blue-600"
                      : "bg-gray-300 dark:bg-gray-600"
                  }`}
                  aria-label="Toggle reduce motion"
                >
                  <span
                    className={`block h-6 w-6 rounded-full bg-white shadow transform transition-transform duration-200 ease-in-out ${
                      settings.reduceMotion ? "translate-x-4" : "translate-x-0"
                    }`}
                  ></span>
                </label>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label
                  htmlFor="screen-reader"
                  className="font-medium text-gray-900 dark:text-white"
                >
                  Screen Reader Optimized
                </label>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Enhances compatibility with screen readers
                </p>
              </div>
              <div className="relative inline-block w-10 mr-2 align-middle select-none">
                <input
                  id="screen-reader"
                  type="checkbox"
                  checked={settings.screenReader}
                  onChange={() => toggleSetting("screenReader")}
                  className="sr-only"
                />
                <label
                  htmlFor="screen-reader"
                  className={`block overflow-hidden h-6 rounded-full cursor-pointer ${
                    settings.screenReader
                      ? "bg-blue-600"
                      : "bg-gray-300 dark:bg-gray-600"
                  }`}
                  aria-label="Toggle screen reader optimization"
                >
                  <span
                    className={`block h-6 w-6 rounded-full bg-white shadow transform transition-transform duration-200 ease-in-out ${
                      settings.screenReader ? "translate-x-4" : "translate-x-0"
                    }`}
                  ></span>
                </label>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            {showConfirmReset ? (
              <div className="space-y-2">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Are you sure you want to reset all accessibility settings to
                  their defaults?
                </p>
                <div className="flex space-x-2">
                  <button
                    onClick={handleConfirmReset}
                    className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                  >
                    Yes, Reset
                  </button>
                  <button
                    onClick={handleCancelReset}
                    className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={handleResetClick}
                className="w-full px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Reset to Default Settings
              </button>
            )}
          </div>
        </div>
      </div>
    </dialog>
  );
};

AccessibilityPanel.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  className: PropTypes.string,
};

export default AccessibilityPanel;
