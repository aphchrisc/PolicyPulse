import React, { useState, useRef } from "react";
import { jsPDF } from "jspdf";
import html2canvas from "html2canvas";
import ImpactScoreChart from "../analysis/ImpactScoreChart";
import BillTimeline from "../visualizations/BillTimeline";
import PropTypes from "prop-types";
import logger from "../../utils/logger";
import { billPropTypes, analysisPropTypes } from "../../utils/propTypes";

/**
 * Component for exporting bill analysis as PDF
 *
 * @param {Object} props - Component props
 * @param {Object} props.bill - The bill data
 * @param {Object} props.analysisData - The analysis data to export
 * @param {Function} props.onExportStart - Callback when export starts
 * @param {Function} props.onExportComplete - Callback when export completes
 * @param {Function} props.onExportError - Callback when export fails
 */
const AnalysisExport = ({
  bill,
  analysisData,
  onExportStart,
  onExportComplete,
  onExportError,
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [exportOptions, setExportOptions] = useState({
    includeFullText: false,
    includeCharts: true,
    includeRecommendations: true,
    includeImpactDetails: true,
    format: "letter", // 'letter' or 'a4'
    orientation: "portrait", // 'portrait' or 'landscape'
  });

  const handleOptionChange = (option) => {
    setExportOptions((prev) => ({
      ...prev,
      [option]: !prev[option],
    }));
  };

  const handleFormatChange = (e) => {
    setExportOptions((prev) => ({
      ...prev,
      format: e.target.value,
    }));
  };

  const handleOrientationChange = (e) => {
    setExportOptions((prev) => ({
      ...prev,
      orientation: e.target.value,
    }));
  };

  // Create refs for chart components
  const impactChartRef = useRef(null);
  const timelineRef = useRef(null);

  const exportToPdf = async () => {
    if (!bill || !analysisData) {
      if (onExportError) {
        onExportError("No bill or analysis data available");
      }
      return;
    }

    try {
      setIsExporting(true);
      if (onExportStart) {
        onExportStart();
      }

      // Capture charts as images if includeCharts is enabled
      let impactChartImg = null;
      let timelineImg = null;

      if (exportOptions.includeCharts) {
        if (impactChartRef.current) {
          const impactCanvas = await html2canvas(impactChartRef.current, {
            scale: 2,
            useCORS: true,
            logging: false,
          });
          impactChartImg = impactCanvas.toDataURL("image/png");
        }

        if (timelineRef.current) {
          const timelineCanvas = await html2canvas(timelineRef.current, {
            scale: 2,
            useCORS: true,
            logging: false,
          });
          timelineImg = timelineCanvas.toDataURL("image/png");
        }
      }

      // Create a temporary div to render the report content
      let reportContainer = null;
      try {
        reportContainer = document.createElement("div");
        reportContainer.className = "pdf-report";
        reportContainer.style.width =
          exportOptions.format === "letter"
            ? exportOptions.orientation === "portrait"
              ? "8.5in"
              : "11in"
            : exportOptions.orientation === "portrait"
            ? "210mm"
            : "297mm";
        reportContainer.style.padding = "0.5in";
        reportContainer.style.fontFamily = "Arial, sans-serif";
        reportContainer.style.position = "absolute";
        reportContainer.style.left = "-9999px";
        document.body.appendChild(reportContainer);

        // Generate report content
        reportContainer.innerHTML = `
        <div style="text-align: center; margin-bottom: 20px;">
          <h1 style="color: #2563eb; font-size: 24px; margin-bottom: 5px;">${
            bill.title || "Bill Analysis"
          }</h1>
          <p style="color: #64748b; font-size: 14px;">Generated on ${new Date().toLocaleDateString()}</p>
        </div>
        
        <div style="margin-bottom: 20px; padding: 15px; background-color: #f8fafc; border-radius: 5px;">
          <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">Bill Information</h2>
          <p><strong>ID:</strong> ${bill.id || "N/A"}</p>
          <p><strong>Status:</strong> ${bill.status || "N/A"}</p>
          <p><strong>Introduced:</strong> ${
            bill.introduced_date || bill.introduced || "N/A"
          }</p>
          <p><strong>Last Action:</strong> ${bill.lastAction || "N/A"}</p>
        </div>
        
        <div style="margin-bottom: 20px;">
          <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">Executive Summary</h2>
          <p>${analysisData.summary || "No summary available."}</p>
        </div>
        
        <div style="margin-bottom: 20px;">
          <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">Key Points</h2>
          ${
            analysisData.key_points && analysisData.key_points.length > 0
              ? `<ul>${analysisData.key_points
                  .map(
                    (item) =>
                      `<li style="margin-bottom: 5px; color: ${
                        item.impact_type === "positive"
                          ? "#15803d"
                          : item.impact_type === "negative"
                          ? "#b91c1c"
                          : "#525252"
                      };">${item.point}</li>`
                  )
                  .join("")}</ul>`
              : "<p>No key points available.</p>"
          }
        </div>
      `;

        // Add impact summary section
        if (analysisData.impact_summary) {
          reportContainer.innerHTML += `
          <div style="margin-bottom: 20px;">
            <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">Impact Summary</h2>
            <p><strong>Primary Category:</strong> ${
              analysisData.impact_summary.primary_category?.replace("_", " ") ||
              "Not specified"
            }</p>
            <p><strong>Impact Level:</strong> ${
              analysisData.impact_summary.impact_level || "Not specified"
            }</p>
            <p><strong>Relevance to Texas:</strong> ${
              analysisData.impact_summary.relevance_to_texas || "Not specified"
            }</p>
          </div>
        `;

          // Add impact chart image if available
          if (exportOptions.includeCharts && impactChartImg) {
            reportContainer.innerHTML += `
            <div style="margin-bottom: 20px; text-align: center;">
              <h3 style="color: #475569; font-size: 16px; margin-bottom: 10px;">Impact Analysis Chart</h3>
              <img src="${impactChartImg}" style="max-width: 100%; height: auto;" />
            </div>
          `;
          }
        }

        // Add impact details if selected
        if (exportOptions.includeImpactDetails) {
          // Public Health Impacts
          if (analysisData.public_health_impacts) {
            reportContainer.innerHTML += `
            <div style="margin-bottom: 20px;">
              <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">Public Health Impacts</h2>
              
              <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px;">Direct Effects</h3>
              ${
                analysisData.public_health_impacts.direct_effects &&
                analysisData.public_health_impacts.direct_effects.length > 0
                  ? `<ul>${analysisData.public_health_impacts.direct_effects
                      .map(
                        (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                      )
                      .join("")}</ul>`
                  : "<p>No direct effects identified.</p>"
              }
              
              <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px; margin-top: 10px;">Indirect Effects</h3>
              ${
                analysisData.public_health_impacts.indirect_effects &&
                analysisData.public_health_impacts.indirect_effects.length > 0
                  ? `<ul>${analysisData.public_health_impacts.indirect_effects
                      .map(
                        (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                      )
                      .join("")}</ul>`
                  : "<p>No indirect effects identified.</p>"
              }
              
              <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px; margin-top: 10px;">Vulnerable Populations</h3>
              ${
                analysisData.public_health_impacts.vulnerable_populations &&
                analysisData.public_health_impacts.vulnerable_populations
                  .length > 0
                  ? `<ul>${analysisData.public_health_impacts.vulnerable_populations
                      .map(
                        (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                      )
                      .join("")}</ul>`
                  : "<p>No vulnerable populations identified.</p>"
              }
            </div>
          `;
          }

          // Local Government Impacts
          if (analysisData.local_government_impacts) {
            reportContainer.innerHTML += `
            <div style="margin-bottom: 20px;">
              <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">Local Government Impacts</h2>
              
              <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px;">Administrative</h3>
              ${
                analysisData.local_government_impacts.administrative &&
                analysisData.local_government_impacts.administrative.length > 0
                  ? `<ul>${analysisData.local_government_impacts.administrative
                      .map(
                        (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                      )
                      .join("")}</ul>`
                  : "<p>No administrative impacts identified.</p>"
              }
              
              <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px; margin-top: 10px;">Fiscal</h3>
              ${
                analysisData.local_government_impacts.fiscal &&
                analysisData.local_government_impacts.fiscal.length > 0
                  ? `<ul>${analysisData.local_government_impacts.fiscal
                      .map(
                        (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                      )
                      .join("")}</ul>`
                  : "<p>No fiscal impacts identified.</p>"
              }
              
              <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px; margin-top: 10px;">Implementation</h3>
              ${
                analysisData.local_government_impacts.implementation &&
                analysisData.local_government_impacts.implementation.length > 0
                  ? `<ul>${analysisData.local_government_impacts.implementation
                      .map(
                        (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                      )
                      .join("")}</ul>`
                  : "<p>No implementation impacts identified.</p>"
              }
            </div>
          `;
          }

          // Economic Impacts
          if (analysisData.economic_impacts) {
            reportContainer.innerHTML += `
            <div style="margin-bottom: 20px;">
              <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">Economic Impacts</h2>
              
              <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px;">Direct Costs</h3>
              ${
                analysisData.economic_impacts.direct_costs &&
                analysisData.economic_impacts.direct_costs.length > 0
                  ? `<ul>${analysisData.economic_impacts.direct_costs
                      .map(
                        (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                      )
                      .join("")}</ul>`
                  : "<p>No direct costs identified.</p>"
              }
              
              <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px; margin-top: 10px;">Benefits</h3>
              ${
                analysisData.economic_impacts.benefits &&
                analysisData.economic_impacts.benefits.length > 0
                  ? `<ul>${analysisData.economic_impacts.benefits
                      .map(
                        (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                      )
                      .join("")}</ul>`
                  : "<p>No benefits identified.</p>"
              }
              
              <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px; margin-top: 10px;">Long-term Impact</h3>
              ${
                analysisData.economic_impacts.long_term_impact &&
                analysisData.economic_impacts.long_term_impact.length > 0
                  ? `<ul>${analysisData.economic_impacts.long_term_impact
                      .map(
                        (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                      )
                      .join("")}</ul>`
                  : "<p>No long-term impacts identified.</p>"
              }
            </div>
          `;
          }
        }

        // Add bill timeline if available
        if (
          exportOptions.includeCharts &&
          timelineImg &&
          bill.history &&
          bill.history.length > 0
        ) {
          reportContainer.innerHTML += `
          <div style="margin-bottom: 20px; text-align: center;">
            <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">Bill Timeline</h2>
            <img src="${timelineImg}" style="max-width: 100%; height: auto;" />
          </div>
        `;
        }

        // Add recommendations if selected
        if (exportOptions.includeRecommendations) {
          reportContainer.innerHTML += `
          <div style="margin-bottom: 20px;">
            <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">Recommended Actions</h2>
            ${
              analysisData.recommended_actions &&
              analysisData.recommended_actions.length > 0
                ? `<ul>${analysisData.recommended_actions
                    .map(
                      (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                    )
                    .join("")}</ul>`
                : "<p>No recommended actions identified.</p>"
            }
            
            <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px; margin-top: 15px;">Immediate Actions</h3>
            ${
              analysisData.immediate_actions &&
              analysisData.immediate_actions.length > 0
                ? `<ul>${analysisData.immediate_actions
                    .map(
                      (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                    )
                    .join("")}</ul>`
                : "<p>No immediate actions identified.</p>"
            }
            
            <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px; margin-top: 15px;">Resource Needs</h3>
            ${
              analysisData.resource_needs &&
              analysisData.resource_needs.length > 0
                ? `<ul>${analysisData.resource_needs
                    .map(
                      (item) => `<li style="margin-bottom: 5px;">${item}</li>`
                    )
                    .join("")}</ul>`
                : "<p>No resource needs identified.</p>"
            }
          </div>
        `;
        }

        // Add footer
        reportContainer.innerHTML += `
        <div style="margin-top: 30px; text-align: center; font-size: 12px; color: #64748b;">
          <p>Generated by PolicyPulse | ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}</p>
        </div>
      `;

        // Create PDF
        const pdf = new jsPDF({
          format: exportOptions.format,
          orientation: exportOptions.orientation,
          unit: "pt",
        });

        // Convert the HTML to canvas
        const canvas = await html2canvas(reportContainer, {
          scale: 2, // Higher scale for better quality
          useCORS: true,
          logging: false,
        });

        // Add the canvas to PDF
        const imgData = canvas.toDataURL("image/png");
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = pdf.internal.pageSize.getHeight();
        const ratio = canvas.width / canvas.height;
        const canvasWidth = pdfWidth;
        const canvasHeight = canvasWidth / ratio;

        let heightLeft = canvasHeight;
        let position = 0;

        // Add first page
        pdf.addImage(imgData, "PNG", 0, position, canvasWidth, canvasHeight);
        heightLeft -= pdfHeight;

        // Add additional pages if needed
        while (heightLeft > 0) {
          position = heightLeft - canvasHeight;
          pdf.addPage();
          pdf.addImage(imgData, "PNG", 0, position, canvasWidth, canvasHeight);
          heightLeft -= pdfHeight;
        }

        // Save the PDF
        const fileName = `${
          bill.title
            ? bill.title.replace(/[^a-z0-9]/gi, "_").toLowerCase()
            : "bill"
        }_analysis_${new Date().toISOString().split("T")[0]}.pdf`;
        pdf.save(fileName);

        setIsExporting(false);
        if (onExportComplete) {
          onExportComplete(fileName);
        }

        return fileName;
      } finally {
        // Clean up - ensure the temporary DOM element is always removed
        if (reportContainer && document.body.contains(reportContainer)) {
          try {
            document.body.removeChild(reportContainer);
          } catch (cleanupError) {
            logger.error("Error during cleanup:", cleanupError);
          }
        }
      }
    } catch (error) {
      logger.error("Error exporting PDF:", error);
      setIsExporting(false);
      if (onExportError) {
        onExportError(error.message || "Failed to export PDF");
      }
      throw error; // Re-throw to be caught by the finally block
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4">Export Analysis Report</h3>

      {/* Hidden chart components for capturing */}
      <div style={{ position: "absolute", left: "-9999px", width: "800px" }}>
        {analysisData && (
          <div ref={impactChartRef}>
            <ImpactScoreChart analysisData={analysisData} />
          </div>
        )}

        {bill && (
          <div ref={timelineRef}>
            <BillTimeline bill={bill} />
          </div>
        )}
      </div>

      <div className="space-y-4">
        <div>
          <h4 className="font-medium mb-2">Report Content</h4>
          <div className="space-y-2">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportOptions.includeFullText}
                onChange={() => handleOptionChange("includeFullText")}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              <span>Include full bill text</span>
            </label>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportOptions.includeCharts}
                onChange={() => handleOptionChange("includeCharts")}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              <span>Include charts and visualizations</span>
            </label>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportOptions.includeRecommendations}
                onChange={() => handleOptionChange("includeRecommendations")}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              <span>Include recommended actions</span>
            </label>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportOptions.includeImpactDetails}
                onChange={() => handleOptionChange("includeImpactDetails")}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              <span>Include detailed impact analysis</span>
            </label>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <h4 className="font-medium mb-2">Paper Size</h4>
            <select
              value={exportOptions.format}
              onChange={handleFormatChange}
              className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="letter">Letter (8.5&quot; x 11&quot;)</option>
              <option value="a4">A4 (210mm x 297mm)</option>
            </select>
          </div>

          <div>
            <h4 className="font-medium mb-2">Orientation</h4>
            <select
              value={exportOptions.orientation}
              onChange={handleOrientationChange}
              className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="portrait">Portrait</option>
              <option value="landscape">Landscape</option>
            </select>
          </div>
        </div>

        <div className="pt-4">
          <button
            onClick={exportToPdf}
            disabled={isExporting}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition dark:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isExporting ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
                Generating PDF...
              </span>
            ) : (
              "Export as PDF"
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

AnalysisExport.propTypes = {
  bill: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    title: PropTypes.string,
    status: PropTypes.string,
    introduced_date: PropTypes.string,
    introduced: PropTypes.string,
    lastAction: PropTypes.string,
    history: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string,
        action: PropTypes.string,
      })
    ),
  }).isRequired,
  analysisData: PropTypes.object,
  onExportStart: PropTypes.func,
  onExportComplete: PropTypes.func,
  onExportError: PropTypes.func,
};

AnalysisExport.defaultProps = {
  onExportStart: () => {},
  onExportComplete: () => {},
  onExportError: () => {},
};

export default AnalysisExport;
