import React, { useState } from "react";
import PropTypes from "prop-types";

/**
 * Search form component for finding legislation
 * @param {Object} props
 * @param {string} props.searchTerm - Current search term
 * @param {Function} props.setSearchTerm - Function to update search term
 * @param {Function} props.handleSearch - Search submission handler
 * @param {boolean} props.loading - Loading state
 * @param {boolean} props.showAdvanced - Whether to show advanced search options
 * @param {Function} props.toggleAdvanced - Function to toggle advanced search
 * @param {Object} props.advancedFilters - Advanced search filters
 * @param {Function} props.setAdvancedFilters - Function to update advanced filters
 * @param {Array} props.searchHistory - Previous search terms
 */
const BillSearch = ({
  searchTerm,
  setSearchTerm,
  handleSearch,
  loading,
  showAdvanced,
  toggleAdvanced,
  advancedFilters,
  setAdvancedFilters,
  searchHistory,
}) => {
  const [showHistory, setShowHistory] = useState(false);

  return (
    <div>
      <form onSubmit={handleSearch} className="mb-2">
        <div className="flex flex-col md:flex-row gap-4 mb-2">
          <div className="flex-1 relative">
            <input
              type="text"
              placeholder="Search bills by title, content, or sponsor..."
              className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              aria-label="Search bills"
            />
            {searchHistory && searchHistory.length > 0 && (
              <button
                type="button"
                className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                onClick={() => setShowHistory(!showHistory)}
                aria-label="Show search history"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>
            )}
            {showHistory && searchHistory && searchHistory.length > 0 && (
              <div className="absolute top-full left-0 right-0 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg z-10 mt-1">
                <ul className="py-1">
                  {searchHistory.map((term, index) => (
                    <li key={`${term}-${index}`}>
                      <button
                        type="button"
                        className="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700"
                        onClick={() => {
                          setSearchTerm(term);
                          setShowHistory(false);
                        }}
                      >
                        {term}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition dark:bg-blue-700 dark:hover:bg-blue-600"
            disabled={loading}
          >
            {loading ? "Searching..." : "Search"}
          </button>
          <button
            type="button"
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
            onClick={toggleAdvanced}
          >
            {showAdvanced ? "Simple Search" : "Advanced Search"}
          </button>
        </div>
      </form>

      {showAdvanced && (
        <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-md mb-4 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium mb-3">Advanced Search Options</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Bill Number
              </label>
              <input
                type="text"
                className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                value={advancedFilters.billNumber || ""}
                onChange={(e) =>
                  setAdvancedFilters({
                    ...advancedFilters,
                    billNumber: e.target.value,
                  })
                }
                placeholder="e.g. HR1234"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Sponsor
              </label>
              <input
                type="text"
                className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                value={advancedFilters.sponsor || ""}
                onChange={(e) =>
                  setAdvancedFilters({
                    ...advancedFilters,
                    sponsor: e.target.value,
                  })
                }
                placeholder="Sponsor name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Subject
              </label>
              <input
                type="text"
                className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                value={advancedFilters.subject || ""}
                onChange={(e) =>
                  setAdvancedFilters({
                    ...advancedFilters,
                    subject: e.target.value,
                  })
                }
                placeholder="e.g. Healthcare"
              />
            </div>
            <div className="md:col-span-2 lg:col-span-3">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Full-text Content Search
              </label>
              <textarea
                className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                value={advancedFilters.fullText || ""}
                onChange={(e) =>
                  setAdvancedFilters({
                    ...advancedFilters,
                    fullText: e.target.value,
                  })
                }
                placeholder="Search through the full text of bills"
                rows={3}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

BillSearch.propTypes = {
  searchTerm: PropTypes.string.isRequired,
  setSearchTerm: PropTypes.func.isRequired,
  handleSearch: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  showAdvanced: PropTypes.bool,
  toggleAdvanced: PropTypes.func,
  advancedFilters: PropTypes.object,
  setAdvancedFilters: PropTypes.func,
  searchHistory: PropTypes.arrayOf(PropTypes.string),
};

BillSearch.defaultProps = {
  loading: false,
  showAdvanced: false,
  toggleAdvanced: () => {},
  advancedFilters: {},
  setAdvancedFilters: () => {},
  searchHistory: [],
};

export default BillSearch;
