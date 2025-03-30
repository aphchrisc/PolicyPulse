import React, { useState, useRef } from "react";
import { jsPDF } from "jspdf";
import html2canvas from "html2canvas";
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
} from "chart.js";
import { Radar, Bar } from "react-chartjs-2";
import PropTypes from "prop-types";
import logger from "../../utils/logger";
import { billPropTypes, analysisPropTypes } from "../../utils/propTypes";

// Register Chart.js components
ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement
);

/**
 * Component for exporting comparative analysis of multiple bills as PDF
 *
 * @param {Object} props - Component props
 * @param {Array} props.bills - Array of bill data to compare
 * @param {Array} props.analysisData - Array of analysis data corresponding to bills
 * @param {Function} props.onExportStart - Callback when export starts
 * @param {Function} props.onExportComplete - Callback when export completes
 * @param {Function} props.onExportError - Callback when export fails
 */
const ComparativeAnalysisExport = ({
  bills,
  analysisData,
  onExportStart,
  onExportComplete,
  onExportError,
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [exportOptions, setExportOptions] = useState({
    includeRadarChart: true,
    includeBarChart: true,
    includeDetailedComparison: true,
    format: "letter",
    orientation: "landscape",
  });

  // Refs for chart components
  const radarChartRef = useRef(null);
  const barChartRef = useRef(null);

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

  // Convert impact levels to numeric scores for visualization
  const getImpactScore = (level) => {
    switch (level?.toLowerCase()) {
      case "critical":
        return 100;
      case "high":
        return 75;
      case "moderate":
        return 50;
      case "low":
        return 25;
      default:
        return 0;
    }
  };

  // Prepare radar chart data for comparative analysis
  const prepareRadarChartData = () => {
    if (!analysisData || analysisData.length === 0) {
      return null;
    }

    const datasets = analysisData.map((analysis, index) => {
      // Calculate impact scores for each category
      let publicHealthScore = analysis.public_health_impacts
        ? (analysis.public_health_impacts.direct_effects?.length +
            analysis.public_health_impacts.indirect_effects?.length) *
          10
        : 0;

      let localGovScore = analysis.local_government_impacts
        ? (analysis.local_government_impacts.administrative?.length +
            analysis.local_government_impacts.fiscal?.length +
            analysis.local_government_impacts.implementation?.length) *
          10
        : 0;

      let economicScore = analysis.economic_impacts
        ? (analysis.economic_impacts.direct_costs?.length +
            analysis.economic_impacts.economic_effects?.length +
            analysis.economic_impacts.benefits?.length +
            analysis.economic_impacts.long_term_impact?.length) *
          10
        : 0;

      let environmentalScore = analysis.environmental_impacts?.length * 20 || 0;
      let educationScore = analysis.education_impacts?.length * 20 || 0;
      let infrastructureScore =
        analysis.infrastructure_impacts?.length * 20 || 0;

      // Use impact_summary if available for more accurate scoring
      const impactLevel = getImpactScore(analysis.impact_summary?.impact_level);
      const primaryCategory = analysis.impact_summary?.primary_category;

      // Adjust the primary category score if available
      if (primaryCategory && impactLevel) {
        switch (primaryCategory) {
          case "public_health":
            publicHealthScore = Math.max(publicHealthScore, impactLevel);
            break;
          case "local_gov":
            localGovScore = Math.max(localGovScore, impactLevel);
            break;
          case "economic":
            economicScore = Math.max(economicScore, impactLevel);
            break;
          case "environmental":
            environmentalScore = Math.max(environmentalScore, impactLevel);
            break;
          case "education":
            educationScore = Math.max(educationScore, impactLevel);
            break;
          case "infrastructure":
            infrastructureScore = Math.max(infrastructureScore, impactLevel);
            break;
          default:
            break;
        }
      }

      // Cap scores at 100
      const normalizeScore = (score) => Math.min(Math.round(score), 100);

      // Generate a color based on index
      const colors = [
        "rgba(54, 162, 235, 0.2)", // blue
        "rgba(255, 99, 132, 0.2)", // red
        "rgba(75, 192, 192, 0.2)", // green
        "rgba(255, 159, 64, 0.2)", // orange
        "rgba(153, 102, 255, 0.2)", // purple
      ];

      const borderColors = [
        "rgba(54, 162, 235, 1)",
        "rgba(255, 99, 132, 1)",
        "rgba(75, 192, 192, 1)",
        "rgba(255, 159, 64, 1)",
        "rgba(153, 102, 255, 1)",
      ];

      const colorIndex = index % colors.length;

      return {
        label: bills[index]?.title || `Bill ${index + 1}`,
        data: [
          normalizeScore(publicHealthScore),
          normalizeScore(localGovScore),
          normalizeScore(economicScore),
          normalizeScore(environmentalScore),
          normalizeScore(educationScore),
          normalizeScore(infrastructureScore),
        ],
        backgroundColor: colors[colorIndex],
        borderColor: borderColors[colorIndex],
        borderWidth: 2,
        pointBackgroundColor: borderColors[colorIndex],
        pointBorderColor: "#fff",
        pointHoverBackgroundColor: "#fff",
        pointHoverBorderColor: borderColors[colorIndex],
      };
    });

    return {
      labels: [
        "Public Health",
        "Local Government",
        "Economic",
        "Environmental",
        "Education",
        "Infrastructure",
      ],
      datasets,
    };
  };

  // Prepare bar chart data for impact level comparison
  const prepareBarChartData = () => {
    if (!analysisData || analysisData.length === 0) {
      return null;
    }

    const labels = bills.map(
      (bill) => bill.title || `Bill ${bill.id || "Unknown"}`
    );

    // Get overall impact scores
    const data = analysisData.map((analysis) => {
      // Use impact_summary if available
      if (analysis.impact_summary?.impact_level) {
        return getImpactScore(analysis.impact_summary.impact_level);
      }

      // Otherwise calculate an average score from all categories
      const scores = [];
      if (analysis.public_health_impacts) {
        scores.push(
          analysis.public_health_impacts.direct_effects?.length * 10 || 0
        );
      }
      if (analysis.local_government_impacts) {
        scores.push(
          analysis.local_government_impacts.administrative?.length * 10 || 0
        );
      }
      if (analysis.economic_impacts) {
        scores.push(analysis.economic_impacts.direct_costs?.length * 10 || 0);
      }
      if (analysis.environmental_impacts) {
        scores.push(analysis.environmental_impacts.length * 20 || 0);
      }

      // Calculate average and normalize
      return scores.length > 0
        ? Math.min(
            Math.round(
              scores.reduce((sum, score) => sum + score, 0) / scores.length
            ),
            100
          )
        : 0;
    });

    // Generate colors based on impact scores
    const backgroundColor = data.map((score) => {
      if (score >= 75) {
        return "rgba(255, 99, 132, 0.7)";
      } // High/Critical - Red
      if (score >= 50) {
        return "rgba(255, 159, 64, 0.7)";
      } // Moderate - Orange
      return "rgba(75, 192, 192, 0.7)"; // Low - Green
    });

    const borderColor = data.map((score) => {
      if (score >= 75) {
        return "rgba(255, 99, 132, 1)";
      }
      if (score >= 50) {
        return "rgba(255, 159, 64, 1)";
      }
      return "rgba(75, 192, 192, 1)";
    });

    return {
      labels,
      datasets: [
        {
          label: "Overall Impact Score",
          data,
          backgroundColor,
          borderColor,
          borderWidth: 1,
        },
      ],
    };
  };

  const radarChartOptions = {
    scales: {
      r: {
        angleLines: {
          display: true,
        },
        suggestedMin: 0,
        suggestedMax: 100,
        ticks: {
          stepSize: 25,
        },
      },
    },
    plugins: {
      legend: {
        position: "top",
      },
      tooltip: {
        callbacks: {
          label: function (context) {
            return `${context.dataset.label}: ${context.raw}/100`;
          },
        },
      },
    },
    maintainAspectRatio: false,
  };

  const barChartOptions = {
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        title: {
          display: true,
          text: "Impact Score",
        },
      },
      x: {
        title: {
          display: true,
          text: "Bills",
        },
      },
    },
    plugins: {
      legend: {
        position: "top",
      },
      tooltip: {
        callbacks: {
          label: function (context) {
            const score = context.raw;
            let impactLevel = "Low";
            if (score >= 75) {
              impactLevel = "Critical";
            } else if (score >= 50) {
              impactLevel = "Moderate";
            } else if (score >= 25) {
              impactLevel = "Low";
            }
            return `Impact: ${impactLevel} (${score}/100)`;
          },
        },
      },
    },
    maintainAspectRatio: false,
  };

  const exportToPdf = async () => {
    if (
      !bills ||
      !analysisData ||
      bills.length === 0 ||
      analysisData.length === 0
    ) {
      if (onExportError) {
        onExportError("No bills or analysis data available");
      }
      return;
    }

    try {
      setIsExporting(true);
      if (onExportStart) {
        onExportStart();
      }

      // Capture charts as images if enabled
      let radarChartImg = null;
      let barChartImg = null;

      if (exportOptions.includeRadarChart && radarChartRef.current) {
        const radarCanvas = await html2canvas(radarChartRef.current, {
          scale: 2,
          useCORS: true,
          logging: false,
        });
        radarChartImg = radarCanvas.toDataURL("image/png");
      }

      if (exportOptions.includeBarChart && barChartRef.current) {
        const barCanvas = await html2canvas(barChartRef.current, {
          scale: 2,
          useCORS: true,
          logging: false,
        });
        barChartImg = barCanvas.toDataURL("image/png");
      }

      // Create a temporary div to render the report content
      const reportContainer = document.createElement("div");
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
          <h1 style="color: #2563eb; font-size: 24px; margin-bottom: 5px;">Comparative Bill Analysis</h1>
          <p style="color: #64748b; font-size: 14px;">Generated on ${new Date().toLocaleDateString()}</p>
        </div>
        
        <div style="margin-bottom: 20px; padding: 15px; background-color: #f8fafc; border-radius: 5px;">
          <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">Bills Compared</h2>
          <ul>
            ${bills
              .map(
                (bill) => `
              <li style="margin-bottom: 10px;">
                <strong>${bill.title || "Untitled Bill"}</strong> (ID: ${
                  bill.id || "N/A"
                })
                <br>
                <span style="font-size: 14px; color: #64748b;">Status: ${
                  bill.status || "Unknown"
                }</span>
              </li>
            `
              )
              .join("")}
          </ul>
        </div>
      `;

      // Add radar chart if available
      if (exportOptions.includeRadarChart && radarChartImg) {
        reportContainer.innerHTML += `
          <div style="margin-bottom: 30px; text-align: center;">
            <h2 style="color: #334155; font-size: 18px; margin-bottom: 15px;">Impact Category Comparison</h2>
            <img src="${radarChartImg}" style="max-width: 100%; height: auto;" />
            <p style="font-size: 14px; color: #64748b; margin-top: 10px;">
              This radar chart compares the impact of each bill across different policy categories.
              Higher scores indicate greater potential impact in that category.
            </p>
          </div>
        `;
      }

      // Add bar chart if available
      if (exportOptions.includeBarChart && barChartImg) {
        reportContainer.innerHTML += `
          <div style="margin-bottom: 30px; text-align: center;">
            <h2 style="color: #334155; font-size: 18px; margin-bottom: 15px;">Overall Impact Comparison</h2>
            <img src="${barChartImg}" style="max-width: 100%; height: auto;" />
            <p style="font-size: 14px; color: #64748b; margin-top: 10px;">
              This chart shows the overall impact score for each bill.
              <br>
              <span style="color: rgba(255, 99, 132, 1);">Red</span>: Critical impact (75-100)
              <span style="color: rgba(255, 159, 64, 1); margin-left: 10px;">Orange</span>: Moderate impact (50-74)
              <span style="color: rgba(75, 192, 192, 1); margin-left: 10px;">Green</span>: Low impact (0-49)
            </p>
          </div>
        `;
      }

      // Add detailed comparison if selected
      if (exportOptions.includeDetailedComparison) {
        reportContainer.innerHTML += `
          <div style="margin-bottom: 20px;">
            <h2 style="color: #334155; font-size: 18px; margin-bottom: 15px;">Detailed Comparison</h2>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
              <thead>
                <tr style="background-color: #f1f5f9;">
                  <th style="padding: 10px; text-align: left; border: 1px solid #e2e8f0;">Aspect</th>
                  ${bills
                    .map(
                      (bill) => `
                    <th style="padding: 10px; text-align: left; border: 1px solid #e2e8f0;">${
                      bill.title || `Bill ${bill.id || "Unknown"}`
                    }</th>
                  `
                    )
                    .join("")}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">Primary Impact</td>
                  ${analysisData
                    .map(
                      (analysis) => `
                    <td style="padding: 10px; border: 1px solid #e2e8f0;">
                      ${
                        analysis.impact_summary?.primary_category?.replace(
                          "_",
                          " "
                        ) || "Not specified"
                      }
                    </td>
                  `
                    )
                    .join("")}
                </tr>
                <tr>
                  <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">Impact Level</td>
                  ${analysisData
                    .map(
                      (analysis) => `
                    <td style="padding: 10px; border: 1px solid #e2e8f0;">
                      ${
                        analysis.impact_summary?.impact_level || "Not specified"
                      }
                    </td>
                  `
                    )
                    .join("")}
                </tr>
                <tr>
                  <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">Key Points</td>
                  ${analysisData
                    .map(
                      (analysis) => `
                    <td style="padding: 10px; border: 1px solid #e2e8f0;">
                      ${
                        analysis.key_points && analysis.key_points.length > 0
                          ? `<ul style="margin: 0; padding-left: 20px;">${analysis.key_points
                              .slice(0, 3)
                              .map(
                                (item) =>
                                  `<li style="margin-bottom: 5px;">${
                                    item.point || item
                                  }</li>`
                              )
                              .join("")}</ul>${
                              analysis.key_points.length > 3
                                ? '<p style="font-style: italic; margin-top: 5px;">...and more</p>'
                                : ""
                            }`
                          : "No key points available"
                      }
                    </td>
                  `
                    )
                    .join("")}
                </tr>
                <tr>
                  <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">Public Health Impact</td>
                  ${analysisData
                    .map(
                      (analysis) => `
                    <td style="padding: 10px; border: 1px solid #e2e8f0;">
                      ${
                        analysis.public_health_impacts?.direct_effects &&
                        analysis.public_health_impacts.direct_effects.length > 0
                          ? analysis.public_health_impacts.direct_effects[0]
                          : "No significant impact identified"
                      }
                    </td>
                  `
                    )
                    .join("")}
                </tr>
                <tr>
                  <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">Economic Impact</td>
                  ${analysisData
                    .map(
                      (analysis) => `
                    <td style="padding: 10px; border: 1px solid #e2e8f0;">
                      ${
                        analysis.economic_impacts?.direct_costs &&
                        analysis.economic_impacts.direct_costs.length > 0
                          ? analysis.economic_impacts.direct_costs[0]
                          : analysis.economic_impacts?.benefits &&
                            analysis.economic_impacts.benefits.length > 0
                          ? analysis.economic_impacts.benefits[0]
                          : "No significant impact identified"
                      }
                    </td>
                  `
                    )
                    .join("")}
                </tr>
              </tbody>
            </table>
          </div>
        `;
      }

      // Add recommendations section
      reportContainer.innerHTML += `
        <div style="margin-bottom: 20px;">
          <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">Comparative Analysis Conclusions</h2>
          <p>Based on the analysis of the compared bills:</p>
          <ul>
            ${analysisData
              .map((analysis, index) => {
                const bill = bills[index];
                const impactLevel =
                  analysis.impact_summary?.impact_level || "unknown";
                const primaryCategory =
                  analysis.impact_summary?.primary_category?.replace(
                    "_",
                    " "
                  ) || "multiple areas";

                return `
                <li style="margin-bottom: 10px;">
                  <strong>${
                    bill.title || `Bill ${bill.id || "Unknown"}`
                  }</strong> has a 
                  <span style="font-weight: bold; color: ${
                    impactLevel.toLowerCase() === "critical"
                      ? "#ef4444"
                      : impactLevel.toLowerCase() === "high"
                      ? "#f97316"
                      : impactLevel.toLowerCase() === "moderate"
                      ? "#f59e0b"
                      : "#10b981"
                  };">${impactLevel}</span> 
                  impact on ${primaryCategory}.
                  ${
                    analysis.summary
                      ? `<br><span style="font-style: italic;">"${analysis.summary.substring(
                          0,
                          100
                        )}${analysis.summary.length > 100 ? "..." : ""}"</span>`
                      : ""
                  }
                </li>
              `;
              })
              .join("")}
          </ul>
        </div>
      `;

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
      const fileName = `comparative_bill_analysis_${
        new Date().toISOString().split("T")[0]
      }.pdf`;
      pdf.save(fileName);

      // Clean up
      document.body.removeChild(reportContainer);
      setIsExporting(false);
      if (onExportComplete) {
        onExportComplete(fileName);
      }
    } catch (error) {
      logger.error("Error exporting PDF:", error);
      setIsExporting(false);
      if (onExportError) {
        onExportError(error.message || "Failed to export PDF");
      }
    }
  };

  // Prepare chart data
  const radarData = prepareRadarChartData();
  const barData = prepareBarChartData();

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-4">
        Export Comparative Analysis
      </h3>

      {/* Hidden chart components for capturing */}
      <div style={{ position: "absolute", left: "-9999px" }}>
        {radarData && (
          <div
            ref={radarChartRef}
            style={{
              width: "800px",
              height: "500px",
              background: "white",
              padding: "20px",
            }}
          >
            <h3
              style={{
                textAlign: "center",
                marginBottom: "20px",
                color: "#334155",
              }}
            >
              Impact Category Comparison
            </h3>
            <div style={{ height: "400px" }}>
              <Radar data={radarData} options={radarChartOptions} />
            </div>
          </div>
        )}

        {barData && (
          <div
            ref={barChartRef}
            style={{
              width: "800px",
              height: "500px",
              background: "white",
              padding: "20px",
            }}
          >
            <h3
              style={{
                textAlign: "center",
                marginBottom: "20px",
                color: "#334155",
              }}
            >
              Overall Impact Comparison
            </h3>
            <div style={{ height: "400px" }}>
              <Bar data={barData} options={barChartOptions} />
            </div>
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
                checked={exportOptions.includeRadarChart}
                onChange={() => handleOptionChange("includeRadarChart")}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              <span>Include radar chart comparison</span>
            </label>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportOptions.includeBarChart}
                onChange={() => handleOptionChange("includeBarChart")}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              <span>Include impact bar chart</span>
            </label>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={exportOptions.includeDetailedComparison}
                onChange={() => handleOptionChange("includeDetailedComparison")}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              <span>Include detailed comparison table</span>
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
            disabled={isExporting || !bills || bills.length === 0}
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
              "Export Comparative Analysis as PDF"
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

ComparativeAnalysisExport.propTypes = {
  bills: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      title: PropTypes.string,
      status: PropTypes.string,
      introduced_date: PropTypes.string,
    })
  ).isRequired,
  analysisData: PropTypes.arrayOf(PropTypes.object).isRequired,
  onExportStart: PropTypes.func,
  onExportComplete: PropTypes.func,
  onExportError: PropTypes.func,
};

ComparativeAnalysisExport.defaultProps = {
  onExportStart: () => {},
  onExportComplete: () => {},
  onExportError: () => {},
};

export default ComparativeAnalysisExport;
