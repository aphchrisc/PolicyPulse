import React, { useState, useEffect } from "react";
import { billService } from "../services/api";
import AnalysisExport from "../components/export/AnalysisExport";
import ComparativeAnalysisExport from "../components/export/ComparativeAnalysisExport";
import ExportExample from "../components/export/ExportExample";
import logger from "../utils/logger";

/**
 * Dashboard component for managing bill exports
 * Allows users to export single bill analysis or comparative analysis of multiple bills
 */
const ExportDashboard = () => {
  const [selectedBills, setSelectedBills] = useState([]);
  const [availableBills, setAvailableBills] = useState([]);
  const [analysisData, setAnalysisData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [exportMode, setExportMode] = useState("single"); // 'single' or 'comparative'
  const [exportStatus, setExportStatus] = useState({ status: "", message: "" });
  const [activeTab, setActiveTab] = useState("export"); // 'export' or 'example'

  // Fetch available bills on component mount
  useEffect(() => {
    const fetchBills = async () => {
      try {
        setIsLoading(true);
        const response = await billService.searchBills({ limit: 10 });
        setAvailableBills(response.bills || []);
      } catch (error) {
        logger.error("Error fetching bills:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchBills();
  }, []);

  // Handle bill selection
  const handleBillSelect = (billId) => {
    // For single mode, replace the selection
    if (exportMode === "single") {
      const bill = availableBills.find((b) => b.id === billId);
      setSelectedBills(bill ? [bill] : []);
      // Clear analysis data when changing selection
      setAnalysisData([]);
    } else {
      // For comparative mode, toggle selection
      setSelectedBills((prev) => {
        const isSelected = prev.some((bill) => bill.id === billId);
        if (isSelected) {
          return prev.filter((bill) => bill.id !== billId);
        } else {
          const bill = availableBills.find((b) => b.id === billId);
          return bill ? [...prev, bill] : prev;
        }
      });
      // Clear analysis data when changing selection
      setAnalysisData([]);
    }
  };

  // Handle export mode change
  const handleModeChange = (mode) => {
    setExportMode(mode);
    // Reset selections when changing modes
    setSelectedBills([]);
    setAnalysisData([]);
  };

  // Fetch analysis data for selected bills
  const fetchAnalysisData = async () => {
    if (selectedBills.length === 0) {
      setExportStatus({
        status: "error",
        message: "Please select at least one bill to export",
      });
      return;
    }

    try {
      setIsLoading(true);
      setExportStatus({
        status: "loading",
        message: "Fetching analysis data...",
      });

      const analysisPromises = selectedBills.map((bill) =>
        billService
          .getAnalysis(bill.id)
          .then((data) => {
            // Get the most recent analysis if there are multiple
            const analyses = data.analyses || [];
            return analyses.length > 0 ? analyses[0] : null;
          })
          .catch((error) => {
            logger.error(`Error fetching analysis for bill ${bill.id}:`, error);
            return null;
          })
      );

      const results = await Promise.all(analysisPromises);
      const validResults = results.filter((result) => result !== null);

      if (validResults.length === 0) {
        setExportStatus({
          status: "error",
          message: "No analysis data available for the selected bills",
        });
        return;
      }

      setAnalysisData(validResults);
      setExportStatus({
        status: "success",
        message: "Analysis data loaded successfully",
      });
    } catch (error) {
      logger.error("Error fetching analysis data:", error);
      setExportStatus({
        status: "error",
        message: "Failed to fetch analysis data",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle export start
  const handleExportStart = () => {
    setExportStatus({
      status: "loading",
      message: "Generating PDF export...",
    });
  };

  // Handle export complete
  const handleExportComplete = (fileName) => {
    setExportStatus({
      status: "success",
      message: `Export complete: ${fileName}`,
    });
  };

  // Handle export error
  const handleExportError = (errorMessage) => {
    setExportStatus({
      status: "error",
      message: `Export failed: ${errorMessage}`,
    });
  };

  return (
    <div className="container mx-auto p-4">
      <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-gray-200">
        Bill Analysis Export
      </h2>

      {/* Tab Navigation */}
      <div className="mb-6 border-b border-gray-200 dark:border-gray-700">
        <ul className="flex flex-wrap -mb-px">
          <li className="mr-2">
            <button
              onClick={() => setActiveTab("export")}
              className={`inline-block py-4 px-4 text-sm font-medium text-center rounded-t-lg border-b-2 ${
                activeTab === "export"
                  ? "text-blue-600 border-blue-600 dark:text-blue-500 dark:border-blue-500"
                  : "text-gray-500 border-transparent hover:text-gray-600 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300"
              }`}
            >
              Export Tool
            </button>
          </li>
          <li className="mr-2">
            <button
              onClick={() => setActiveTab("example")}
              className={`inline-block py-4 px-4 text-sm font-medium text-center rounded-t-lg border-b-2 ${
                activeTab === "example"
                  ? "text-blue-600 border-blue-600 dark:text-blue-500 dark:border-blue-500"
                  : "text-gray-500 border-transparent hover:text-gray-600 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300"
              }`}
            >
              Example & Documentation
            </button>
          </li>
        </ul>
      </div>

      {activeTab === "example" ? (
        <ExportExample />
      ) : (
        <>
          {/* Export Mode Selection */}
          <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <h3 className="text-lg font-semibold mb-4">Export Type</h3>
            <div className="flex space-x-4">
              <button
                onClick={() => handleModeChange("single")}
                className={`px-4 py-2 rounded-md ${
                  exportMode === "single"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200"
                }`}
              >
                Single Bill Analysis
              </button>
              <button
                onClick={() => handleModeChange("comparative")}
                className={`px-4 py-2 rounded-md ${
                  exportMode === "comparative"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200"
                }`}
              >
                Comparative Analysis
              </button>
            </div>
          </div>

          {/* Bill Selection */}
          <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <h3 className="text-lg font-semibold mb-4">
              {exportMode === "single"
                ? "Select a Bill"
                : "Select Bills to Compare"}
            </h3>

            {isLoading && !availableBills.length ? (
              <div className="flex justify-center items-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : (
              <div className="space-y-2">
                {availableBills.map((bill) => (
                  <div key={bill.id} className="flex items-start space-x-3">
                    <input
                      type="checkbox"
                      id={`bill-${bill.id}`}
                      checked={selectedBills.some(
                        (selected) => selected.id === bill.id
                      )}
                      onChange={() => handleBillSelect(bill.id)}
                      className="mt-1 rounded text-blue-600 focus:ring-blue-500"
                    />
                    <label
                      htmlFor={`bill-${bill.id}`}
                      className="flex-1 cursor-pointer"
                    >
                      <div className="font-medium text-gray-800 dark:text-gray-200">
                        {bill.title || `Bill ${bill.id}`}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        Status: {bill.status || "Unknown"} | Introduced:{" "}
                        {bill.introduced_date || "Unknown"}
                      </div>
                    </label>
                  </div>
                ))}

                {availableBills.length === 0 && (
                  <p className="text-gray-500 dark:text-gray-400 py-4 text-center">
                    No bills available. Please check your connection or try
                    again later.
                  </p>
                )}
              </div>
            )}

            <div className="mt-4">
              <button
                onClick={fetchAnalysisData}
                disabled={selectedBills.length === 0 || isLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <span className="flex items-center">
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Loading...
                  </span>
                ) : (
                  `Load Analysis Data for ${
                    exportMode === "single" ? "Bill" : "Comparison"
                  }`
                )}
              </button>
            </div>

            {/* Status Message */}
            {exportStatus.message && (
              <div
                className={`mt-4 p-3 rounded-md ${
                  exportStatus.status === "error"
                    ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200"
                    : exportStatus.status === "success"
                    ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200"
                    : "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200"
                }`}
              >
                {exportStatus.message}
              </div>
            )}
          </div>

          {/* Export Component */}
          {analysisData.length > 0 && (
            <div className="mb-6">
              {exportMode === "single" ? (
                <AnalysisExport
                  bill={selectedBills[0]}
                  analysisData={analysisData[0]}
                  onExportStart={handleExportStart}
                  onExportComplete={handleExportComplete}
                  onExportError={handleExportError}
                />
              ) : (
                <ComparativeAnalysisExport
                  bills={selectedBills}
                  analysisData={analysisData}
                  onExportStart={handleExportStart}
                  onExportComplete={handleExportComplete}
                  onExportError={handleExportError}
                />
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ExportDashboard;
