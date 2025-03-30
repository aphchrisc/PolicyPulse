import React, { useState, useEffect, useRef } from "react";
import { FiInfo } from "react-icons/fi";
import logger from "../../utils/logger";

/**
 * TimelineEvent component to render individual timeline events
 */
const TimelineEvent = ({ event, index, isDarkMode }) => {
  // Determine event icon and styling
  const status = event.status || determineEventStatus(event.action);
  const iconType = event.icon || determineEventIcon(event.action);
  const iconBackground = getIconBackground(iconType);
  const statusBackground = getStatusBackground(status);
  const isFirst = index === 0;
  const formattedDate = new Date(event.date).toLocaleDateString();

  return (
    <div className="flex mb-6 last:mb-0">
      {/* Timeline connector */}
      <div className="flex flex-col items-center mr-4">
        <div className={`w-3 h-3 rounded-full ${iconBackground} z-10`}>
          {renderIcon(iconType)}
        </div>
        {!isFirst && (
          <div className="w-0.5 h-full bg-gray-200 dark:bg-gray-700 -mt-3"></div>
        )}
      </div>

      {/* Event content */}
      <div className="pt-0.5 flex-1">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-1">
          <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {event.action}
          </h4>
          <time className="text-xs text-gray-500 dark:text-gray-400 mt-1 sm:mt-0">
            {formattedDate}
          </time>
        </div>
        {event.description && (
          <p className="text-xs text-gray-600 dark:text-gray-300 mb-1">
            {event.description}
          </p>
        )}
        {status && (
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusBackground}`}
          >
            {status}
          </span>
        )}
      </div>
    </div>
  );
};

/**
 * Bill Timeline Component
 *
 * Displays a vertical timeline of a bill's progression through the legislative process
 *
 * @param {Object} billData - The bill data containing history information
 * @param {boolean} isDarkMode - Whether dark mode is enabled
 */
const BillTimeline = ({ billData, isDarkMode = false }) => {
  const [timelineEvents, setTimelineEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const containerRef = useRef(null);

  // Process the timeline data
  useEffect(() => {
    try {
      setIsLoading(true);

      if (!billData) {
        setTimelineEvents([]);
        return;
      }

      // Check for timeline data in different possible locations
      let historyData = [];

      if (billData.history && Array.isArray(billData.history)) {
        historyData = billData.history;
      } else if (billData.actions && Array.isArray(billData.actions)) {
        historyData = billData.actions;
      } else if (billData.progress && Array.isArray(billData.progress)) {
        historyData = billData.progress;
      }

      // If we have no history data but have status and dates, create a simple timeline
      if (historyData.length === 0) {
        const fallbackEvents = [];

        // Add introduction date if available
        if (billData.introduced_date || billData.bill_introduced_date) {
          fallbackEvents.push({
            date: new Date(
              billData.introduced_date || billData.bill_introduced_date
            ),
            action: "Bill Introduced",
            description: `Bill was introduced${
              billData.sponsor ? ` by ${billData.sponsor}` : ""
            }`,
          });
        }

        // Add last action date if available and different from introduced date
        if (billData.updated_at || billData.bill_last_action_date) {
          const lastActionDate = new Date(
            billData.updated_at || billData.bill_last_action_date
          );
          const introDate =
            billData.introduced_date || billData.bill_introduced_date
              ? new Date(
                  billData.introduced_date || billData.bill_introduced_date
                )
              : null;

          // Only add if it's different from introduction date
          if (!introDate || lastActionDate.getTime() !== introDate.getTime()) {
            fallbackEvents.push({
              date: lastActionDate,
              action: billData.bill_status || "Last Update",
              description: `Bill status: ${billData.bill_status || "Updated"}`,
            });
          }
        }

        historyData = fallbackEvents;
      }

      if (historyData.length > 0) {
        // Format the data for timeline display
        const formattedEvents = historyData.map((event, index) => {
          // Ensure the event has a date
          const eventDate = event.date || event.action_date || event.timestamp;
          const date = eventDate ? new Date(eventDate) : new Date();

          return {
            id: index,
            date: date,
            title:
              event.action ||
              event.description ||
              event.status ||
              `Event ${index + 1}`,
            description: event.description || event.notes || "",
            status: determineEventStatus(event.action || event.status || ""),
            icon: determineEventIcon(event.action || event.status || ""),
          };
        });

        // Sort by date
        formattedEvents.sort((a, b) => a.date - b.date);

        setTimelineEvents(formattedEvents);
        setError(null);
      } else {
        // No data available
        setTimelineEvents([]);
        setError("No timeline data available");
      }
    } catch (err) {
      logger.error("Error processing timeline data", { error: err });
      setError("Failed to process timeline data");
      setIsLoading(false);
    }
  }, [billData]);

  // Helper function to determine status type
  const determineEventStatus = (action) => {
    if (!action) return "default";

    const actionLower = action.toLowerCase();

    if (actionLower.includes("passed") || actionLower.includes("approved")) {
      return "success";
    } else if (
      actionLower.includes("introduced") ||
      actionLower.includes("filed")
    ) {
      return "major";
    } else if (
      actionLower.includes("vetoed") ||
      actionLower.includes("failed")
    ) {
      return "critical";
    } else if (actionLower.includes("committee")) {
      return "info";
    } else {
      return "default";
    }
  };

  // Helper function to determine icon
  const determineEventIcon = (action) => {
    if (!action) return "default";

    const actionLower = action.toLowerCase();

    if (actionLower.includes("introduced") || actionLower.includes("filed")) {
      return "fileText";
    } else if (actionLower.includes("committee")) {
      return "users";
    } else if (
      actionLower.includes("passed") ||
      actionLower.includes("approved")
    ) {
      return "checkCircle";
    } else if (actionLower.includes("signed")) {
      return "edit";
    } else if (actionLower.includes("vetoed")) {
      return "xCircle";
    } else {
      return "clock";
    }
  };

  // Render appropriate icon based on type
  const renderIcon = (iconType) => {
    return (
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center ${getIconBackground(
          iconType
        )}`}
      >
        {getIconSvg(iconType)}
      </div>
    );
  };

  // Get background color for icon
  const getIconBackground = (iconType) => {
    switch (iconType) {
      case "fileText":
        return "bg-blue-100 dark:bg-blue-900";
      case "users":
        return "bg-yellow-100 dark:bg-yellow-900";
      case "checkCircle":
        return "bg-green-100 dark:bg-green-900";
      case "edit":
        return "bg-purple-100 dark:bg-purple-900";
      case "xCircle":
        return "bg-red-100 dark:bg-red-900";
      default:
        return "bg-gray-100 dark:bg-gray-800";
    }
  };

  // Get SVG icon based on type
  const getIconSvg = (iconType) => {
    const iconColor = isDarkMode ? "currentColor" : "currentColor";

    switch (iconType) {
      case "fileText":
        return (
          <svg
            className="w-4 h-4 text-blue-600 dark:text-blue-400"
            fill="none"
            stroke={iconColor}
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        );
      case "users":
        return (
          <svg
            className="w-4 h-4 text-yellow-600 dark:text-yellow-400"
            fill="none"
            stroke={iconColor}
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
            />
          </svg>
        );
      case "checkCircle":
        return (
          <svg
            className="w-4 h-4 text-green-600 dark:text-green-400"
            fill="none"
            stroke={iconColor}
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        );
      case "edit":
        return (
          <svg
            className="w-4 h-4 text-purple-600 dark:text-purple-400"
            fill="none"
            stroke={iconColor}
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
            />
          </svg>
        );
      case "xCircle":
        return (
          <svg
            className="w-4 h-4 text-red-600 dark:text-red-400"
            fill="none"
            stroke={iconColor}
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        );
      default:
        return (
          <svg
            className="w-4 h-4 text-gray-600 dark:text-gray-400"
            fill="none"
            stroke={iconColor}
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        );
    }
  };

  // Get background color for timeline item based on status
  const getStatusBackground = (status) => {
    switch (status) {
      case "success":
        return "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800";
      case "major":
        return "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800";
      case "critical":
        return "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800";
      case "info":
        return "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800";
      default:
        return "bg-gray-50 dark:bg-gray-800/30 border-gray-200 dark:border-gray-700";
    }
  };

  return (
    <div className="w-full h-full flex flex-col" ref={containerRef}>
      <div className="mb-2">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
          Bill Timeline
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Chronological progression of the bill
        </p>
      </div>

      <div className="flex-1 overflow-y-auto pr-2">
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-red-500">
              <FiInfo className="w-6 h-6 mb-2 mx-auto" />
              <p>{error}</p>
            </div>
          </div>
        ) : timelineEvents.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-gray-500 dark:text-gray-400">
              <FiInfo className="w-6 h-6 mb-2 mx-auto" />
              <p>No timeline data available</p>
            </div>
          </div>
        ) : (
          <div className="py-2">
            {timelineEvents.map((event, index) => (
              <TimelineEvent
                key={`${event.date}-${index}`}
                event={event}
                index={index}
                isDarkMode={isDarkMode}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default BillTimeline;
