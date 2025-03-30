import React from "react";
import PropTypes from "prop-types";
import Card from "../ui/Card";
import { ChatIcon } from "../icons/DashboardIcons";
import LoadingSpinner from "./common/LoadingSpinner";

/**
 * Key terms analysis card for the dashboard
 *
 * @param {Object} props - Component props
 * @param {Array} props.data - Array of key terms data
 * @param {boolean} props.loading - Loading state
 * @returns {JSX.Element} KeyTermsAnalysisCard component
 */
const KeyTermsAnalysisCard = ({ data, loading }) => {
  return (
    <Card title="Key Terms Analysis" icon={<ChatIcon />}>
      {loading ? (
        <div className="flex justify-center py-8">
          <LoadingSpinner size="sm" />
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 justify-center p-4 h-full">
          {data.map((term) => (
            <span
              key={`term-${term.text}`}
              className="inline-block px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200"
              style={{
                fontSize: `${Math.max(0.8, term.value / 10)}rem`,
                opacity: Math.max(0.5, term.value / 40),
              }}
            >
              {term.text}
            </span>
          ))}
        </div>
      )}
    </Card>
  );
};

KeyTermsAnalysisCard.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      text: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    })
  ).isRequired,
  loading: PropTypes.bool,
};

export default KeyTermsAnalysisCard;
