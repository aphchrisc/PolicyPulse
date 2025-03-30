import React, { useState, useEffect } from "react";
import KeyTermsCloud from "./KeyTermsCloud";
import ImpactChart from "./ImpactChart";
import BillTimeline from "./BillTimeline";
import AnalysisRadarChart from "./AnalysisRadarChart";
import ImpactRatingsVisualization from "../analysis/ImpactRatingsVisualization"; // Import the new component
import { useUserPreferences } from "../../context/UserPreferencesContext";
import { FiBarChart2, FiClock, FiSearch, FiPieChart, FiStar } from "react-icons/fi"; // Added FiStar for ratings
import logger from "../../utils/logger";

/**
 * Loading indicator component
 */
const LoadingIndicator = () => (
  <div className="absolute inset-0 flex items-center justify-center">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
  </div>
);

/**
 * Message for when no data is available
 */
const NoDataMessage = ({ message }) => (
  <div className="flex items-center justify-center h-64">
    <div className="text-center text-gray-500 dark:text-gray-400">
      <p className="text-lg font-medium">{message}</p>
      <p className="text-sm mt-2">
        No data available to generate this visualization
      </p>
    </div>
  </div>
);

/**
 * Tab button component
 */
const TabButton = ({ tab, isActive, onClick, disabled }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={`flex items-center mr-4 py-2 px-4 border-b-2 font-medium text-sm whitespace-nowrap transition-colors duration-200
      ${!disabled ? "cursor-pointer" : "opacity-50 cursor-not-allowed"}
      ${
        isActive
          ? "border-blue-500 text-blue-600 dark:text-blue-400"
          : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600"
      }`}
    aria-current={isActive ? "page" : undefined}
  >
    <span className="mr-2">{tab.icon}</span>
    {tab.label}
  </button>
);

/**
 * Key Terms visualization component
 */
const KeyTermsVisualization = ({ analysisData, billData, isDarkMode }) => {
  const enrichedAnalysisData = {
    ...analysisData,
    bill: billData,
    latest_text: billData?.latest_text || analysisData?.latest_text,
  };
  return (
    <KeyTermsCloud
      analysisData={enrichedAnalysisData}
      height={300}
      width={600}
      isDarkMode={isDarkMode}
    />
  );
};

/**
 * Impact Assessment visualization component
 */
const ImpactAssessmentVisualization = ({ analysisData, isDarkMode }) => {
  return <ImpactChart analysisData={analysisData} isDarkMode={isDarkMode} />;
};

/**
 * Radar Chart visualization component
 */
const RadarVisualization = ({ analysisData, isDarkMode }) => {
  return (
    <AnalysisRadarChart analysisData={analysisData} isDarkMode={isDarkMode} />
  );
};

/**
 * Timeline visualization component
 */
const TimelineVisualization = ({ billData, isDarkMode }) => {
  return <BillTimeline billData={billData} isDarkMode={isDarkMode} />;
};

/**
 * Main visualization dashboard component
 */
const VisualizationDashboard = ({ bill }) => {
  const [activeTab, setActiveTab] = useState("keyTerms");
  const { preferences } = useUserPreferences();
  const isDarkMode = preferences.theme === "dark";

  const billData = bill || {};
  const analysisData = bill?.analysis || {};

  // Check if we have valid data for each tab
  const hasKeyTerms = !!bill;
  const hasImpactData = !!analysisData && Object.keys(analysisData).length > 0;
  const hasRadarData = !!analysisData && Object.keys(analysisData).length > 0;
  const hasTimelineData =
    !!billData &&
    Array.isArray(billData.history) &&
    billData.history.length > 0;
  // Check for impact ratings data
  const hasImpactRatingsData =
    !!analysisData &&
    Array.isArray(analysisData.impact_ratings) &&
    analysisData.impact_ratings.length > 0;

  const tabs = [
    {
      id: "keyTerms",
      label: "Key Terms",
      icon: <FiSearch className="w-4 h-4" />,
      enabled: hasKeyTerms,
    },
    {
      id: "impact",
      label: "Impact Assessment",
      icon: <FiBarChart2 className="w-4 h-4" />,
      enabled: hasImpactData,
    },
    {
      id: "radar",
      label: "Impact Radar",
      icon: <FiPieChart className="w-4 h-4" />,
      enabled: hasRadarData,
    },
    // Add the new Impact Ratings tab
    {
      id: "ratings",
      label: "Impact Ratings",
      icon: <FiStar className="w-4 h-4" />, // Use FiStar icon
      enabled: hasImpactRatingsData,
    },
    {
      id: "timeline",
      label: "Bill Timeline",
      icon: <FiClock className="w-4 h-4" />,
      enabled: hasTimelineData,
    },
  ];

  // If current active tab has no data, switch to first available tab
  useEffect(() => {
    const currentTab = tabs.find((tab) => tab.id === activeTab);
    if (currentTab && !currentTab.enabled) {
      const firstEnabledTab = tabs.find((tab) => tab.enabled);
      if (firstEnabledTab) {
        setActiveTab(firstEnabledTab.id);
      } else {
         // If no tabs are enabled, maybe default to keyTerms or handle appropriately
         setActiveTab("keyTerms");
      }
    }
  }, [activeTab, tabs]); // Dependency array includes tabs now

  /**
   * Render the active visualization based on selected tab
   */
  const renderVisualization = () => {
    if (!billData) {
      return <LoadingIndicator />;
    }

    // No data state (check if *any* visualization data is available)
    const hasAnyVizData = hasKeyTerms || hasImpactData || hasRadarData || hasTimelineData || hasImpactRatingsData;
    if (!hasAnyVizData) {
      return (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center text-gray-500 dark:text-gray-400">
            <p className="text-lg font-medium">No analysis data available</p>
            <p className="text-sm">
              Analysis data is required to generate visualizations
            </p>
          </div>
        </div>
      );
    }

    switch (activeTab) {
      case "keyTerms":
        return hasKeyTerms ? (
          <KeyTermsVisualization
            analysisData={analysisData}
            billData={billData}
            isDarkMode={isDarkMode}
          />
        ) : (
          <NoDataMessage message="No key terms data available" />
        );

      case "impact":
        return hasImpactData ? (
          <ImpactAssessmentVisualization
            analysisData={analysisData}
            isDarkMode={isDarkMode}
          />
        ) : (
          <NoDataMessage message="No impact assessment data available" />
        );

      case "radar":
        return hasRadarData ? (
          <RadarVisualization
            analysisData={analysisData}
            isDarkMode={isDarkMode}
          />
        ) : (
          <NoDataMessage message="No radar chart data available" />
        );

      // Add case for the new ratings tab
      case "ratings":
        return hasImpactRatingsData ? (
          <ImpactRatingsVisualization ratings={analysisData.impact_ratings} />
        ) : (
          <NoDataMessage message="No impact ratings data available" />
        );

      case "timeline":
        return hasTimelineData ? (
          <TimelineVisualization billData={billData} isDarkMode={isDarkMode} />
        ) : (
          <NoDataMessage message="No timeline data available" />
        );

      default:
        // Fallback to first enabled tab if somehow default is reached
        const firstEnabledTab = tabs.find(tab => tab.enabled);
        if (firstEnabledTab) setActiveTab(firstEnabledTab.id);
        return null;
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg transition-colors duration-200">
      <div className="flex border-b border-gray-200 dark:border-gray-700 mb-4 overflow-x-auto">
        {tabs.map((tab) => (
          <TabButton
            key={tab.id}
            tab={tab}
            isActive={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            disabled={!tab.enabled}
          />
        ))}
      </div>

      {/* Removed fixed height to allow content to determine size */}
      <div className="visualization-container relative p-4 min-h-[200px]">
        {renderVisualization()}
      </div>
    </div>
  );
};

export default VisualizationDashboard;
