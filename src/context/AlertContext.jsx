import React, { createContext, useContext, useState, useEffect } from "react";
import PropTypes from "prop-types";
import { billService } from "../services/api";
import logger from "../utils/logger";
import { contextPropTypes } from "../utils/propTypes";

// Create a context for alerts
const AlertContext = createContext();

/**
 * Custom hook to use the alert context
 */
export const useAlerts = () => {
  const context = useContext(AlertContext);
  if (!context) {
    throw new Error("useAlerts must be used within an AlertProvider");
  }
  return context;
};

/**
 * AlertProvider component to wrap the application with alert context
 */
export const AlertProvider = ({ children }) => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch high-impact bills and executive orders
  useEffect(() => {
    const fetchHighImpactAlerts = async () => {
      try {
        setLoading(true);
        setError(null);
        // Use mock data since billService.getHighImpactAlerts doesn't exist
        const data = { alerts: getMockHighImpactAlerts() };
        setAlerts(data.alerts || []);
      } catch (err) {
        console.error("Error fetching high-impact alerts:", err);
        logger.error("Error fetching high-impact alerts:", err);
        setError("Failed to load alerts");
      } finally {
        setLoading(false);
      }
    };

    fetchHighImpactAlerts();
  }, []);

  // Add a new alert (would be called when a new high-impact bill is detected)
  const addAlert = (alert) => {
    setAlerts((prevAlerts) => [alert, ...prevAlerts]);
  };

  // Remove an alert (e.g., if it's no longer high impact)
  const removeAlert = (alertId) => {
    setAlerts((prevAlerts) =>
      prevAlerts.filter((alert) => alert.id !== alertId)
    );
  };

  // The value that will be provided to consumers of this context
  const value = {
    alerts,
    loading,
    error,
    addAlert,
    removeAlert,
  };

  return (
    <AlertContext.Provider value={value}>{children}</AlertContext.Provider>
  );
};

AlertProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

// Mock data function for high-impact alerts
const getMockHighImpactAlerts = () => [
  {
    id: "HR1234",
    title: "HR 1234 - Critical Healthcare Reform Act",
    description: "Major healthcare system restructuring with widespread impact",
    type: "bill",
    impactLevel: "critical",
    date: "2023-03-15",
  },
  {
    id: "EO2023-04",
    title: "Executive Order 2023-04: Emergency Climate Response",
    description: "New regulations for industries addressing climate change",
    type: "executive-order",
    impactLevel: "high",
    date: "2023-04-22",
  },
  {
    id: "SB5678",
    title: "SB 5678 - Education Funding Emergency Act",
    description: "Urgent education funding reallocation across states",
    type: "bill",
    impactLevel: "high",
    date: "2023-02-28",
  },
  {
    id: "HR9876",
    title: "HR 9876 - Cybersecurity Infrastructure Protection",
    description: "Critical updates to national cybersecurity standards",
    type: "bill",
    impactLevel: "critical",
    date: "2023-05-01",
  },
  {
    id: "EO2023-07",
    title: "Executive Order 2023-07: Drug Price Controls",
    description: "New regulations on pharmaceutical pricing and transparency",
    type: "executive-order",
    impactLevel: "high",
    date: "2023-04-30",
  },
];

export default AlertContext;
