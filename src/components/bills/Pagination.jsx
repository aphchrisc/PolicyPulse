import React from "react";
import PropTypes from "prop-types";

/**
 * Pagination component for navigating through results
 * @param {Object} props
 * @param {number} props.currentPage - Current page number
 * @param {number} props.limit - Number of items per page
 * @param {number} props.total - Total number of items
 * @param {Function} props.onPageChange - Handler for page changes
 */
const Pagination = ({ currentPage, limit, total, onPageChange }) => {
  // Calculate total pages
  const totalPages = Math.ceil(total / limit);

  // Calculate current range being displayed
  const startItem = total > 0 ? (currentPage - 1) * limit + 1 : 0;
  const endItem = Math.min(currentPage * limit, total);

  // Determine if navigation is possible
  const canGoPrevious = currentPage > 1;
  const canGoNext = currentPage < totalPages;

  // Handle page navigation
  const handlePrevious = () => {
    if (canGoPrevious) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (canGoNext) {
      onPageChange(currentPage + 1);
    }
  };

  // Generate page number buttons
  const getPageNumbers = () => {
    const pages = [];
    const maxVisiblePages = 5; // Number of page buttons to show

    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = startPage + maxVisiblePages - 1;

    if (endPage > totalPages) {
      endPage = totalPages;
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    // Add first page button if necessary
    if (startPage > 1) {
      pages.push(
        <button
          key="page-1"
          onClick={() => onPageChange(1)}
          className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600"
        >
          1
        </button>
      );

      // Add ellipsis if there's a gap
      if (startPage > 2) {
        pages.push(
          <span
            key="ellipsis-1"
            className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            ...
          </span>
        );
      }
    }

    // Add page number buttons
    for (let i = startPage; i <= endPage; i++) {
      pages.push(
        <button
          key={`page-${i}`}
          onClick={() => onPageChange(i)}
          className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
            i === currentPage
              ? "z-10 bg-blue-50 dark:bg-blue-900 border-blue-500 text-blue-600 dark:text-blue-300"
              : "bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600"
          }`}
        >
          {i}
        </button>
      );
    }

    // Add last page button if necessary
    if (endPage < totalPages) {
      // Add ellipsis if there's a gap
      if (endPage < totalPages - 1) {
        pages.push(
          <span
            key="ellipsis-2"
            className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            ...
          </span>
        );
      }

      pages.push(
        <button
          key={`page-${totalPages}`}
          onClick={() => onPageChange(totalPages)}
          className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600"
        >
          {totalPages}
        </button>
      );
    }

    return pages;
  };

  // Don't render pagination if there's only one page
  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
      {/* Mobile pagination */}
      <div className="flex-1 flex justify-between sm:hidden">
        <button
          onClick={handlePrevious}
          disabled={!canGoPrevious}
          className={`relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md ${
            !canGoPrevious
              ? "text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800"
              : "text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
          }`}
          aria-label="Previous page"
        >
          Previous
        </button>
        <div className="mx-2 flex items-center text-sm text-gray-700 dark:text-gray-300">
          <span className="font-medium">{currentPage}</span>
          <span className="mx-1">/</span>
          <span>{totalPages}</span>
        </div>
        <button
          onClick={handleNext}
          disabled={!canGoNext}
          className={`relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md ${
            !canGoNext
              ? "text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800"
              : "text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
          }`}
          aria-label="Next page"
        >
          Next
        </button>
      </div>

      {/* Desktop pagination */}
      <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            Showing <span className="font-medium">{startItem}</span> to{" "}
            <span className="font-medium">{endItem}</span> of{" "}
            <span className="font-medium">{total}</span> results
          </p>
        </div>
        <div>
          <nav
            className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
            aria-label="Pagination"
          >
            <button
              onClick={handlePrevious}
              disabled={!canGoPrevious}
              className={`relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 text-sm font-medium ${
                !canGoPrevious
                  ? "text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800"
                  : "text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
              }`}
              aria-label="Previous page"
            >
              <span className="sr-only">Previous</span>
              <svg
                className="h-5 w-5"
                width="20"
                height="20"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            </button>

            {/* Page number buttons */}
            {getPageNumbers()}

            <button
              onClick={handleNext}
              disabled={!canGoNext}
              className={`relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 dark:border-gray-600 text-sm font-medium ${
                !canGoNext
                  ? "text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800"
                  : "text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600"
              }`}
              aria-label="Next page"
            >
              <span className="sr-only">Next</span>
              <svg
                className="h-5 w-5"
                width="20"
                height="20"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </nav>
        </div>
      </div>
    </div>
  );
};

Pagination.propTypes = {
  currentPage: PropTypes.number.isRequired,
  limit: PropTypes.number.isRequired,
  total: PropTypes.number.isRequired,
  onPageChange: PropTypes.func.isRequired,
};

export default Pagination;
