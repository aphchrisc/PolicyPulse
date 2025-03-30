import React from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import Card from "../ui/Card";
import { ClockIcon } from "../icons/DashboardIcons";
import { getStatusIcon, getStatusLabel } from "../icons/StatusIcons";
import LoadingSpinner from "./common/LoadingSpinner";

/**
 * Recent legislative activity card for the dashboard
 *
 * @param {Object} props - Component props
 * @param {Array} props.data - Array of recent bills data
 * @param {boolean} props.loading - Loading state
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} RecentActivityCard component
 */
const RecentActivityCard = ({ data, loading, className = "" }) => {
  return (
    <Card
      title="Recent Legislative Activity"
      icon={<ClockIcon />}
      className={className}
    >
      {loading ? (
        <div className="flex justify-center py-8">
          <LoadingSpinner size="sm" />
        </div>
      ) : (
        <div className="space-y-4">
          {data.map((bill) => (
            <div
              key={bill.id}
              className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 shadow-sm"
            >
              <h3 className="font-medium text-blue-600 dark:text-blue-400 mb-2">
                <Link to={`/bills/${bill.id}`} className="hover:underline">
                  {bill.title}
                </Link>
              </h3>
              <div className="grid grid-cols-2 gap-2 text-sm mb-2">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">
                    Jurisdiction:
                  </span>
                  <span className="ml-1 text-gray-700 dark:text-gray-300">
                    {bill.jurisdiction}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">
                    Date:
                  </span>
                  <span className="ml-1 text-gray-700 dark:text-gray-300">
                    {bill.date}
                  </span>
                </div>
              </div>
              <div className="mt-2">
                <div className="flex items-center mb-1.5">
                  <span className="text-gray-500 dark:text-gray-400 text-sm mr-2">
                    Status:
                  </span>
                  <div className="flex items-center">
                    {getStatusIcon(bill.status)}
                    <span className="ml-1.5 text-gray-700 dark:text-gray-300 text-sm">
                      {getStatusLabel(bill.status || "introduced")}
                    </span>
                  </div>
                </div>
                <span className="text-gray-500 dark:text-gray-400 text-sm">
                  Progress:
                </span>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mt-1 overflow-hidden">
                  <div
                    className="bg-blue-600 dark:bg-blue-500 h-2.5 rounded-full relative"
                    style={{ width: `${bill.progress}%` }}
                  >
                    {/* Status milestones */}
                    <div className="absolute inset-0 flex justify-between items-center px-1">
                      <div className="h-2 w-0.5 bg-gray-800/30 dark:bg-white/30"></div>
                      <div className="h-2 w-0.5 bg-gray-800/30 dark:bg-white/30"></div>
                      <div className="h-2 w-0.5 bg-gray-800/30 dark:bg-white/30"></div>
                      <div className="h-2 w-0.5 bg-gray-800/30 dark:bg-white/30"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
          <div className="text-center mt-4">
            <Link
              to="/bills"
              className="text-blue-600 dark:text-blue-400 hover:underline text-sm font-medium"
            >
              View All Bills →
            </Link>
          </div>
        </div>
      )}
    </Card>
  );
};

RecentActivityCard.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      title: PropTypes.string.isRequired,
      jurisdiction: PropTypes.string.isRequired,
      date: PropTypes.string.isRequired,
      progress: PropTypes.number.isRequired,
      status: PropTypes.string,
    })
  ).isRequired,
  loading: PropTypes.bool,
  className: PropTypes.string,
};

export default RecentActivityCard;
