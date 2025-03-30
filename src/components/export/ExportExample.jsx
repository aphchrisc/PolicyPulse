import React, { useState, useEffect } from "react";
import { billService } from "../../services/api";
import AnalysisExport from "./AnalysisExport";
import ComparativeAnalysisExport from "./ComparativeAnalysisExport";
import logger from "../../utils/logger";

/**
 * Example component to demonstrate PDF export functionality
 * This component loads sample data and shows how to use both export components
 */
const ExportExample = () => {
  const [sampleBill, setSampleBill] = useState(null);
  const [sampleAnalysis, setSampleAnalysis] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [exportStatus, setExportStatus] = useState("");
  const [showComparative, setShowComparative] = useState(false);

  // Load sample data on component mount
  useEffect(() => {
    const loadSampleData = async () => {
      try {
        setIsLoading(true);

        // Get a sample bill
        const billsResponse = await billService.searchBills({ limit: 1 });
        const bill = billsResponse.bills?.[0];

        if (bill) {
          setSampleBill(bill);

          // Get analysis for the sample bill
          const analysisResponse = await billService.getAnalysis(bill.id);
          const analysis = analysisResponse.analyses?.[0];

          if (analysis) {
            setSampleAnalysis(analysis);
          }
        }
      } catch (error) {
        logger.error("Error loading sample data:", error);
        setExportStatus("Failed to load sample data. Please try again later.");
      } finally {
        setIsLoading(false);
      }
    };

    loadSampleData();
  }, []);

  // Handle export start
  const handleExportStart = () => {
    setExportStatus("Generating PDF...");
  };

  // Handle export complete
  const handleExportComplete = (fileName) => {
    setExportStatus(`Export complete: ${fileName}`);
  };

  // Handle export error
  const handleExportError = (errorMessage) => {
    setExportStatus(`Export failed: ${errorMessage}`);
  };

  // Toggle between single and comparative export
  const toggleExportType = () => {
    setShowComparative(!showComparative);
  };

  // Create sample data for comparative analysis
  const getComparativeData = () => {
    if (!sampleBill || !sampleAnalysis) {
      return { bills: [], analysisData: [] };
    }

    // Create a modified copy of the sample bill and analysis for demonstration
    const secondBill = {
      ...sampleBill,
      id: `${sampleBill.id}-2`,
      title: `${sampleBill.title} (Alternative Version)`,
    };

    const secondAnalysis = {
      ...sampleAnalysis,
      impact_summary: {
        ...sampleAnalysis.impact_summary,
        impact_level:
          sampleAnalysis.impact_summary?.impact_level === "high"
            ? "moderate"
            : "high",
        primary_category:
          sampleAnalysis.impact_summary?.primary_category === "economic"
            ? "public_health"
            : "economic",
      },
    };

    return {
      bills: [sampleBill, secondBill],
      analysisData: [sampleAnalysis, secondAnalysis],
    };
  };

  const comparativeData = getComparativeData();

  return (
    <div className="container mx-auto p-4">
      <h2 className="text-2xl font-bold mb-6 text-gray-800 dark:text-gray-200">
        PDF Export Example
      </h2>

      <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">Export Type</h3>
        <button
          onClick={toggleExportType}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
        >
          {showComparative
            ? "Switch to Single Bill Export"
            : "Switch to Comparative Export"}
        </button>

        {exportStatus && (
          <div className="mt-4 p-3 bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300 rounded-md">
            {exportStatus}
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : sampleBill && sampleAnalysis ? (
        <div className="mb-6">
          {showComparative ? (
            <ComparativeAnalysisExport
              bills={comparativeData.bills}
              analysisData={comparativeData.analysisData}
              onExportStart={handleExportStart}
              onExportComplete={handleExportComplete}
              onExportError={handleExportError}
            />
          ) : (
            <AnalysisExport
              bill={sampleBill}
              analysisData={sampleAnalysis}
              onExportStart={handleExportStart}
              onExportComplete={handleExportComplete}
              onExportError={handleExportError}
            />
          )}
        </div>
      ) : (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-md text-yellow-700 dark:text-yellow-300">
          No sample data available. Please check your API connection.
        </div>
      )}

      <div className="mt-8 bg-gray-50 dark:bg-gray-800 rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">How to Use</h3>
        <div className="prose dark:prose-invert max-w-none">
          <p>
            This example demonstrates how to use the PDF export components in
            your application. There are two main components:
          </p>
          <ul>
            <li>
              <strong>AnalysisExport</strong> - For exporting a single bill
              analysis
            </li>
            <li>
              <strong>ComparativeAnalysisExport</strong> - For comparing and
              exporting multiple bills
            </li>
          </ul>
          <p>
            Both components use jsPDF and html2canvas to generate PDF reports
            with charts and visualizations. The PDFs include radar charts for
            impact analysis and other visualizations based on the bill data.
          </p>
          <h4 className="text-md font-semibold mt-4">
            Implementation Example:
          </h4>
          <pre className="bg-gray-100 dark:bg-gray-700 p-3 rounded-md overflow-x-auto">
            {`
// Single bill export
<AnalysisExport
  bill={billData}
  analysisData={analysisData}
  onExportStart={handleExportStart}
  onExportComplete={handleExportComplete}
  onExportError={handleExportError}
/>

// Comparative analysis export
<ComparativeAnalysisExport
  bills={[bill1, bill2, ...]}
  analysisData={[analysis1, analysis2, ...]}
  onExportStart={handleExportStart}
  onExportComplete={handleExportComplete}
  onExportError={handleExportError}
/>
            `}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default ExportExample;
