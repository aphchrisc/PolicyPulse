import React, { useState } from "react";
import { useBookmarks } from "../context/BookmarkContext";
import BookmarkManager from "../components/bookmarks/BookmarkManager";
import { jsPDF } from "jspdf";
import html2canvas from "html2canvas";
import Breadcrumbs from "../components/navigation/Breadcrumbs";
import logger from "../utils/logger";

/**
 * Page component for displaying and managing bookmarked bills
 */
const BookmarksPage = () => {
  const { bookmarkedBills, removeBookmark, clearBookmarks } = useBookmarks();

  const [exportStatus, setExportStatus] = useState({
    isExporting: false,
    message: "",
    isError: false,
  });

  /**
   * Export bookmarked bills as PDF
   * @param {Array} bills - The bills to export
   */
  const handleExportBookmarks = async (bills) => {
    if (!bills || bills.length === 0) {
      setExportStatus({
        isExporting: false,
        message: "No bills to export",
        isError: true,
      });
      return;
    }

    try {
      setExportStatus({
        isExporting: true,
        message: "Generating PDF...",
        isError: false,
      });

      // Create a temporary div to render the report content
      const reportContainer = document.createElement("div");
      reportContainer.className = "pdf-report";
      reportContainer.style.width = "8.5in";
      reportContainer.style.padding = "0.5in";
      reportContainer.style.fontFamily = "Arial, sans-serif";
      reportContainer.style.position = "absolute";
      reportContainer.style.left = "-9999px";
      document.body.appendChild(reportContainer);

      // Generate report content
      reportContainer.innerHTML = `
        <div style="text-align: center; margin-bottom: 20px;">
          <h1 style="color: #2563eb; font-size: 24px; margin-bottom: 5px;">Bookmarked Bills</h1>
          <p style="color: #64748b; font-size: 14px;">Generated on ${new Date().toLocaleDateString()}</p>
        </div>
        
        <div style="margin-bottom: 20px;">
          <p>This report contains ${bills.length} bookmarked bill${
        bills.length !== 1 ? "s" : ""
      }.</p>
        </div>
      `;

      // Add each bill to the report
      bills.forEach((bill, index) => {
        reportContainer.innerHTML += `
          <div style="margin-bottom: 30px; ${
            index > 0 ? "border-top: 1px solid #e2e8f0; padding-top: 20px;" : ""
          }">
            <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">${
              bill.title || `Bill #${bill.id}`
            }</h2>
            
            <div style="margin-bottom: 10px;">
              <p><strong>ID:</strong> ${bill.id || "N/A"}</p>
              <p><strong>Status:</strong> ${bill.status || "N/A"}</p>
              <p><strong>Introduced:</strong> ${
                bill.introduced_date || bill.introduced || "N/A"
              }</p>
              ${
                bill.lastAction
                  ? `<p><strong>Last Action:</strong> ${bill.lastAction}</p>`
                  : ""
              }
            </div>
            
            ${
              bill.description
                ? `
              <div style="margin-bottom: 10px;">
                <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px;">Description</h3>
                <p>${bill.description}</p>
              </div>
            `
                : ""
            }
            
            ${
              bill.analysis?.summary
                ? `
              <div style="margin-bottom: 10px;">
                <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px;">Summary</h3>
                <p>${bill.analysis.summary}</p>
              </div>
            `
                : ""
            }
            
            ${
              bill.analysis?.impact_summary
                ? `
              <div style="margin-bottom: 10px;">
                <h3 style="color: #475569; font-size: 16px; margin-bottom: 5px;">Impact</h3>
                <p><strong>Primary Category:</strong> ${
                  bill.analysis.impact_summary.primary_category?.replace(
                    "_",
                    " "
                  ) || "Not specified"
                }</p>
                <p><strong>Impact Level:</strong> ${
                  bill.analysis.impact_summary.impact_level || "Not specified"
                }</p>
                <p><strong>Relevance to Texas:</strong> ${
                  bill.analysis.impact_summary.relevance_to_texas ||
                  "Not specified"
                }</p>
              </div>
            `
                : ""
            }
            
            <div style="margin-top: 10px; font-size: 12px; color: #64748b;">
              <p>Bookmarked on ${new Date(
                bill.bookmarkedAt
              ).toLocaleDateString()}</p>
            </div>
          </div>
        `;
      });

      // Add footer
      reportContainer.innerHTML += `
        <div style="margin-top: 30px; text-align: center; font-size: 12px; color: #64748b;">
          <p>Generated by PolicyPulse | ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}</p>
        </div>
      `;

      // Create PDF
      const pdf = new jsPDF({
        format: "letter",
        orientation: "portrait",
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
      const fileName = `bookmarked_bills_${
        new Date().toISOString().split("T")[0]
      }.pdf`;
      pdf.save(fileName);

      // Clean up
      document.body.removeChild(reportContainer);

      setExportStatus({
        isExporting: false,
        message: "PDF exported successfully!",
        isError: false,
      });

      // Clear message after 3 seconds
      setTimeout(() => {
        setExportStatus((prev) => ({
          ...prev,
          message: "",
        }));
      }, 3000);
    } catch (error) {
      logger.error("Error exporting bookmarks", { error });
      setExportStatus({
        isExporting: false,
        message: `Export failed: ${error.message || "Unknown error"}`,
        isError: true,
      });
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <Breadcrumbs
        crumbs={[
          { path: "/", label: "Home" },
          { path: "/bookmarks", label: "Bookmarks", isLast: true },
        ]}
      />

      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Bookmarked Bills
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Manage your saved bills and export them for reference
        </p>
      </div>

      {exportStatus.message && (
        <div
          className={`mb-6 p-4 rounded-md ${
            exportStatus.isError
              ? "bg-red-50 border-l-4 border-red-500 text-red-700 dark:bg-red-900/20 dark:text-red-400"
              : "bg-green-50 border-l-4 border-green-500 text-green-700 dark:bg-green-900/20 dark:text-green-400"
          }`}
        >
          <p>{exportStatus.message}</p>
        </div>
      )}

      <BookmarkManager
        bookmarkedBills={bookmarkedBills}
        onRemoveBookmark={removeBookmark}
        onClearBookmarks={clearBookmarks}
        onExportBookmarks={handleExportBookmarks}
      />

      {bookmarkedBills.length === 0 && (
        <div className="mt-8 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            You haven't bookmarked any bills yet. Browse the legislation and
            bookmark bills to save them for later reference.
          </p>
        </div>
      )}
    </div>
  );
};

export default BookmarksPage;
