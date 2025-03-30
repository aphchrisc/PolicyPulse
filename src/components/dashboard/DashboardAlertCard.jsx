import React from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import ImpactBadge from "../ui/ImpactBadge";
import PrimaryImpactDisplay from "../ui/PrimaryImpactDisplay";
import { impactPropTypes } from "../../utils/propTypes";

/**
 * DashboardAlertCard - A component for displaying alert cards on the dashboard
 *
 * @param {Object} props - Component props
 * @param {string} props.id - The alert ID
 * @param {string} props.title - The alert title
 * @param {string} props.type - The alert type (bill, executive-order)
 * @param {string} props.impactLevel - The alert impact level
 * @param {string} props.date - The alert date
 * @param {string} props.description - The alert description
 * @param {string} props.impactDetails - The primary impact details
 * @param {Array} props.categories - The alert categories
 */
const DashboardAlertCard = ({
  id,
  title,
  type,
  impactLevel,
  date,
  description,
  impactDetails,
  categories = [],
}) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300">
      <div className="p-4">
        <div className="flex justify-between items-start">
          <div className="w-full">
            <div className="flex items-center gap-2 mb-2">
              <span
                className={`px-2 py-1 rounded-full text-xs font-semibold ${
                  type === "bill"
                    ? "bg-blue-100 text-blue-800"
                    : "bg-purple-100 text-purple-800"
                }`}
              >
                {type === "bill" ? "Bill" : "Executive Order"}
              </span>
              <ImpactBadge impact={impactLevel} />
              <span className="text-xs text-gray-500">
                {new Date(date).toLocaleDateString()}
              </span>
            </div>

            <div className="flex items-center flex-wrap gap-x-3 mb-2">
              <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
                <Link to={`/bills/${id}`} className="hover:underline">
                  {title}
                </Link>
              </h2>
              {impactDetails && (
                <PrimaryImpactDisplay impactDetails={impactDetails} />
              )}
            </div>

            <p className="text-gray-600 dark:text-gray-300 mb-3">
              {description}
            </p>

            {/* Display categories if available */}
            {categories.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {categories.map((category, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800"
                  >
                    {category}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="px-4 py-3 bg-gray-50 dark:bg-gray-700 border-t border-gray-100 dark:border-gray-600 flex justify-center items-center">
        <Link
          to={`/bills/${id}`}
          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium text-sm"
        >
          View Details →
        </Link>
      </div>
    </div>
  );
};

DashboardAlertCard.propTypes = {
  id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  title: PropTypes.string.isRequired,
  type: PropTypes.oneOf(["bill", "executive-order"]).isRequired,
  impactLevel: PropTypes.oneOf(["high", "medium", "low", "unknown"]).isRequired,
  date: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  impactDetails: PropTypes.shape({
    primaryCategory: PropTypes.string,
    level: PropTypes.string,
    details: PropTypes.string,
  }),
  categories: PropTypes.arrayOf(PropTypes.string),
};

DashboardAlertCard.defaultProps = {
  categories: [],
  impactDetails: null,
};

export default DashboardAlertCard;
