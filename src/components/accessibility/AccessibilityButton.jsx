import React, { useState, useCallback } from "react";
import PropTypes from "prop-types";
import AccessibilityPanel from "./AccessibilityPanel";

/**
 * Accessibility button component that toggles the accessibility panel
 *
 * @param {Object} props - Component props
 * @param {string} props.className - Additional CSS classes
 */
const AccessibilityButton = ({ className = "" }) => {
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  // Use useCallback to prevent unnecessary re-renders
  const togglePanel = useCallback(() => {
    setIsPanelOpen((prevState) => !prevState);
  }, []);

  const closePanel = useCallback(() => {
    setIsPanelOpen(false);
  }, []);

  return (
    <>
      <button
        onClick={togglePanel}
        className={`p-2 rounded-full transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-blue-500 hover:bg-gray-100 dark:hover:bg-gray-700 ${className}`}
        aria-label="Accessibility settings"
        title="Accessibility settings"
      >
        <svg
          className="icon-md inline-block flex-shrink-0 text-blue-500 dark:text-blue-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </button>

      {/* Only mount the panel component when it's supposed to be open */}
      {isPanelOpen && (
        <AccessibilityPanel isOpen={isPanelOpen} onClose={closePanel} />
      )}
    </>
  );
};

AccessibilityButton.propTypes = {
  className: PropTypes.string,
};

export default AccessibilityButton;
