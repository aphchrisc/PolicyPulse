import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { getLegislationById, fetchLegislationAnalysis } from "../services/api";
import AnalysisDashboard from "../components/analysis/AnalysisDashboard";
import VisualizationDashboard from "../components/visualizations/VisualizationDashboard";
import BookmarkButton from "../components/bookmarks/BookmarkButton";
import AnalysisExport from "../components/export/AnalysisExport";
import { useNotification } from "../context/NotificationContext";
import Breadcrumbs from "../components/navigation/Breadcrumbs";
import ImpactScoreChart from "../components/analysis/ImpactScoreChart";
import logger from "../utils/logger";

// Add this function at the top of the file, outside the component
function sanitizeHTML(html) {
  // Simple version - in production, use a library like DOMPurify
  if (!html) return "";
  return html
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function BillDetail() {
  const { billId } = useParams();
  const navigate = useNavigate();
  const [bill, setBill] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [similarBills, setSimilarBills] = useState([]);
  const [showExportPanel, setShowExportPanel] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const { addNotification } = useNotification();

  useEffect(() => {
    const fetchBillDetail = async () => {
      if (!billId) {
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const response = await getLegislationById(billId);

        if (!response || !response.data) {
          throw new Error("No data received from the server");
        }

        // Normalize the bill data to account for field name inconsistencies
        const normalizedBill = normalizeData(response.data);
        logger.info(
          "Normalized bill data (before analysis check):",
          normalizedBill
        ); // <-- ADDED LOG
        setBill(normalizedBill);

        // If bill has no analysis data, fetch it separately
        if (
          !normalizedBill.analysis ||
          Object.keys(normalizedBill.analysis).length === 0
        ) {
          try {
            setAnalysisLoading(true);
            const analysisResponse = await fetchLegislationAnalysis(billId);
            if (analysisResponse && analysisResponse.data) {
              normalizedBill.analysis = analysisResponse.data;
              setBill({ ...normalizedBill });
            }
          } catch (analysisError) {
            logger.warn("Error fetching bill analysis", {
              error: analysisError,
            });
            // Don't fail the main view if analysis can't be loaded
          } finally {
            setAnalysisLoading(false);
          }
        }

        setLoading(false);

        // Fetch similar bills if available
        if (
          normalizedBill.similarBills &&
          Array.isArray(normalizedBill.similarBills) &&
          normalizedBill.similarBills.length > 0
        ) {
          try {
            const similarBillsData = await Promise.all(
              normalizedBill.similarBills.map((id) => getLegislationById(id))
            );

            // Normalize each similar bill's data
            const normalizedSimilarBills = similarBillsData
              .filter((res) => res && res.data)
              .map((res) => normalizeData(res.data));

            setSimilarBills(normalizedSimilarBills);
          } catch (err) {
            logger.warn("Error fetching similar bills", { error: err });
            // Don't fail the main view if similar bills can't be loaded
          }
        }
      } catch (err) {
        logger.error("Error fetching bill", { error: err, billId });

        // Check for validation errors and show a more helpful message
        if (err.message && err.message.includes("ResponseValidationError")) {
          setError(
            "There was a problem with the bill data format. Our team has been notified and is working on a fix."
          );

          // Log the error in more detail for debugging
          logger.error("API Response Validation Error:", {
            error: err.message,
            details: err.originalError?.response?.data || {},
          });
        } else {
          setError(
            err.message ||
              "Failed to load bill details. Please try again later."
          );
        }

        setLoading(false);
      }
    };

    fetchBillDetail();
  }, [billId]);

  /**
   * Normalize bill data to handle inconsistent field names
   * @param {Object} data - The raw bill data from API
   * @returns {Object} Normalized bill data with consistent field names
   */
  const normalizeData = (data) => {
    if (!data) return null;

    // Handle case where data might be a string (raw JSON)
    if (typeof data === "string") {
      try {
        data = JSON.parse(data);
      } catch (e) {
        logger.error("Failed to parse bill data as JSON", { error: e });
        return null;
      }
    }

    // Create a copy to avoid mutating the original
    const normalized = { ...data };

    // Handle jurisdiction field
    if (!normalized.jurisdiction) {
      if (normalized.govt_source)
        normalized.jurisdiction = normalized.govt_source;
      else if (normalized.state) normalized.jurisdiction = normalized.state;
      else if (normalized.govt_type)
        normalized.jurisdiction = normalized.govt_type;
      else normalized.jurisdiction = "Unknown";
    }

    // Handle status field
    if (!normalized.bill_status) {
      if (normalized.status) normalized.bill_status = normalized.status;
      else normalized.bill_status = "Unknown";
    }

    // Handle sponsor field
    if (
      !normalized.sponsor &&
      normalized.sponsors &&
      normalized.sponsors.length > 0
    ) {
      if (typeof normalized.sponsors[0] === "string") {
        normalized.sponsor = normalized.sponsors[0];
      } else if (
        typeof normalized.sponsors[0] === "object" &&
        normalized.sponsors[0].name
      ) {
        normalized.sponsor = normalized.sponsors[0].name;
      } else {
        normalized.sponsor = "Unknown";
      }
    } else if (!normalized.sponsor) {
      normalized.sponsor = "Unknown";
    }

    // Ensure required fields have defaults
    normalized.bill_number = normalized.bill_number || `Bill #${normalized.id}`;
    normalized.title = normalized.title || `Untitled Bill #${normalized.id}`;
    normalized.description =
      normalized.description || "No description available";

    // Ensure all required nested objects exist
    if (!normalized.latest_text || typeof normalized.latest_text !== "object") {
      normalized.latest_text = { text: "No text available" };
    }

    if (!normalized.analysis || typeof normalized.analysis !== "object") {
      normalized.analysis = {};
    }

    return normalized;
  };

  const handleRetry = () => {
    // Reset state and try again
    setError(null);
    setLoading(true);
    navigate(0); // Refresh the page
  };

  // This is a new function to properly render bill text
  const renderBillText = (text) => {
    if (!text) return <p>No text available.</p>;

    // Check if the text appears to be HTML
    const isHTML = text.trim().startsWith("<") && text.includes(">");

    if (isHTML) {
      // For HTML content, we'll use dangerouslySetInnerHTML
      // In a production app, you should use a proper sanitizer like DOMPurify
      return (
        <div
          className="prose prose-sm max-w-none text-gray-700"
          dangerouslySetInnerHTML={{ __html: text }}
        />
      );
    }

    // For plain text, preserve whitespace
    return (
      <pre className="whitespace-pre-wrap text-gray-700 font-sans text-sm">
        {text}
      </pre>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-l-4 border-red-500 p-4">
        <div className="flex flex-col">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-500"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
          <div className="mt-4 text-center">
            <button
              onClick={handleRetry}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Try Again
            </button>
            <button
              onClick={() => navigate("/bills")}
              className="ml-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Back to Bills
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!bill) {
    return (
      <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-yellow-500"
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
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              Bill information is not available. Please try a different bill.
            </p>
            <button
              onClick={() => navigate("/bills")}
              className="mt-2 text-sm text-blue-600 hover:text-blue-800"
            >
              Return to Bills List
            </button>
          </div>
        </div>
      </div>
    );
  }

  // For the breadcrumbs to show the right information
  return (
    <div className="container mx-auto px-4 py-8">
      <Breadcrumbs
        items={[
          { label: "Home", path: "/" },
          { label: "Bills", path: "/bills" },
          { label: bill.bill_number || `Bill ${billId}`, path: null },
        ]}
      />

      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {bill.bill_number} - {bill.title}
          </h1>
          <div className="mt-2 flex flex-wrap gap-2">
            {bill.jurisdiction && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Jurisdiction: {bill.jurisdiction}
              </span>
            )}
            {bill.bill_status && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Status: {bill.bill_status}
              </span>
            )}
            {bill.sponsor && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                Sponsor: {bill.sponsor}
              </span>
            )}
          </div>
        </div>
        <div className="flex space-x-2">
          <BookmarkButton
            bill={{
              id: bill.id,
              title: bill.title,
            }}
            size="md"
            showText={false}
            className="text-gray-500 hover:text-blue-500"
          />
          <button
            onClick={() => setShowExportPanel(!showExportPanel)}
            className="text-gray-500 hover:text-blue-500"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
          </button>
        </div>
      </div>

      {showExportPanel && (
        <AnalysisExport
          billId={bill.id}
          billTitle={bill.title}
          billNumber={bill.bill_number}
          analysisData={bill.analysis}
          onClose={() => setShowExportPanel(false)}
          onError={handleExportError}
          onComplete={handleExportComplete}
          onStart={handleExportStart}
        />
      )}

      <div className="grid grid-cols-1 gap-8">
        {/* Bill Summary */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-5 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Bill Summary</h3>
          </div>
          <div className="px-6 py-5">
            <p className="text-gray-700">
              {bill.description || bill.summary || "No summary available."}
            </p>
          </div>
        </div>

        {/* Bill Text */}
        {bill.latest_text && (
          <div className="bg-white shadow rounded-lg mb-8">
            <div className="px-6 py-5 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Bill Text</h3>
            </div>
            <div className="px-6 py-5 overflow-x-auto max-h-[500px]">
              {renderBillText(
                bill.latest_text.text || bill.latest_text.text_content
              )}
            </div>
          </div>
        )}

        {/* Bill Analysis */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-5 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center">
              AI Analysis
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800 relative group cursor-help">
                <svg
                  className="h-3 w-3 mr-1"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z"
                    clipRule="evenodd"
                  />
                </svg>
                AI-powered
                <span className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs bg-gray-800 text-white rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none w-max">
                  AI Analysis performed by OpenAI ChatGPT 4o
                  <span className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-800"></span>
                </span>
              </span>
            </h3>
          </div>
          <div className="px-6 py-5">
            {analysisLoading ? (
              <div className="flex justify-center items-center py-4">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-600"></div>
                <span className="ml-2">Loading analysis data...</span>
              </div>
            ) : bill.analysis &&
              bill.analysis.status !== "pending" &&
              bill.analysis.id ? (
              <AnalysisDashboard analysisData={bill.analysis} />
            ) : (
              <div className="text-center py-8 bg-gray-50 rounded-lg">
                <p className="text-gray-500 text-lg mb-2">
                  No analysis available for this bill.
                </p>
                <p className="text-gray-400 text-sm">
                  Analysis data is being processed or is not available for this
                  legislation.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Visualizations */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-6 py-5 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center">
              AI Insights Visualizations
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                <svg
                  className="h-3 w-3 mr-1"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"
                    clipRule="evenodd"
                  />
                </svg>
                Interactive
              </span>
            </h3>
          </div>
          <div className="px-6 py-5 max-h-[600px]">
            {analysisLoading ? (
              <div className="flex justify-center items-center py-4">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-600"></div>
                <span className="ml-2">Loading analysis data...</span>
              </div>
            ) : (
              <VisualizationDashboard bill={bill} />
            )}
          </div>
        </div>

        {/* Bill Information Panel - wrap in a grid for better layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white shadow rounded-lg mb-6">
            <div className="px-6 py-5 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                Bill Information
              </h3>
            </div>
            <div className="px-6 py-5">
              <dl className="grid grid-cols-1 gap-4">
                <div>
                  <dt className="text-sm font-medium text-gray-500">
                    Bill Number
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {bill.bill_number || bill.bill_id || "Unknown"}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Status</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusClass(
                        bill.bill_status
                      )}`}
                    >
                      {bill.bill_status || "Unknown"}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">
                    Jurisdiction
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {bill.jurisdiction || "Unknown"}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">
                    Introduced
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {bill.introduced_date || bill.bill_introduced_date
                      ? new Date(
                          bill.introduced_date || bill.bill_introduced_date
                        ).toLocaleDateString()
                      : "Unknown"}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">
                    Last Updated
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {bill.updated_at || bill.bill_last_action_date
                      ? new Date(
                          bill.updated_at || bill.bill_last_action_date
                        ).toLocaleDateString()
                      : "Unknown"}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">
                    Sponsors
                  </dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {bill.sponsors && bill.sponsors.length > 0
                      ? bill.sponsors
                          .map((sponsor) =>
                            typeof sponsor === "string"
                              ? sponsor
                              : sponsor.name || "Unknown"
                          )
                          .join(", ")
                      : bill.sponsor || "Unknown"}
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          {/* Similar Bills Panel */}
          {similarBills.length > 0 && (
            <div className="bg-white shadow rounded-lg mb-6">
              <div className="px-6 py-5 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">
                  Similar Bills
                </h3>
              </div>
              <div className="px-6 py-5">
                <ul className="divide-y divide-gray-200">
                  {similarBills.map((similarBill) => (
                    <li key={similarBill.id} className="py-4">
                      <Link
                        to={`/bills/${similarBill.id}`}
                        className="block hover:bg-gray-50"
                      >
                        <div className="flex items-center space-x-4">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-blue-600 truncate">
                              {similarBill.bill_number ||
                                similarBill.bill_id ||
                                `#${similarBill.id}`}
                            </p>
                            <p className="text-sm text-gray-500 truncate">
                              {similarBill.title}
                            </p>
                          </div>
                          <div>
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusClass(
                                similarBill.bill_status
                              )}`}
                            >
                              {similarBill.bill_status || "Unknown"}
                            </span>
                          </div>
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  function handleExportStart() {
    addNotification({
      type: "info",
      message: "Preparing export...",
      duration: 3000,
    });
  }

  function handleExportComplete(fileName) {
    addNotification({
      type: "success",
      message: `Export completed: ${fileName}`,
      duration: 5000,
    });
    setShowExportPanel(false);
  }

  function handleExportError(errorMessage) {
    addNotification({
      type: "error",
      message: `Export failed: ${errorMessage}`,
      duration: 5000,
    });
  }

  function getStatusClass(status) {
    if (!status) return "bg-gray-100 text-gray-800";

    status = status.toLowerCase();
    if (
      status.includes("passed") ||
      status.includes("enacted") ||
      status.includes("signed")
    )
      return "bg-green-100 text-green-800";
    if (status.includes("introduced")) return "bg-blue-100 text-blue-800";
    if (status.includes("committee")) return "bg-yellow-100 text-yellow-800";
    if (status.includes("vetoed") || status.includes("failed"))
      return "bg-red-100 text-red-800";
    if (status.includes("updated")) return "bg-gray-500 text-white";

    return "bg-gray-100 text-gray-800";
  }
}

export default BillDetail;
