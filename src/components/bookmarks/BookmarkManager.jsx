import React, { useState, useEffect } from "react";
import { Link } from "react-router";
import ImpactBadge from "../ui/ImpactBadge";

/**
 * Component for managing bookmarked bills
 *
 * @param {Object} props - Component props
 * @param {Array} props.bookmarkedBills - List of bookmarked bills
 * @param {Function} props.onRemoveBookmark - Callback when a bookmark is removed
 * @param {Function} props.onClearBookmarks - Callback when all bookmarks are cleared
 * @param {Function} props.onExportBookmarks - Callback when bookmarks are exported
 * @param {string} props.className - Additional CSS classes
 */
const BookmarkManager = ({
  bookmarkedBills = [],
  onRemoveBookmark,
  onClearBookmarks,
  onExportBookmarks,
  className = "",
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [filteredBills, setFilteredBills] = useState(bookmarkedBills);
  const [sortOption, setSortOption] = useState("dateAdded");
  const [isExporting, setIsExporting] = useState(false);

  // Filter and sort bills when dependencies change
  useEffect(() => {
    let result = [...bookmarkedBills];

    // Apply search filter
    if (searchTerm) {
      const lowerCaseSearch = searchTerm.toLowerCase();
      result = result.filter(
        (bill) =>
          bill.title?.toLowerCase().includes(lowerCaseSearch) ||
          bill.description?.toLowerCase().includes(lowerCaseSearch) ||
          bill.id?.toString().toLowerCase().includes(lowerCaseSearch)
      );
    }

    // Apply sorting
    result.sort((a, b) => {
      switch (sortOption) {
        case "title":
          return (a.title || "").localeCompare(b.title || "");
        case "status":
          return (a.status || "").localeCompare(b.status || "");
        case "dateIntroduced":
          return (
            new Date(b.introduced_date || b.introduced || 0) -
            new Date(a.introduced_date || a.introduced || 0)
          );
        case "dateAdded":
        default:
          return new Date(b.bookmarkedAt || 0) - new Date(a.bookmarkedAt || 0);
      }
    });

    setFilteredBills(result);
  }, [bookmarkedBills, searchTerm, sortOption]);

  // Handle search input change
  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };

  // Handle sort option change
  const handleSortChange = (e) => {
    setSortOption(e.target.value);
  };

  // Handle export bookmarks
  const handleExportBookmarks = async () => {
    if (typeof onExportBookmarks === "function") {
      setIsExporting(true);
      try {
        await onExportBookmarks(filteredBills);
      } catch (error) {
        console.error("Error exporting bookmarks:", error);
      } finally {
        setIsExporting(false);
      }
    }
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow ${className}`}>
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold">Bookmarked Bills</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {bookmarkedBills.length}{" "}
          {bookmarkedBills.length === 1 ? "bill" : "bills"} saved for later
          reference
        </p>
      </div>

      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search bookmarked bills..."
              value={searchTerm}
              onChange={handleSearchChange}
              className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>

          <div className="w-full md:w-48">
            <select
              value={sortOption}
              onChange={handleSortChange}
              className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="dateAdded">Sort by Date Added</option>
              <option value="title">Sort by Title</option>
              <option value="status">Sort by Status</option>
              <option value="dateIntroduced">Sort by Date Introduced</option>
            </select>
          </div>
        </div>
      </div>

      {filteredBills.length > 0 ? (
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {filteredBills.map((bill) => (
            <div
              key={bill.id}
              className="p-4 hover:bg-gray-50 dark:hover:bg-gray-750 transition"
            >
              <div className="flex flex-col md:flex-row md:items-center md:justify-between">
                <div className="flex-1">
                  <Link
                    to={`/bills/${bill.id}`}
                    className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
                  >
                    {bill.title}
                  </Link>

                  <div className="mt-1 flex flex-wrap gap-2">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
                      {bill.status || "Unknown Status"}
                    </span>

                    {bill.analysis?.impact_summary?.impact_level && (
                      <ImpactBadge
                        impact={bill.analysis.impact_summary.impact_level}
                        size="sm"
                      />
                    )}

                    {bill.analysis?.impact_summary?.primary_category && (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400">
                        {bill.analysis.impact_summary.primary_category.replace(
                          "_",
                          " "
                        )}
                      </span>
                    )}
                  </div>

                  {bill.description && (
                    <p className="mt-2 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                      {bill.description}
                    </p>
                  )}

                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                    Bookmarked on{" "}
                    {new Date(bill.bookmarkedAt).toLocaleDateString()}
                  </div>
                </div>

                <div className="mt-4 md:mt-0 md:ml-4 flex items-center">
                  <button
                    onClick={() => onRemoveBookmark(bill.id)}
                    className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 text-sm font-medium flex items-center"
                  >
                    <svg
                      className="h-4 w-4 mr-1 inline-block flex-shrink-0"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Remove
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-8 text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400 inline-block flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1}
              d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
            No bookmarked bills
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {searchTerm
              ? "No bills match your search criteria."
              : "Start bookmarking bills to save them for later reference."}
          </p>
        </div>
      )}

      {bookmarkedBills.length > 0 && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row justify-between gap-2">
          <button
            onClick={onClearBookmarks}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
          >
            Clear All Bookmarks
          </button>

          <button
            onClick={handleExportBookmarks}
            disabled={isExporting || filteredBills.length === 0}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition dark:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isExporting ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline-block flex-shrink-0"
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
                Exporting...
              </span>
            ) : (
              "Export Bookmarks"
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default BookmarkManager;
