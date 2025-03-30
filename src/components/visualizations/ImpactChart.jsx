import React, { useState, useEffect, useRef } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { FiInfo } from "react-icons/fi";
import logger from "../../utils/logger";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const ImpactChart = ({ analysisData, isDarkMode = false }) => {
  const [chartData, setChartData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [chartDimensions, setChartDimensions] = useState({
    width: 0,
    height: 300,
  });
  const containerRef = useRef(null);

  // Handle responsive sizing
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const width = containerRef.current.clientWidth;
        // Adjust height based on screen size
        const height = window.innerWidth < 640 ? 250 : 300;
        setChartDimensions({ width, height });
      }
    };

    // Initial sizing
    handleResize();

    // Add resize listener
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    try {
      setIsLoading(true);

      if (!analysisData) {
        setChartData(null);
        setIsLoading(false);
        return;
      }

      // Extract impact data from analysis data
      let categories = [];
      let values = [];

      // Check for specific impact data structures
      if (
        analysisData.impact_assessment &&
        typeof analysisData.impact_assessment === "object"
      ) {
        // Direct impact assessment object
        categories = Object.keys(analysisData.impact_assessment);
        values = Object.values(analysisData.impact_assessment);
      } else if (
        analysisData.impact_scores &&
        typeof analysisData.impact_scores === "object"
      ) {
        // Impact scores object
        categories = Object.keys(analysisData.impact_scores);
        values = Object.values(analysisData.impact_scores);
      } else if (analysisData.impact_summary) {
        // Try to extract from impact summary
        const impactSummary = analysisData.impact_summary;

        if (
          impactSummary.categories &&
          Array.isArray(impactSummary.categories)
        ) {
          // Categories with scores
          categories = impactSummary.categories.map(
            (c) => c.name || c.category || c
          );
          values = impactSummary.categories.map(
            (c) => c.score || c.value || 50
          );
        } else if (typeof impactSummary === "object") {
          // Try to extract any relevant key-value pairs
          const relevantKeys = [
            "economic",
            "social",
            "environmental",
            "political",
            "health",
            "legal",
            "technical",
            "fiscal",
          ];

          // Filter to include only relevant keys that exist in the impact summary
          const filteredKeys = Object.keys(impactSummary).filter((key) =>
            relevantKeys.some((rk) => key.toLowerCase().includes(rk))
          );

          if (filteredKeys.length > 0) {
            categories = filteredKeys;
            values = filteredKeys.map((key) => {
              const val = impactSummary[key];
              return typeof val === "number"
                ? val
                : val === "high"
                ? 80
                : val === "medium"
                ? 50
                : val === "low"
                ? 30
                : 50;
            });
          }
        }
      }

      // If we still don't have data, try to extract impact mentions from various fields
      if (categories.length === 0) {
        // Create a scoring system based on mentions in different fields
        const impactCategories = {
          Economic: 0,
          Social: 0,
          Environmental: 0,
          "Public Health": 0,
          Legal: 0,
          Implementation: 0,
        };

        // Check economic impacts
        if (analysisData.economic_impacts) {
          impactCategories["Economic"] =
            typeof analysisData.economic_impacts === "object"
              ? Object.keys(analysisData.economic_impacts).length * 20
              : 60;
        }

        // Check health impacts
        if (analysisData.public_health_impacts) {
          impactCategories["Public Health"] =
            typeof analysisData.public_health_impacts === "object"
              ? Object.keys(analysisData.public_health_impacts).length * 20
              : 60;
        }

        // Check environmental impacts
        if (analysisData.environmental_impacts) {
          impactCategories["Environmental"] = Array.isArray(
            analysisData.environmental_impacts
          )
            ? analysisData.environmental_impacts.length * 20
            : 60;
        }

        // Check legal issues
        if (analysisData.legal_issues) {
          impactCategories["Legal"] = Array.isArray(analysisData.legal_issues)
            ? analysisData.legal_issues.length * 20
            : 60;
        }

        // Implementation challenges
        if (
          analysisData.implementation_challenges ||
          (analysisData.local_government_impacts &&
            typeof analysisData.local_government_impacts === "object")
        ) {
          impactCategories["Implementation"] = 60;
        }

        // Social impacts - check various fields that might indicate social impact
        if (
          analysisData.stakeholders ||
          analysisData.affected_populations ||
          analysisData.social_impacts
        ) {
          impactCategories["Social"] = 70;
        }

        // Filter out zero values and convert to arrays
        const nonZeroCategories = Object.entries(impactCategories).filter(
          ([_, value]) => value > 0
        );

        if (nonZeroCategories.length > 0) {
          categories = nonZeroCategories.map(([key, _]) => key);
          values = nonZeroCategories.map(([_, value]) => value);
        }
      }

      // If we still don't have any data, create placeholder categories
      if (categories.length === 0) {
        categories = [
          "Economic",
          "Social",
          "Environmental",
          "Health",
          "Implementation",
        ];
        values = [65, 45, 30, 50, 70]; // Default placeholder values
      }

      // Format the categories for display
      const formattedCategories = categories.map((cat) =>
        formatCategoryName(cat)
      );

      // Ensure all values are numbers and cap at 100
      const processedValues = values.map((val) => {
        const numVal = typeof val === "number" ? val : parseInt(val, 10);
        return isNaN(numVal) ? 50 : Math.min(numVal, 100);
      });

      // Prepare chart data
      const data = {
        labels: formattedCategories,
        datasets: [
          {
            label: "Impact Score",
            data: processedValues,
            backgroundColor: isDarkMode
              ? "rgba(59, 130, 246, 0.7)"
              : "rgba(37, 99, 235, 0.7)",
            borderColor: isDarkMode
              ? "rgba(96, 165, 250, 1)"
              : "rgba(37, 99, 235, 1)",
            borderWidth: 1,
            borderRadius: 4,
          },
        ],
      };

      setChartData(data);
      setIsLoading(false);
    } catch (error) {
      logger.error("Error preparing impact chart data", { error });
      setIsLoading(false);
    }
  }, [analysisData, isDarkMode]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: "y", // Horizontal bar chart
    scales: {
      y: {
        grid: {
          display: false,
          color: isDarkMode ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.1)",
        },
        ticks: {
          color: isDarkMode ? "rgba(255, 255, 255, 0.7)" : "rgba(0, 0, 0, 0.7)",
          font: {
            size: 11,
          },
          padding: 5,
        },
      },
      x: {
        beginAtZero: true,
        max: 100,
        grid: {
          color: isDarkMode ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.1)",
        },
        ticks: {
          color: isDarkMode ? "rgba(255, 255, 255, 0.7)" : "rgba(0, 0, 0, 0.7)",
          font: {
            size: 11,
          },
          callback: function (value) {
            return value + "%";
          },
        },
      },
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: isDarkMode
          ? "rgba(0, 0, 0, 0.8)"
          : "rgba(255, 255, 255, 0.8)",
        titleColor: isDarkMode ? "#fff" : "#000",
        bodyColor: isDarkMode ? "#fff" : "#000",
        caretSize: 6,
        cornerRadius: 4,
        padding: 8,
        displayColors: false,
        callbacks: {
          label: function (context) {
            return `Impact: ${context.formattedValue}%`;
          },
        },
      },
    },
  };

  return (
    <div className="w-full h-full flex flex-col" ref={containerRef}>
      <div className="mb-2">
        <h3 className="text-lg font-semibold mb-1 text-gray-800 dark:text-white">
          Impact Assessment
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Estimated impact percentages by category
        </p>
      </div>

      <div className="flex-1 overflow-hidden flex items-center justify-center">
        {isLoading ? (
          <div className="text-center text-gray-500 dark:text-gray-400">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
            <p>Loading impact data...</p>
          </div>
        ) : !chartData ? (
          <div className="text-gray-500 dark:text-gray-400 text-center">
            <FiInfo className="w-6 h-6 mb-2 mx-auto" />
            <p>No impact data available</p>
          </div>
        ) : (
          <div style={{ height: chartDimensions.height, width: "100%" }}>
            <Bar data={chartData} options={chartOptions} />
          </div>
        )}
      </div>
    </div>
  );
};

// Utility function to format category names
function formatCategoryName(category) {
  if (!category) return "Unknown";

  return String(category)
    .replace(/([A-Z])/g, " $1") // Add space before capital letters
    .replace(/[_-]/g, " ") // Replace underscores and hyphens with spaces
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export default ImpactChart;
