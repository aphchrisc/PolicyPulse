import React from "react";
import PropTypes from "prop-types";

/**
 * Filters component for legislation
 * @param {Object} props
 * @param {Object} props.filters - Current filter state
 * @param {Function} props.setFilters - Function to update filters
 * @param {Object} props.filterOptions - Filter options from API data
 */
const BillFilters = ({ filters, setFilters, filterOptions }) => {
  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters({ ...filters, [name]: value });
  };

  return (
    <div className="flex flex-wrap gap-2 mb-4">
      <select
        name="jurisdiction"
        className="p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
        value={filters.jurisdiction}
        onChange={handleFilterChange}
        aria-label="Filter by jurisdiction"
      >
        <option value="all">All Jurisdictions</option>
        {/* Default jurisdictions */}
        <option value="U.S. Congress">U.S. Congress</option>
        <option value="Texas">Texas</option>
        <option value="California">California</option>
        <option value="New York">New York</option>

        {/* Dynamic jurisdictions from API data */}
        {filterOptions.jurisdictions &&
          filterOptions.jurisdictions
            .filter(
              (j) =>
                !["U.S. Congress", "Texas", "California", "New York"].includes(
                  j
                )
            )
            .map((jurisdiction) => (
              <option key={jurisdiction} value={jurisdiction}>
                {jurisdiction}
              </option>
            ))}
      </select>

      <select
        name="status"
        className="p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
        value={filters.status}
        onChange={handleFilterChange}
        aria-label="Filter by status"
      >
        <option value="all">All Statuses</option>
        {/* Default statuses */}
        <option value="Introduced">Introduced</option>
        <option value="In Committee">In Committee</option>
        <option value="Passed Committee">Passed Committee</option>
        <option value="Floor Vote Scheduled">Floor Vote Scheduled</option>
        <option value="Passed">Passed</option>
        <option value="Enacted">Enacted</option>
        <option value="Vetoed">Vetoed</option>

        {/* Dynamic statuses from API data */}
        {filterOptions.statuses &&
          filterOptions.statuses
            .filter(
              (s) =>
                ![
                  "Introduced",
                  "In Committee",
                  "Passed Committee",
                  "Floor Vote Scheduled",
                  "Passed",
                  "Enacted",
                  "Vetoed",
                ].includes(s)
            )
            .map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
      </select>

      <select
        name="dateRange"
        className="p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
        value={filters.dateRange}
        onChange={handleFilterChange}
        aria-label="Filter by date range"
      >
        <option value="all">All Dates</option>
        <option value="lastWeek">Last Week</option>
        <option value="lastMonth">Last Month</option>
        <option value="lastQuarter">Last Quarter</option>
        <option value="lastYear">Last Year</option>
        <option value="thisSession">This Legislative Session</option>
      </select>

      {filterOptions.subjects && filterOptions.subjects.length > 0 && (
        <select
          name="subject"
          className="p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          value={filters.subject || "all"}
          onChange={handleFilterChange}
          aria-label="Filter by subject"
        >
          <option value="all">All Subjects</option>
          {filterOptions.subjects.map((subject) => (
            <option key={subject} value={subject}>
              {subject}
            </option>
          ))}
        </select>
      )}

      <button
        className="p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-600"
        onClick={() =>
          setFilters({
            jurisdiction: "all",
            status: "all",
            dateRange: "all",
            subject: "all",
          })
        }
        aria-label="Reset filters"
      >
        Reset Filters
      </button>
    </div>
  );
};

BillFilters.propTypes = {
  filters: PropTypes.shape({
    jurisdiction: PropTypes.string.isRequired,
    status: PropTypes.string.isRequired,
    dateRange: PropTypes.string.isRequired,
    subject: PropTypes.string,
  }).isRequired,
  setFilters: PropTypes.func.isRequired,
  filterOptions: PropTypes.shape({
    jurisdictions: PropTypes.arrayOf(PropTypes.string),
    statuses: PropTypes.arrayOf(PropTypes.string),
    subjects: PropTypes.arrayOf(PropTypes.string),
  }),
};

BillFilters.defaultProps = {
  filterOptions: {
    jurisdictions: [],
    statuses: [],
    subjects: [],
  },
};

export default BillFilters;
