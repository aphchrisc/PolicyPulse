import React from "react";
import PropTypes from "prop-types";

/**
 * Helper function to format object keys into readable titles.
 * Example: 'public_health_impacts' -> 'Public Health Impacts'
 * @param {string} key - The object key.
 * @returns {string} - Formatted title.
 */
const formatKey = (key) => {
  if (typeof key !== "string") return "";
  return key
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

// Impact tag colors remain the same
const getImpactTagColor = (impactType) => {
  switch (impactType?.toLowerCase()) {
    case "positive":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    case "negative":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
    case "neutral":
      return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200";
    default:
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
  }
};

/**
 * Helper function to render a section with a title and content.
 * Handles different content types (string, array, object) and applies subheading styling.
 * @param {string | null} title - The title of the section (null for recursive calls without outer box).
 * @param {any} content - The data to render.
 * @param {string} sectionKey - A unique key for the section.
 * @returns {JSX.Element|null} - Rendered section or null if content is empty.
 */
const renderSection = (title, content, sectionKey) => {
  // Basic checks for empty content
  if (content === null || content === undefined) return null;
  if (typeof content === "string" && !content.trim()) return null;
  if (Array.isArray(content) && content.length === 0) return null;
  if (
    typeof content === "object" &&
    !Array.isArray(content) &&
    Object.keys(content).length === 0
  )
    return null;

  let renderedContent;

  if (typeof content === "string") {
    // Render simple strings, handling potential date formatting
    if (sectionKey.endsWith("analysis_date") && !isNaN(Date.parse(content))) {
      renderedContent = (
        <p className="text-gray-700 dark:text-gray-300">
          {new Date(content).toLocaleDateString()}
        </p>
      );
    } else {
      renderedContent = (
        <p className="text-gray-700 dark:text-gray-300">{content}</p>
      );
    }
  } else if (Array.isArray(content)) {
    // Render arrays as simple bullet points (excluding key_points which are handled in summary)
    renderedContent = (
      <ul className="list-disc pl-5 space-y-1">
        {content.map((item, index) => (
          <li
            key={`${sectionKey}-${index}`}
            className="text-gray-600 dark:text-gray-400"
          >
            {typeof item === "string" ? item : JSON.stringify(item)}
          </li>
        ))}
      </ul>
    );
  } else if (typeof content === "object") {
    // Render nested objects - treat keys as subheadings
    renderedContent = (
      // Removed indentation and border: pl-3 border-l border-gray-200 dark:border-gray-700
      <div className="space-y-3">
        {Object.entries(content).map(([key, value]) => {
          const formattedSubTitle = formatKey(key);
          const subSectionKey = `${sectionKey}-${key}`;
          // Render the key as a subheading, then recursively render the value
          const subContent = renderSection(null, value, subSectionKey); // Pass null title for recursive call

          // Only render if there's actual sub-content to display
          return subContent ? (
            <div key={subSectionKey} className="mt-2">
              {" "}
              {/* Add some margin-top for sub-sections */}
              <h5 className="text-sm font-semibold mb-1 text-gray-700 dark:text-gray-300">
                {formattedSubTitle}
              </h5>
              {subContent}
            </div>
          ) : null;
        })}
      </div>
    );
  } else {
    // Fallback for other types
    renderedContent = (
      <p className="text-gray-700 dark:text-gray-300">{String(content)}</p>
    );
  }

  // If title is null, just return the inner content (used for recursive calls)
  if (title === null) {
    return renderedContent;
  }

  // Render the full section with title and border box
  return (
    // Reverted background color: dark:bg-gray-800/50 -> dark:bg-gray-800
    <div
      key={sectionKey}
      className="mb-4 p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800"
    >
      <h4 className="text-md font-semibold mb-2 text-gray-800 dark:text-gray-200">
        {title}
      </h4>
      {/* Removed prose class to rely on direct styling for better control */}
      <div className="max-w-none text-sm">{renderedContent}</div>
    </div>
  );
};

/**
 * Renders the detailed analysis sections from the analysis data.
 */
const DetailedAnalysisView = ({ analysisData }) => {
  if (!analysisData || typeof analysisData !== "object") {
    return (
      <p className="text-gray-500 dark:text-gray-400">
        No detailed analysis data available.
      </p>
    );
  }

  // Define the order and keys of sections to display
  // REMOVED key_points from here to avoid duplication
  const sections = [
    { key: "public_health_impacts", title: "Public Health Impacts" },
    { key: "local_gov_impacts", title: "Local Government Impacts" },
    { key: "economic_impacts", title: "Economic Impacts" },
    { key: "environmental_impacts", title: "Environmental Impacts" },
    { key: "education_impacts", title: "Education Impacts" },
    { key: "infrastructure_impacts", title: "Infrastructure Impacts" },
    { key: "stakeholder_impacts", title: "Stakeholder Impacts" },
    { key: "recommended_actions", title: "Recommended Actions" },
    { key: "immediate_actions", title: "Immediate Actions" },
    { key: "resource_needs", title: "Resource Needs" },
    { key: "priority", title: "Priority Assessment" },
    { key: "impact_ratings", title: "Impact Ratings" },
    {
      key: "implementation_requirements",
      title: "Implementation Requirements",
    },
    { key: "model_version", title: "Analysis Model Version" },
    { key: "analysis_date", title: "Analysis Date" },
  ];

  // Filter out sections that don't exist in the data or are explicitly empty/null/empty string
  const availableSections = sections.filter((section) => {
    const content = analysisData[section.key];
    if (content === null || content === undefined) return false;
    if (typeof content === "string" && !content.trim()) return false;
    if (Array.isArray(content) && content.length === 0) return false;
    if (
      typeof content === "object" &&
      !Array.isArray(content) &&
      Object.prototype.toString.call(content) === "[object Object]" &&
      Object.keys(content).length === 0
    )
      return false;
    return analysisData.hasOwnProperty(section.key);
  });

  if (availableSections.length === 0) {
    return (
      <p className="text-gray-500 dark:text-gray-400 mt-4">
        No detailed impact sections found in the analysis.
      </p>
    );
  }

  return (
    <div className="mt-6">
      {availableSections.map((section) =>
        renderSection(section.title, analysisData[section.key], section.key)
      )}
    </div>
  );
};

DetailedAnalysisView.propTypes = {
  analysisData: PropTypes.object,
};

export default DetailedAnalysisView;
