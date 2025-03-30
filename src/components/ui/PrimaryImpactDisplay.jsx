import React from "react";

/**
 * PrimaryImpactDisplay - A reusable component for displaying primary impact information
 * with consistent styling
 *
 * @param {Object} props - Component props
 * @param {string} props.impactDetails - The impact details to display
 * @param {string} props.className - Additional CSS classes
 * @param {boolean} props.showLabel - Whether to show the "Primary impact:" label
 */
const PrimaryImpactDisplay = ({
  impactDetails,
  className = "",
  showLabel = false,
}) => {
  if (!impactDetails) return null;

  return (
    <span
      className={`inline-flex items-center text-xs font-medium text-gray-600 dark:text-gray-400 ${className}`}
    >
      {showLabel && <span className="mr-1">Primary impact:</span>}
      <span className="px-2 py-0.5 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
        {impactDetails}
      </span>
    </span>
  );
};

export default PrimaryImpactDisplay;
