import React from "react";
import { useAlerts } from "../context/AlertContext";
import useDashboardData from "../hooks/useDashboardData";

// Dashboard components
import LoadingSpinner from "../components/dashboard/common/LoadingSpinner";
import ErrorAlert from "../components/dashboard/common/ErrorAlert";
import WelcomeSection from "../components/dashboard/common/WelcomeSection";
import WeeklySummaryCard from "../components/dashboard/SummaryCards/WeeklySummaryCard";
import TotalBillsCard from "../components/dashboard/SummaryCards/TotalBillsCard";
import BookmarksCard from "../components/dashboard/SummaryCards/BookmarksCard";
import HighImpactAlerts from "../components/dashboard/HighImpactAlerts";
import TrendingTopicsCard from "../components/dashboard/TrendingTopicsCard";
import ImpactDistributionCard from "../components/dashboard/ImpactDistributionCard";
import RecentActivityCard from "../components/dashboard/RecentActivityCard";
import KeyTermsAnalysisCard from "../components/dashboard/KeyTermsAnalysisCard";

/**
 * Main Dashboard page component
 * Shows an overview of legislative activity, high impact alerts, and data visualizations
 *
 * @returns {JSX.Element} Dashboard component
 */
function Dashboard() {
  const { loading, error, recentBills, keyTerms, impactSummary } =
    useDashboardData();
  const { alerts, loading: alertsLoading } = useAlerts();

  // Loading state
  if (loading && !recentBills.length) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="md" />
      </div>
    );
  }

  return (
    <div className="dashboard-container space-y-6">
      {/* Welcome Section */}
      <WelcomeSection />

      {/* Error Alert */}
      {error && <ErrorAlert message={error} />}

      {/* Summary Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <WeeklySummaryCard />
        <TotalBillsCard />
        <BookmarksCard />
      </div>

      {/* Alerts Section */}
      {alerts && alerts.length > 0 && (
        <HighImpactAlerts alerts={alerts} loading={alertsLoading} />
      )}

      {/* Visualizations Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <TrendingTopicsCard data={keyTerms} loading={loading} />
        <ImpactDistributionCard data={impactSummary} loading={loading} />
      </div>

      {/* Activity and Terms Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <RecentActivityCard
          data={recentBills}
          loading={loading}
          className="lg:col-span-2"
        />
        <KeyTermsAnalysisCard data={keyTerms} loading={loading} />
      </div>
    </div>
  );
}

export default Dashboard;
