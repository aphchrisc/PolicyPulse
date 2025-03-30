import React, { useMemo } from "react";
import PropTypes from "prop-types";
import { Radar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from "chart.js";
import logger from "../../utils/logger";
import { analysisPropTypes, uiPropTypes } from "../../utils/propTypes";

// Register Chart.js components
ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

/**
 * Component to visualize impact scores across different categories using a radar chart
 *
 * @param {Object} props - Component props
 * @param {Object} props.analysisData - The analysis data containing impact information
 * @param {string} props.className - Additional CSS classes
 */
const ImpactScoreChart = ({ analysisData, className = "" }) => {
  // Convert impact levels to numeric scores for visualization
  const getImpactScore = (level) => {
    switch (level?.toLowerCase()) {
      case "critical":
        return 100;
      case "high":
        return 75;
      case "moderate":
        return 50;
      case "low":
        return 25;
      default:
        return 0;
    }
  };

  // Extract impact data from analysis with proper error handling
  const chartData = useMemo(() => {
    // Early return if no data
    if (!analysisData) {
      return null;
    }

    try {
      // Safely get array length with null/undefined checks
      const safeArrayLength = (arr) => (Array.isArray(arr) ? arr.length : 0);

      // Safely access nested properties
      const safeGet = (obj, path, defaultValue = 0) => {
        try {
          const result = path
            .split(".")
            .reduce(
              (o, key) => (o && o[key] !== undefined ? o[key] : null),
              obj
            );
          return result !== null ? result : defaultValue;
        } catch (e) {
          logger.warn(`Error accessing path ${path}:`, e);
          return defaultValue;
        }
      };

      // Calculate impact scores for each category with proper error handling
      // Public Health impacts
      const publicHealthImpacts = safeGet(
        analysisData,
        "public_health_impacts",
        {}
      );
      const directEffects = safeArrayLength(
        safeGet(publicHealthImpacts, "direct_effects", [])
      );
      const indirectEffects = safeArrayLength(
        safeGet(publicHealthImpacts, "indirect_effects", [])
      );
      let publicHealthScore = (directEffects + indirectEffects) * 10;

      // Local Government impacts
      const localGovImpacts = safeGet(
        analysisData,
        "local_government_impacts",
        {}
      );
      const administrative = safeArrayLength(
        safeGet(localGovImpacts, "administrative", [])
      );
      const fiscal = safeArrayLength(safeGet(localGovImpacts, "fiscal", []));
      const implementation = safeArrayLength(
        safeGet(localGovImpacts, "implementation", [])
      );
      let localGovScore = (administrative + fiscal + implementation) * 10;

      // Economic impacts
      const economicImpacts = safeGet(analysisData, "economic_impacts", {});
      const directCosts = safeArrayLength(
        safeGet(economicImpacts, "direct_costs", [])
      );
      const economicEffects = safeArrayLength(
        safeGet(economicImpacts, "economic_effects", [])
      );
      const benefits = safeArrayLength(
        safeGet(economicImpacts, "benefits", [])
      );
      const longTermImpact = safeArrayLength(
        safeGet(economicImpacts, "long_term_impact", [])
      );
      let economicScore =
        (directCosts + economicEffects + benefits + longTermImpact) * 10;

      // Other impacts
      let environmentalScore =
        safeArrayLength(safeGet(analysisData, "environmental_impacts", [])) *
        20;
      let educationScore =
        safeArrayLength(safeGet(analysisData, "education_impacts", [])) * 20;
      let infrastructureScore =
        safeArrayLength(safeGet(analysisData, "infrastructure_impacts", [])) *
        20;

      // Use impact_summary if available for more accurate scoring
      const impactSummary = safeGet(analysisData, "impact_summary", {});
      const impactLevel = getImpactScore(
        safeGet(impactSummary, "impact_level")
      );
      const primaryCategory = safeGet(impactSummary, "primary_category");

      // Adjust the primary category score if available
      if (primaryCategory && impactLevel) {
        switch (primaryCategory) {
          case "public_health":
            publicHealthScore = Math.max(publicHealthScore, impactLevel);
            break;
          case "local_gov":
            localGovScore = Math.max(localGovScore, impactLevel);
            break;
          case "economic":
            economicScore = Math.max(economicScore, impactLevel);
            break;
          case "environmental":
            environmentalScore = Math.max(environmentalScore, impactLevel);
            break;
          case "education":
            educationScore = Math.max(educationScore, impactLevel);
            break;
          case "infrastructure":
            infrastructureScore = Math.max(infrastructureScore, impactLevel);
            break;
          default:
            break;
        }
      }

      // Cap scores at 100 with null/undefined handling
      const normalizeScore = (score) => Math.min(Math.round(score || 0), 100);

      return {
        labels: [
          "Public Health",
          "Local Government",
          "Economic",
          "Environmental",
          "Education",
          "Infrastructure",
        ],
        datasets: [
          {
            label: "Impact Score",
            data: [
              normalizeScore(publicHealthScore),
              normalizeScore(localGovScore),
              normalizeScore(economicScore),
              normalizeScore(environmentalScore),
              normalizeScore(educationScore),
              normalizeScore(infrastructureScore),
            ],
            backgroundColor: "rgba(54, 162, 235, 0.2)",
            borderColor: "rgba(54, 162, 235, 1)",
            borderWidth: 2,
            pointBackgroundColor: "rgba(54, 162, 235, 1)",
            pointBorderColor: "#fff",
            pointHoverBackgroundColor: "#fff",
            pointHoverBorderColor: "rgba(54, 162, 235, 1)",
          },
        ],
      };
    } catch (error) {
      logger.error("Error processing impact data:", error);
      // Return fallback data in case of error
      return {
        labels: [
          "Public Health",
          "Local Government",
          "Economic",
          "Environmental",
          "Education",
          "Infrastructure",
        ],
        datasets: [
          {
            label: "Impact Score",
            data: [0, 0, 0, 0, 0, 0],
            backgroundColor: "rgba(54, 162, 235, 0.2)",
            borderColor: "rgba(54, 162, 235, 1)",
            borderWidth: 2,
            pointBackgroundColor: "rgba(54, 162, 235, 1)",
            pointBorderColor: "#fff",
            pointHoverBackgroundColor: "#fff",
            pointHoverBorderColor: "rgba(54, 162, 235, 1)",
          },
        ],
      };
    }
  }, [analysisData]);

  const chartOptions = {
    scales: {
      r: {
        angleLines: {
          display: true,
        },
        suggestedMin: 0,
        suggestedMax: 100,
        ticks: {
          stepSize: 25,
        },
      },
    },
    plugins: {
      legend: {
        position: "top",
      },
      tooltip: {
        callbacks: {
          label: function (context) {
            return `${context.dataset.label}: ${context.raw}/100`;
          },
        },
      },
    },
    maintainAspectRatio: false,
  };

  if (!chartData) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
      >
        <h3 className="text-lg font-semibold mb-4">Impact Analysis</h3>
        <p className="text-gray-500 dark:text-gray-400">
          No impact data available
        </p>
      </div>
    );
  }

  // Create a data table for screen readers
  const renderDataTable = () => {
    if (
      !chartData ||
      !chartData.labels ||
      !chartData.datasets ||
      !chartData.datasets[0]
    ) {
      return null;
    }

    return (
      <div className="chart-text sr-only">
        <table className="data-table">
          <caption>Impact Analysis Scores (0-100)</caption>
          <thead>
            <tr>
              <th scope="col">Category</th>
              <th scope="col">Impact Score</th>
            </tr>
          </thead>
          <tbody>
            {chartData.labels.map((label, index) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                <td>{chartData.datasets[0].data[index]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className} analysis-section`}
    >
      <h3 className="text-lg font-semibold mb-4" id="impact-analysis-heading">
        Impact Analysis
      </h3>

      {/* Screen reader description */}
      <div className="chart-description sr-only">
        <p>
          This radar chart shows the impact scores across six categories: Public
          Health, Local Government, Economic, Environmental, Education, and
          Infrastructure. Scores range from 0 to 100, with higher scores
          indicating greater potential impact.
        </p>
      </div>

      <div
        className="h-64 md:h-80 chart-container"
        aria-labelledby="impact-analysis-heading"
      >
        <Radar data={chartData} options={chartOptions} />
        {renderDataTable()}
      </div>

      <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
        <p>
          This chart shows the relative impact of the bill across different
          categories.
        </p>
        <p>Higher scores indicate greater potential impact.</p>
      </div>
    </div>
  );
};

// PropTypes definition for component
ImpactScoreChart.propTypes = {
  analysisData: PropTypes.shape({
    public_health_impacts: PropTypes.object,
    local_government_impacts: PropTypes.object,
    economic_impacts: PropTypes.object,
    environmental_impacts: PropTypes.array,
    education_impacts: PropTypes.array,
    infrastructure_impacts: PropTypes.array,
    impact_summary: PropTypes.shape({
      impact_level: PropTypes.string,
      primary_category: PropTypes.string,
    }),
  }),
  className: PropTypes.string,
};

ImpactScoreChart.defaultProps = {
  className: "",
  analysisData: null,
};

export default ImpactScoreChart;
