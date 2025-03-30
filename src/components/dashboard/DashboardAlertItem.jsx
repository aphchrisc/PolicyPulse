import React from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";
import ImpactBadge from "../ui/ImpactBadge";
import PrimaryImpactDisplay from "../ui/PrimaryImpactDisplay";

/**
 * A streamlined component for displaying alerts on the dashboard
 *
 * @param {Object} props - Component props
 * @param {Object} props.alert - Alert data
 * @returns {JSX.Element} Alert item component
 */
const DashboardAlertItem = ({ alert }) => {
  const { id, title, type, impactLevel, impactDetails } = alert;

  return (
    <div className="mb-4 border-b border-gray-100 dark:border-gray-700 pb-4 last:border-0 last:pb-0">
      <div className="flex flex-wrap items-center gap-2 mb-1.5">
        <span
          className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${
            type === "bill"
              ? "bg-blue-100 text-blue-800"
              : "bg-purple-100 text-purple-800"
          }`}
        >
          {type === "bill" ? "Bill" : "Executive Order"}
        </span>
        <ImpactBadge impact={impactLevel} size="sm" />
      </div>

      <div className="flex items-center flex-wrap gap-x-2">
        <h3 className="text-base font-medium text-blue-600 dark:text-blue-400">
          <Link to={`/bills/${id}`} className="hover:underline">
            {title}
          </Link>
        </h3>
        {impactDetails && (
          <PrimaryImpactDisplay impactDetails={impactDetails} />
        )}
      </div>
    </div>
  );
};

// PropTypes validation
DashboardAlertItem.propTypes = {
  alert: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    title: PropTypes.string.isRequired,
    type: PropTypes.string.isRequired,
    impactLevel: PropTypes.string.isRequired,
    impactDetails: PropTypes.object,
  }).isRequired,
};

export default DashboardAlertItem;
