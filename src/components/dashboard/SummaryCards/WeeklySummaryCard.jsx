import React from "react";
import Card from "../../ui/Card";
import { ChartIcon } from "../../icons/DashboardIcons";

/**
 * Weekly summary card displaying new bills count
 *
 * @returns {JSX.Element} WeeklySummaryCard component
 */
const WeeklySummaryCard = () => {
  return (
    <Card title="Weekly Summary" icon={<ChartIcon />}>
      <div className="text-center">
        <div className="text-4xl font-bold text-blue-600 dark:text-blue-400 mb-2">
          47
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          New Bills This Week
        </div>
        <div className="mt-4 flex items-center justify-center text-green-600 dark:text-green-400">
          <svg
            className="w-4 h-4 mr-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 10l7-7m0 0l7 7m-7-7v18"
            />
          </svg>
          <span className="text-sm font-medium">+3.5%</span>
        </div>
      </div>
    </Card>
  );
};

export default WeeklySummaryCard;
