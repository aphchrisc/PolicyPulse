import React from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";
import Card from "../ui/Card";
import { AlertIcon } from "../icons/DashboardIcons";
import DashboardAlertItem from "./DashboardAlertItem";
import LoadingSpinner from "./common/LoadingSpinner";

/**
 * High Impact Alerts section for the dashboard
 *
 * @param {Object} props - Component props
 * @param {Array} props.alerts - List of alerts to display
 * @param {boolean} props.loading - Loading state
 * @returns {JSX.Element} HighImpactAlerts component
 */
const HighImpactAlerts = ({ alerts, loading }) => {
  return (
    <div className="mt-6">
      <Card title="High Impact Alerts" icon={<AlertIcon />}>
        {loading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="sm" />
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {alerts.slice(0, 3).map((alert) => (
              <DashboardAlertItem key={alert.id} alert={alert} />
            ))}
            {alerts.length > 3 && (
              <div className="pt-4 text-center">
                <Link
                  to="/alerts"
                  className="inline-flex items-center text-blue-600 dark:text-blue-400 hover:underline"
                >
                  View all {alerts.length} alerts
                  <svg
                    className="ml-1 w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </Link>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
};

HighImpactAlerts.propTypes = {
  alerts: PropTypes.array.isRequired,
  loading: PropTypes.bool,
};

export default HighImpactAlerts;
