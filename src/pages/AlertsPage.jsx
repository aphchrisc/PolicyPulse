import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { billService } from "../services/api"; // Ensure billService is imported
import Card from "../components/ui/Card";
import BookmarkButton from "../components/bookmarks/BookmarkButton";
import Breadcrumbs from "../components/navigation/Breadcrumbs";
// Removed ImpactBadge and PrimaryImpactDisplay as summary data lacks required fields
import logger from "../utils/logger";

/**
 * AlertsPage - Displays high-impact bills based on API data.
 * Fetches bills where analysis impact_level is 'high' or 'critical'.
 */
const AlertsPage = () => {
  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  // Note: Filtering by 'executive-order' won't work until backend provides type info
  const [filter, setFilter] = useState("all"); // 'all', 'bill', 'executive-order'

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true);
        setError(null); // Clear previous errors

        // Define search parameters for high-impact bills
        const searchParams = {
          filters: {
            impact_level: ["high", "critical"],
            // Add other filters if needed, e.g., govt_type: ['federal']
          },
          sort_by: "updated", // Sort by most recently updated
          sort_dir: "desc",
          limit: 100, // Fetch up to 100 alerts
          offset: 0,
        };

        // Call the advanced search API
        const responseData = await billService.searchLegislationAdvanced(searchParams);

        // Assuming responseData structure is { count, items, page_info }
        if (responseData && Array.isArray(responseData.items)) {
          // Map API response (LegislationSummary) to the structure needed by the component
          const formattedAlerts = responseData.items.map(item => ({
              id: item.id, // Use the database ID for links/keys
              title: `${item.bill_number} - ${item.title}`, // Combine number and title
              // description: item.description || "No description available.", // Description not in summary
              type: item.govt_type || "bill", // Assume 'bill' if type is missing
              // impactLevel: item.analysis?.impact_level || 'unknown', // Not in summary
              date: item.updated_at, // Use updated_at as the primary date
              // categories: item.analysis?.impact_category ? [item.analysis.impact_category] : [], // Not in summary
              // impactDetails: item.analysis?.summary, // Not in summary
              status: item.bill_status || "Unknown",
              // Add other fields from summary if needed
              bill_number: item.bill_number,
              govt_source: item.govt_source,
          }));
          setAlerts(formattedAlerts);
        } else {
           logger.error("Invalid data structure received from alerts API", { responseData });
           setAlerts([]); // Set empty array if data is invalid
           setError("Received invalid data format for alerts.");
        }

      } catch (err) {
        logger.error("Error fetching alerts", { error: err });
        setError(err.message || "Failed to load alerts");
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
  }, []); // Run only on component mount

  // Filter alerts based on the selected tab (currently only 'bill' or 'all')
  const filteredAlerts = alerts.filter((alert) => {
    if (filter === "all") return true;
    // Basic filtering assuming 'bill' type for now
    return filter === 'bill' && alert.type === 'bill';
    // Add logic for 'executive-order' when data supports it
    // return filter === alert.type;
  });

  // Sort by date, newest first (using the 'date' field mapped from updated_at)
  const sortedAlerts = [...filteredAlerts].sort(
    (a, b) => new Date(b.date) - new Date(a.date)
  );

  return (
    <div className="container mx-auto px-4 py-8">
      <Breadcrumbs
        crumbs={[
          { path: "/", label: "Home" },
          { path: "/alerts", label: "High-Impact Alerts", isLast: true },
        ]}
      />

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-primary-700 mb-2">
          High-Impact Alerts
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          Track important legislation with significant potential impact based on AI analysis.
        </p>
      </div>

      {/* Filter tabs - Note: Executive Order filter is currently non-functional */}
      <div className="mb-6 border-b border-gray-200">
        <div className="flex flex-wrap -mb-px">
          <button
            onClick={() => setFilter("all")}
            className={`inline-block py-2 px-4 text-sm font-medium ${
              filter === "all"
                ? "text-primary-600 border-b-2 border-primary-600"
                : "text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            All Alerts
          </button>
          <button
            onClick={() => setFilter("bill")}
            className={`inline-block py-2 px-4 text-sm font-medium ${
              filter === "bill"
                ? "text-primary-600 border-b-2 border-primary-600"
                : "text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            Bills
          </button>
          <button
            onClick={() => setFilter("executive-order")}
            disabled // Disable until backend supports type filtering/data
            className={`inline-block py-2 px-4 text-sm font-medium ${
              filter === "executive-order"
                ? "text-primary-600 border-b-2 border-primary-600"
                : "text-gray-500 hover:text-gray-700 hover:border-gray-300"
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            title="Executive Order filtering not yet available"
          >
            Executive Orders
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
        </div>
      ) : error ? (
        <div className="bg-red-50 border-l-4 border-red-500 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-500"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      ) : sortedAlerts.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
            No high-impact alerts found
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            There are no alerts matching the 'high' or 'critical' impact level at this time.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {sortedAlerts.map((alert) => (
            <Card
              key={alert.id} // Use database ID as key
              className="shadow-sm hover:shadow-md transition-shadow duration-200"
            >
              <div className="flex justify-between items-start">
                <div className="w-full">
                  {/* Header section with Type (simplified), Status, and Date */}
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                     {/* Simplified Type Badge - Assuming 'bill' */}
                     <span
                      className={`px-2 py-1 rounded-full text-xs font-semibold capitalize bg-blue-100 text-blue-800`}
                    >
                      {alert.type || 'Legislation'}
                    </span>
                    {/* Status Badge */}
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-semibold capitalize ${
                        alert.status === 'passed' || alert.status === 'enacted' ? 'bg-green-100 text-green-800' :
                        alert.status === 'failed' || alert.status === 'vetoed' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800' // Default for introduced, committee, etc.
                      }`}
                    >
                      {alert.status || 'Unknown Status'}
                    </span>
                    {/* Date */}
                    <span className="text-xs text-gray-500">
                      Updated: {alert.date ? new Date(alert.date).toLocaleDateString() : 'N/A'}
                    </span>
                     {/* Jurisdiction */}
                     {alert.govt_source && (
                        <span className="text-xs text-gray-500 hidden sm:inline">
                            ({alert.govt_source})
                        </span>
                     )}
                  </div>

                  {/* Title */}
                  <h2 className="text-lg font-semibold text-primary-700 mb-2">
                    <Link
                      to={`/bills/${alert.id}`} // Link using database ID
                      className="hover:underline"
                    >
                      {alert.title} {/* Display combined bill_number and title */}
                    </Link>
                  </h2>

                  {/* Removed Description - Not available in summary */}
                  {/* Removed Categories - Not available in summary */}
                  {/* Removed PrimaryImpactDisplay - Not available in summary */}

                </div>

                {/* Bookmark Button - Pass minimal required info */}
                <BookmarkButton
                    bill={{ id: alert.id, title: alert.title }} // Pass only necessary info
                    size="md"
                    showText={false}
                />
              </div>

              {/* Footer with View Details link */}
              <div className="mt-4 pt-3 border-t border-gray-100 flex justify-between items-center">
                <Link
                  to={`/bills/${alert.id}`} // Link using database ID
                  className="text-primary-600 hover:text-primary-800 font-medium text-sm"
                >
                  View Details →
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default AlertsPage;
