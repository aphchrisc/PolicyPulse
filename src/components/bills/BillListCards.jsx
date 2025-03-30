import React from "react";
import PropTypes from "prop-types";
import { formatDate } from "../../utils/helpers";

/**
 * Card view for bills list (mobile display)
 * @param {Object} props
 * @param {Array} props.bills - List of bills to display
 */
const BillListCards = ({ bills }) => {
  if (!bills || bills.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500 dark:text-gray-400">
        No bills found matching your criteria.
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-200 dark:divide-gray-700">
      {bills.map((bill) => (
        <div key={bill.id} className="p-4">
          <div className="font-medium text-gray-700 dark:text-gray-300 mb-1">
            {bill.bill_number || bill.bill_id || `Bill #${bill.id}`}
          </div>
          <h3 className="font-medium text-blue-600 dark:text-blue-400 mb-2">
            <a href={`/bills/${bill.id}`} className="hover:underline">
              {bill.title}
            </a>
          </h3>
          <div className="grid grid-cols-2 gap-2 text-sm mb-3">
            <div>
              <span className="text-gray-500 dark:text-gray-400">
                Jurisdiction:
              </span>
              <span className="ml-1 text-gray-700 dark:text-gray-300">
                {bill.jurisdiction || "Unknown"}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Status:</span>
              <span
                className={`ml-1 px-2 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full 
                  ${getStatusColor(bill.status)}`}
              >
                {bill.status || "Unknown"}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Updated:</span>
              <span className="ml-1 text-gray-700 dark:text-gray-300">
                {bill.updated_at
                  ? formatDate(bill.updated_at)
                  : bill.last_action_date
                  ? formatDate(bill.last_action_date)
                  : "Unknown"}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Sponsor:</span>
              <span className="ml-1 text-gray-700 dark:text-gray-300">
                {bill.sponsor || "Unknown"}
              </span>
            </div>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2 line-clamp-2">
            {bill.description || bill.summary || "No description available."}
          </p>
          <div className="flex justify-end">
            <a
              href={`/bills/${bill.id}`}
              className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
            >
              View Details →
            </a>
          </div>
        </div>
      ))}
    </div>
  );
};

/**
 * Return the appropriate CSS classes for a status badge
 * @param {string} status - The bill status
 * @returns {string} CSS classes for the status badge
 */
const getStatusColor = (status) => {
  if (!status)
    return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";

  switch (status.toLowerCase()) {
    case "introduced":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300";
    case "in committee":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300";
    case "passed committee":
      return "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300";
    case "floor vote scheduled":
      return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300";
    case "passed":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
    case "enacted":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
    case "vetoed":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
  }
};

BillListCards.propTypes = {
  bills: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      title: PropTypes.string.isRequired,
      bill_number: PropTypes.string,
      bill_id: PropTypes.string,
      jurisdiction: PropTypes.string,
      status: PropTypes.string,
      updated_at: PropTypes.string,
      last_action_date: PropTypes.string,
      sponsor: PropTypes.string,
      description: PropTypes.string,
      summary: PropTypes.string,
    })
  ),
};

BillListCards.defaultProps = {
  bills: [],
};

export default BillListCards;
