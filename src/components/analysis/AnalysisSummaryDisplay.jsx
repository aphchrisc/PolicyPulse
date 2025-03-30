import React from "react";
import PropTypes from "prop-types";

/**
 * Helper function to format object keys into readable titles.
 * Example: 'public_health_impacts' -> 'Public Health Impacts'
 */
const formatKey = (key) => {
  if (typeof key !== "string") return "";
  return key
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

/**
 * Determine the appropriate color class based on impact type
 */
const getImpactTagColor = (impactType) => {
  switch (impactType?.toLowerCase()) {
    case "positive":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    case "negative":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
    case "neutral":
      return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200";
    default:
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"; // Default/unknown
  }
};

/**
 * Component for displaying the analysis summary section
 * Shows a summary paragraph and key points with impact tags
 */
const AnalysisSummaryDisplay = ({ data }) => (
  <div className="card bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6">
    {/* Removed the Summary heading per requirements */}
    <div className="prose dark:prose-invert max-w-none">
      <p className="text-gray-700 dark:text-gray-300">
        {data?.summary || "No summary available."}
      </p>
      {/* Display first few key points for quick reference with impact tags */}
      {Array.isArray(data?.key_points) && data.key_points.length > 0 && (
        <div className="mt-3">
          <h4 className="text-md font-medium mb-1 text-gray-700 dark:text-gray-300">
            Key Points:
          </h4>
          {/* Use list-none for custom layout with tags */}
          <ul className="list-none pl-0 space-y-2 text-sm">
            {/* Removed .slice(0, 3) to show all points */}
            {data.key_points.map((item, idx) => (
              <li
                key={idx}
                className="flex items-start text-gray-600 dark:text-gray-400"
              >
                <span className="mr-2 mt-1 text-gray-400 dark:text-gray-500 text-xs">
                  &bull;
                </span>{" "}
                {/* Manual bullet */}
                <span className="flex-1">
                  {typeof item === "string" ? item : item?.point || ""}
                </span>
                {/* Add impact tag if available */}
                {typeof item === "object" && item?.impact_type && (
                  <span
                    className={`ml-2 flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${getImpactTagColor(
                      item.impact_type
                    )}`}
                  >
                    {formatKey(item.impact_type)}
                  </span>
                )}
              </li>
            ))}
            {/* Removed truncation message */}
          </ul>
        </div>
      )}
    </div>
  </div>
);

AnalysisSummaryDisplay.propTypes = {
  data: PropTypes.shape({
    summary: PropTypes.string,
    key_points: PropTypes.arrayOf(
      PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.shape({
          point: PropTypes.string,
          impact_type: PropTypes.string, // Expect impact_type now
        }),
      ])
    ),
  }),
};

export default AnalysisSummaryDisplay;
