import React from "react";
import PropTypes from "prop-types";
import DetailedAnalysisView from "./DetailedAnalysisView"; // Import the new component
import AnalysisSummaryDisplay from "./AnalysisSummaryDisplay";

// Helper functions copied from DetailedAnalysisView for consistency
const formatKey = (key) => {
  if (typeof key !== "string") return "";
  return key
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

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
 * Main component to display the bill analysis.
 * Handles loading states, insufficient text warnings, and renders summary + detailed view.
 */
const AnalysisDashboard = ({ analysisData }) => {
  // 1. Handle insufficient text case
  if (analysisData?.insufficient_text) {
    return (
      <div className="analysis-dashboard p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg text-center">
        <h2 className="text-xl font-semibold mb-2 text-yellow-800 dark:text-yellow-200">
          Bill Analysis
        </h2>
        <p className="text-yellow-700 dark:text-yellow-300">
          Insufficient text was available for a detailed analysis.
        </p>
        {/* Optionally show summary if it exists even with insufficient text */}
        {analysisData.summary && (
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Summary: {analysisData.summary}
          </p>
        )}
      </div>
    );
  }

  // 2. Handle case where analysis is missing or incomplete (but not due to insufficient text)
  if (
    !analysisData ||
    typeof analysisData !== "object" ||
    Object.keys(analysisData).length === 0 ||
    !analysisData.summary
  ) {
    return (
      <div className="analysis-dashboard p-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-center">
        <h2 className="text-xl font-semibold mb-2 text-gray-600 dark:text-gray-300">
          Bill Analysis
        </h2>
        <p className="text-gray-500 dark:text-gray-400">
          Analysis data is not yet available or is currently incomplete.
        </p>
      </div>
    );
  }

  // 3. Render the full analysis dashboard
  return (
    <div className="analysis-dashboard space-y-6">
      {/* Display the high-level summary first */}
      <AnalysisSummaryDisplay data={analysisData} />

      {/* Render the new DetailedAnalysisView for the rest of the data */}
      <DetailedAnalysisView analysisData={analysisData} />
    </div>
  );
};

AnalysisDashboard.propTypes = {
  /** The analysis data object fetched from the API */
  analysisData: PropTypes.object,
};

export default AnalysisDashboard;
