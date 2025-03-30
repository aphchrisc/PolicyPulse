import React from "react";
import PropTypes from "prop-types";
import Card from "../ui/Card";
import { BarChartIcon } from "../icons/DashboardIcons";
import TrendingTopicsChart from "../visualizations/TrendingTopicsChart";
import LoadingSpinner from "./common/LoadingSpinner";

/**
 * Trending topics visualization card for the dashboard
 *
 * @param {Object} props - Component props
 * @param {Array} props.data - Array of trending terms data
 * @param {boolean} props.loading - Loading state
 * @returns {JSX.Element} TrendingTopicsCard component
 */
const TrendingTopicsCard = ({ data, loading }) => {
  return (
    <Card title="Trending Legislative Topics" icon={<BarChartIcon />}>
      {loading ? (
        <div className="flex justify-center py-8">
          <LoadingSpinner size="sm" />
        </div>
      ) : (
        <div className="h-80">
          <TrendingTopicsChart
            data={data.map((term) => ({
              name: term.text,
              count: term.value,
            }))}
            limit={8}
          />
        </div>
      )}
    </Card>
  );
};

TrendingTopicsCard.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      text: PropTypes.string.isRequired,
      value: PropTypes.number.isRequired,
    })
  ).isRequired,
  loading: PropTypes.bool,
};

export default TrendingTopicsCard;
