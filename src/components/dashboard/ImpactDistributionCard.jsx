import React from "react";
import PropTypes from "prop-types";
import Card from "../ui/Card";
import { ChartIcon } from "../icons/DashboardIcons";
import LoadingSpinner from "./common/LoadingSpinner";

/**
 * Impact level distribution chart for the dashboard
 *
 * @param {Object} props - Component props
 * @param {Object} props.data - Impact distribution data
 * @param {boolean} props.loading - Loading state
 * @returns {JSX.Element} ImpactDistributionCard component
 */
const ImpactDistributionCard = ({ data, loading }) => {
  return (
    <Card title="Impact Level Distribution" icon={<ChartIcon />}>
      {loading ? (
        <div className="flex justify-center py-8">
          <LoadingSpinner size="sm" />
        </div>
      ) : (
        <div className="h-80">
          <div className="w-full h-full flex flex-col justify-center items-center">
            <div className="relative w-64 h-64">
              {/* Simple pie chart */}
              {data && (
                <svg viewBox="0 0 100 100" className="w-full h-full">
                  {(() => {
                    // Calculate the total number of bills
                    const highImpact = data.high_impact || 0;
                    const mediumImpact = data.medium_impact || 0;
                    const lowImpact = data.low_impact || 0;
                    const total = highImpact + mediumImpact + lowImpact;

                    // Calculate percentages
                    const highPercentage = (highImpact / total) * 100;
                    const mediumPercentage = (mediumImpact / total) * 100;
                    const lowPercentage = (lowImpact / total) * 100;

                    // Calculate the circumference of the circle
                    const circumference = 2 * Math.PI * 25;

                    // Calculate the arc length for each segment
                    const highArc = (highPercentage / 100) * circumference;
                    const mediumArc = (mediumPercentage / 100) * circumference;
                    const lowArc = (lowPercentage / 100) * circumference;

                    // Calculate strokeDashoffset for each segment
                    const highOffset = 0;
                    const mediumOffset = -highArc;
                    const lowOffset = -(highArc + mediumArc);

                    return (
                      <>
                        {/* High Impact slice */}
                        <circle
                          cx="50"
                          cy="50"
                          r="25"
                          fill="transparent"
                          stroke="#FF5252"
                          strokeWidth="50"
                          strokeDasharray={`${highArc} ${circumference}`}
                          strokeDashoffset={highOffset}
                          transform="rotate(-90 50 50)"
                        />
                        {/* Medium Impact slice */}
                        <circle
                          cx="50"
                          cy="50"
                          r="25"
                          fill="transparent"
                          stroke="#FFB74D"
                          strokeWidth="50"
                          strokeDasharray={`${mediumArc} ${circumference}`}
                          strokeDashoffset={mediumOffset}
                          transform="rotate(-90 50 50)"
                        />
                        {/* Low Impact slice */}
                        <circle
                          cx="50"
                          cy="50"
                          r="25"
                          fill="transparent"
                          stroke="#4CAF50"
                          strokeWidth="50"
                          strokeDasharray={`${lowArc} ${circumference}`}
                          strokeDashoffset={lowOffset}
                          transform="rotate(-90 50 50)"
                        />
                        <circle
                          cx="50"
                          cy="50"
                          r="12.5"
                          fill="white"
                          className="dark:fill-gray-800"
                        />
                      </>
                    );
                  })()}
                </svg>
              )}
            </div>

            {/* Legend */}
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="flex items-center">
                <div className="w-4 h-4 rounded-full bg-[#FF5252] mr-2"></div>
                <span className="text-sm">
                  High (
                  {data
                    ? `${Math.round(
                        (data.high_impact /
                          (data.high_impact +
                            data.medium_impact +
                            data.low_impact)) *
                          100
                      )}%`
                    : "0%"}
                  )
                </span>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 rounded-full bg-[#FFB74D] mr-2"></div>
                <span className="text-sm">
                  Medium (
                  {data
                    ? `${Math.round(
                        (data.medium_impact /
                          (data.high_impact +
                            data.medium_impact +
                            data.low_impact)) *
                          100
                      )}%`
                    : "0%"}
                  )
                </span>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 rounded-full bg-[#4CAF50] mr-2"></div>
                <span className="text-sm">
                  Low (
                  {data
                    ? `${Math.round(
                        (data.low_impact /
                          (data.high_impact +
                            data.medium_impact +
                            data.low_impact)) *
                          100
                      )}%`
                    : "0%"}
                  )
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};

ImpactDistributionCard.propTypes = {
  data: PropTypes.shape({
    high_impact: PropTypes.number,
    medium_impact: PropTypes.number,
    low_impact: PropTypes.number,
  }),
  loading: PropTypes.bool,
};

export default ImpactDistributionCard;
