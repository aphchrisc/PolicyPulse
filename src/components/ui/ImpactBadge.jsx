import React from "react";
import PropTypes from "prop-types";
import { impactPropTypes, uiPropTypes } from "./propTypes";

/**
 * ImpactBadge - A reusable component for displaying impact levels with consistent styling
 *
 * @param {Object} props - Component props
 * @param {string} props.impact - The impact level (critical, high, moderate, low)
 * @param {boolean} props.showText - Whether to show the "Impact" text after the level
 * @param {string} props.className - Additional CSS classes
 * @param {string} props.size - Size of the badge (sm, md, lg)
 */
const ImpactBadge = ({
  impact,
  showText = true,
  className = "",
  size = "md",
}) => {
  // Handle null or undefined impact level
  if (!impact) return null;

  // Normalize impact level to lowercase for consistency
  const impactLevel = impact.toLowerCase();

  // Map impact level to appropriate styling
  const getBadgeColor = () => {
    switch (impactLevel) {
      case "critical":
        return "bg-red-600 text-white";
      case "high":
        return "bg-orange-500 text-white";
      case "moderate":
        return "bg-yellow-400 text-gray-800";
      case "low":
        return "bg-blue-500 text-white";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
    }
  };

  // Determine size class
  const sizeClass = () => {
    switch (size) {
      case "sm":
        return "px-2 py-0.5 text-xs";
      case "lg":
        return "px-4 py-1.5 text-sm";
      case "md":
      default:
        return "px-3 py-1 text-xs";
    }
  };

  return (
    <span
      className={`
      rounded-full font-bold ${sizeClass()} ${getBadgeColor()} shadow-sm
      ${className}
    `}
    >
      {impact.charAt(0).toUpperCase() + impact.slice(1)}
      {showText && " Impact"}
    </span>
  );
};

// Define prop types for the component
ImpactBadge.propTypes = {
  impact: PropTypes.string.isRequired,
  showText: PropTypes.bool,
  className: PropTypes.string,
  size: PropTypes.oneOf(["sm", "md", "lg"]),
};

// Define default props
ImpactBadge.defaultProps = {
  showText: true,
  className: "",
  size: "md",
};

export default ImpactBadge;
