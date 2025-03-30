import { useState, useEffect } from "react";
import {
  getRecentActivity,
  getImpactSummary,
  getStatusBreakdown,
  getTrendingTopics,
} from "../services/api";
import logger from "../utils/logger";
import { calculateProgress } from "../utils/statusUtils";

/**
 * Custom hook to fetch and process dashboard data from the API
 * @returns {Object} Dashboard data state including loading, error, and processed data
 */
export const useDashboardData = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recentBills, setRecentBills] = useState([]);
  const [keyTerms, setKeyTerms] = useState([]);
  const [impactSummary, setImpactSummary] = useState(null);
  const [statusBreakdown, setStatusBreakdown] = useState(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        logger.info("Fetching dashboard data...");

        // Fetch all dashboard data in parallel
        const [
          recentActivityResponse,
          impactSummaryResponse,
          statusBreakdownResponse,
          trendingTopicsResponse,
        ] = await Promise.allSettled([
          getRecentActivity(30, 10),
          getImpactSummary("public_health", "current"),
          getStatusBreakdown(),
          getTrendingTopics(10),
        ]);

        // Process recent activity data
        if (
          recentActivityResponse.status === "fulfilled" &&
          recentActivityResponse.value?.data?.items
        ) {
          const processedBills = recentActivityResponse.value.data.items.map(
            (item) => ({
              id: item.id || Math.random().toString(36).substring(2),
              title: item.bill_number
                ? `${item.bill_number} - ${item.title}`
                : item.title || "Untitled Bill",
              jurisdiction: item.govt_type === "state" ? "State" : "Federal",
              date: item.updated_at
                ? new Date(item.updated_at).toLocaleDateString()
                : new Date().toLocaleDateString(),
              progress: calculateProgress(item.status || "introduced"),
              status: item.status || "introduced",
            })
          );
          logger.debug("Processed bills", { count: processedBills.length });
          setRecentBills(processedBills);
        } else if (recentActivityResponse.status === "rejected") {
          logger.error(
            "Failed to fetch recent activity",
            recentActivityResponse.reason
          );
        }

        // Process impact summary data
        if (
          impactSummaryResponse.status === "fulfilled" &&
          impactSummaryResponse.value?.data
        ) {
          logger.debug("Setting impact summary", {
            data: impactSummaryResponse.value.data,
          });
          setImpactSummary(impactSummaryResponse.value.data);
        } else if (impactSummaryResponse.status === "rejected") {
          logger.error(
            "Failed to fetch impact summary",
            impactSummaryResponse.reason
          );
        }

        // Process status breakdown data
        if (
          statusBreakdownResponse.status === "fulfilled" &&
          statusBreakdownResponse.value?.data
        ) {
          logger.debug("Setting status breakdown", {
            data: statusBreakdownResponse.value.data,
          });
          setStatusBreakdown(statusBreakdownResponse.value.data);
        } else if (statusBreakdownResponse.status === "rejected") {
          logger.error(
            "Failed to fetch status breakdown",
            statusBreakdownResponse.reason
          );
        }

        // Process trending topics data
        if (
          trendingTopicsResponse.status === "fulfilled" &&
          trendingTopicsResponse.value?.data?.topics
        ) {
          logger.debug("Setting trending topics", {
            count: trendingTopicsResponse.value.data.topics.length,
          });
          // Transform to expected format if needed
          const formattedTopics = trendingTopicsResponse.value.data.topics.map(
            (topic) => ({
              text: topic.term || topic.name || topic.text,
              value: topic.count || topic.value || 1,
            })
          );
          setKeyTerms(formattedTopics);
        } else if (trendingTopicsResponse.status === "rejected") {
          logger.error(
            "Failed to fetch trending topics",
            trendingTopicsResponse.reason
          );
        }

        // If all requests failed, set an error
        if (
          recentActivityResponse.status === "rejected" &&
          impactSummaryResponse.status === "rejected" &&
          statusBreakdownResponse.status === "rejected" &&
          trendingTopicsResponse.status === "rejected"
        ) {
          setError("Unable to load dashboard data. Please try again later.");
        }
      } catch (error) {
        logger.error("Error fetching dashboard data", { error });
        setError("Failed to load dashboard data. Please try again later.");
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return {
    loading,
    error,
    recentBills,
    keyTerms,
    impactSummary,
    statusBreakdown,
  };
};

export default useDashboardData;
