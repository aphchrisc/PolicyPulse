import React from "react";
import PropTypes from "prop-types";
import { formatDate } from "../../utils/helpers";
import { Link } from "react-router-dom";

/**
 * Table view for bills list (desktop display)
 * @param {Object} props
 * @param {Array} props.bills - List of bills to display
 */
const BillListTable = ({ bills }) => {
  if (!bills || bills.length === 0) {
    return (
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-700">
          <tr>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
            >
              Bill
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
            >
              Title
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
            >
              Jurisdiction
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
            >
              Status
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
            >
              Updated
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
            >
              Sponsor
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
          <tr>
            <td
              colSpan="6"
              className="px-6 py-4 text-center text-gray-500 dark:text-gray-400"
            >
              No bills found matching your criteria.
            </td>
          </tr>
        </tbody>
      </table>
    );
  }

  return (
    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
      <thead className="bg-gray-50 dark:bg-gray-700">
        <tr>
          <th
            scope="col"
            className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
          >
            Bill
          </th>
          <th
            scope="col"
            className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
          >
            Title
          </th>
          <th
            scope="col"
            className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
          >
            Jurisdiction
          </th>
          <th
            scope="col"
            className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
          >
            Status
          </th>
          <th
            scope="col"
            className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
          >
            Updated
          </th>
          <th
            scope="col"
            className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
          >
            Sponsor
          </th>
        </tr>
      </thead>
      <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
        {bills.map((bill) => (
          <tr key={bill.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
              <Link
                to={`/bills/${bill.id}`}
                className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
              >
                {bill.bill_number || bill.bill_id || `#${bill.id}`}
              </Link>
            </td>
            <td className="px-6 py-4 whitespace-nowrap text-sm">
              <Link
                to={`/bills/${bill.id}`}
                className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                title={bill.description || bill.title}
              >
                {bill.title}
              </Link>
            </td>
            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
              {getJurisdictionDisplay(bill)}
            </td>
            <td className="px-6 py-4 whitespace-nowrap text-sm">
              <span
                className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                  ${getStatusColor(bill.bill_status || bill.status)}`}
              >
                {bill.bill_status || bill.status || "Unknown"}
              </span>
            </td>
            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
              {bill.updated_at
                ? formatDate(bill.updated_at)
                : bill.last_action_date
                ? formatDate(bill.last_action_date)
                : "Unknown"}
            </td>
            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
              {getSponsorDisplay(bill)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

/**
 * Get display value for jurisdiction, checking multiple possible field names
 * @param {Object} bill - The bill object
 * @returns {string} The jurisdiction display text
 */
const getJurisdictionDisplay = (bill) => {
  // Handle the case where bill might be a string (raw JSON)
  if (typeof bill === "string") {
    try {
      const parsedBill = JSON.parse(bill);
      return getJurisdictionDisplay(parsedBill);
    } catch (e) {
      return "Unknown";
    }
  }

  // Direct check for jurisdiction field
  if (typeof bill?.jurisdiction === "string" && bill.jurisdiction.trim())
    return bill.jurisdiction;

  // Check various possible field names for jurisdiction information
  if (typeof bill?.govt_source === "string" && bill.govt_source.trim())
    return bill.govt_source;

  if (typeof bill?.state === "string" && bill.state.trim()) return bill.state;

  if (typeof bill?.govt_type === "string" && bill.govt_type.trim())
    return bill.govt_type;

  // If we have a bill_number, try to extract a jurisdiction prefix
  if (typeof bill?.bill_number === "string" && bill.bill_number.includes("-")) {
    const parts = bill.bill_number.split("-");
    if (parts.length > 1) return parts[parts.length - 1];
  }

  return "Unknown";
};

/**
 * Process sponsor information and return a display string
 * @param {Object} bill - The bill with sponsor information
 * @returns {string} Formatted sponsor display text
 */
const getSponsorDisplay = (bill) => {
  // Handle the case where bill might be a string (raw JSON)
  if (typeof bill === "string") {
    try {
      const parsedBill = JSON.parse(bill);
      return getSponsorDisplay(parsedBill);
    } catch (e) {
      return "Unknown";
    }
  }

  if (bill?.sponsor) {
    return bill.sponsor;
  }

  if (bill?.sponsors && bill.sponsors.length > 0) {
    if (typeof bill.sponsors[0] === "string") {
      return bill.sponsors[0];
    }

    if (typeof bill.sponsors[0] === "object" && bill.sponsors[0]?.name) {
      return bill.sponsors[0].name;
    }
  }

  return "Unknown";
};

/**
 * Return the appropriate CSS classes for a status badge
 * @param {string} status - The bill status
 * @returns {string} CSS classes for the status badge
 */
const getStatusColor = (status) => {
  // Handle undefined or null
  if (!status) {
    return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
  }

  // Handle case where status might be an object with a value property
  if (typeof status === "object") {
    if (status.value) {
      status = status.value;
    } else {
      return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
    }
  }

  // Convert to lowercase string for consistency
  const statusLower = status.toString().toLowerCase();

  if (statusLower.includes("introduced")) {
    return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300";
  } else if (statusLower.includes("committee")) {
    return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300";
  } else if (statusLower.includes("passed")) {
    return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
  } else if (
    statusLower.includes("enacted") ||
    statusLower.includes("signed")
  ) {
    return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
  } else if (statusLower.includes("vetoed") || statusLower.includes("failed")) {
    return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300";
  } else if (statusLower.includes("vote")) {
    return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300";
  } else if (statusLower.includes("updated")) {
    return "bg-gray-500 text-white dark:bg-gray-600";
  }

  return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
};

BillListTable.propTypes = {
  bills: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      title: PropTypes.string.isRequired,
      bill_number: PropTypes.string,
      bill_id: PropTypes.string,
      jurisdiction: PropTypes.string,
      govt_source: PropTypes.string,
      state: PropTypes.string,
      govt_type: PropTypes.string,
      status: PropTypes.string,
      bill_status: PropTypes.string,
      updated_at: PropTypes.string,
      last_action_date: PropTypes.string,
      sponsor: PropTypes.string,
      sponsors: PropTypes.oneOfType([
        PropTypes.arrayOf(PropTypes.string),
        PropTypes.arrayOf(
          PropTypes.shape({
            name: PropTypes.string,
            party: PropTypes.string,
            role: PropTypes.string,
          })
        ),
      ]),
      description: PropTypes.string,
    })
  ),
};

BillListTable.defaultProps = {
  bills: [],
};

export default BillListTable;
