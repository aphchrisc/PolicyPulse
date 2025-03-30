import React, {
  createContext,
  useState,
  useContext,
  useEffect,
  useMemo,
} from "react";
import PropTypes from "prop-types";
import { jsPDF } from "jspdf";
import html2canvas from "html2canvas";
import logger from "../utils/logger";

// Create context
const BookmarkContext = createContext();

/**
 * Custom hook to use the bookmark context
 * @returns {Object} Bookmark context value
 */
export const useBookmarks = () => {
  const context = useContext(BookmarkContext);
  if (!context) {
    throw new Error("useBookmarks must be used within a BookmarkProvider");
  }
  return context;
};

/**
 * Provider component for managing bookmarked bills
 *
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components
 */
export const BookmarkProvider = ({ children }) => {
  // Initialize state from localStorage if available
  const [bookmarkedBills, setBookmarkedBills] = useState(() => {
    try {
      const storedBookmarks = localStorage.getItem("bookmarkedBills");
      return storedBookmarks ? JSON.parse(storedBookmarks) : [];
    } catch (error) {
      logger.error("Error loading bookmarks from localStorage:", error);
      return [];
    }
  });

  // Save bookmarks to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem("bookmarkedBills", JSON.stringify(bookmarkedBills));
    } catch (error) {
      logger.error("Error saving bookmarks to localStorage:", error);
    }
  }, [bookmarkedBills]);

  /**
   * Add a bill to bookmarks
   * @param {Object} bill - The bill to bookmark
   */
  const addBookmark = (bill) => {
    if (!bill?.id) {
      logger.error("Cannot bookmark bill: Invalid bill data");
      return;
    }

    setBookmarkedBills((prevBookmarks) => {
      // Check if bill is already bookmarked
      if (prevBookmarks.some((b) => b.id === bill.id)) {
        return prevBookmarks;
      }

      // Add bookmark with timestamp
      return [
        ...prevBookmarks,
        {
          ...bill,
          bookmarkedAt: new Date().toISOString(),
        },
      ];
    });
  };

  /**
   * Remove a bill from bookmarks
   * @param {string|number} billId - The ID of the bill to remove
   */
  const removeBookmark = (billId) => {
    if (!billId) {
      logger.error("Cannot remove bookmark: Invalid bill ID");
      return;
    }

    setBookmarkedBills((prevBookmarks) =>
      prevBookmarks.filter((bill) => bill.id !== billId)
    );
  };

  /**
   * Check if a bill is bookmarked
   * @param {string|number} billId - The ID of the bill to check
   * @returns {boolean} True if the bill is bookmarked
   */
  const isBookmarked = (billId) => {
    return bookmarkedBills.some((bill) => bill.id === billId);
  };

  /**
   * Toggle bookmark status for a bill
   * @param {Object} bill - The bill to toggle bookmark for
   */
  const toggleBookmark = (bill) => {
    if (!bill?.id) {
      logger.error("Cannot toggle bookmark: Invalid bill data");
      return;
    }

    if (isBookmarked(bill.id)) {
      removeBookmark(bill.id);
    } else {
      addBookmark(bill);
    }
  };

  /**
   * Clear all bookmarks
   */
  const clearBookmarks = () => {
    setBookmarkedBills([]);
  };

  /**
   * Export bookmarks as PDF
   * @param {Array} bills - The bills to export (defaults to all bookmarked bills)
   * @returns {Promise} - Promise that resolves when export is complete
   */
  const exportBookmarks = async (bills = bookmarkedBills) => {
    if (!bills || bills.length === 0) {
      return Promise.reject(new Error("No bookmarks to export"));
    }

    try {
      logger.info("Exporting bookmarks:", bills);

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
          <p>Total bookmarks: ${bills.length}</p>
        </div>
      `;

      // Add each bill to the report
      bills.forEach((bill, index) => {
        reportContainer.innerHTML += `
          <div style="margin-bottom: 20px; padding: 15px; background-color: ${
            index % 2 === 0 ? "#f8fafc" : "#fff"
          }; border-radius: 5px; border: 1px solid #e2e8f0;">
            <h2 style="color: #334155; font-size: 18px; margin-bottom: 10px;">${
              bill.title || "Untitled Bill"
            }</h2>
            <p><strong>ID:</strong> ${bill.id || "N/A"}</p>
            <p><strong>Status:</strong> ${bill.status || "N/A"}</p>
            <p><strong>Introduced:</strong> ${
              bill.introduced_date || bill.introduced || "N/A"
            }</p>
            <p><strong>Last Action:</strong> ${bill.lastAction || "N/A"}</p>
            <p><strong>Bookmarked:</strong> ${new Date(
              bill.bookmarkedAt
            ).toLocaleString()}</p>
            ${
              bill.description
                ? `<p><strong>Description:</strong> ${bill.description}</p>`
                : ""
            }
          </div>
        `;
      });

      // Add footer
      reportContainer.innerHTML += `
        <div style="margin-top: 30px; text-align: center; font-size: 12px; color: #64748b;">
          <p>Generated by PolicyPulse | ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}</p>
        </div>
      `;

      try {
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

        return {
          success: true,
          message: "Bookmarks exported successfully",
          fileName,
        };
      } catch (error) {
        // Clean up in case of error
        if (document.body.contains(reportContainer)) {
          document.body.removeChild(reportContainer);
        }
        throw error;
      }
    } catch (error) {
      logger.error("Error exporting bookmarks:", error);
      return Promise.reject(
        new Error(`Failed to export bookmarks: ${error.message}`)
      );
    }
  };

  // Context value wrapped in useMemo to prevent unnecessary re-renders
  const value = useMemo(
    () => ({
      bookmarkedBills,
      addBookmark,
      removeBookmark,
      isBookmarked,
      toggleBookmark,
      clearBookmarks,
      exportBookmarks,
    }),
    [
      bookmarkedBills,
      // No dependencies needed for the functions as they're defined inside the component
      // and will maintain reference stability through renders
    ]
  );

  return (
    <BookmarkContext.Provider value={value}>
      {children}
    </BookmarkContext.Provider>
  );
};

export default BookmarkContext;

// Add PropTypes at the end of the file
BookmarkProvider.propTypes = {
  children: PropTypes.node.isRequired,
};
