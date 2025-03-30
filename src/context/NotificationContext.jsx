import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
} from "react";
import PropTypes from "prop-types";

// Create the notification context
const NotificationContext = createContext();

// Custom hook to use the notification context
export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error(
      "useNotification must be used within a NotificationProvider"
    );
  }
  return context;
};

// Notification types
export const NOTIFICATION_TYPES = {
  SUCCESS: "success",
  ERROR: "error",
  WARNING: "warning",
  INFO: "info",
};

// Notification provider component
export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);

  // Add a new notification
  const addNotification = useCallback(
    (message, type = NOTIFICATION_TYPES.INFO, timeout = 5000) => {
      const id = Date.now() + Math.random().toString(36).substring(2, 5);
      const newNotification = {
        id,
        message,
        type,
        timestamp: new Date(),
      };

      setNotifications((prev) => [...prev, newNotification]);

      // Auto-remove notification after timeout
      if (timeout !== 0) {
        setTimeout(() => {
          removeNotification(id);
        }, timeout);
      }

      return id;
    },
    []
  );

  // Remove a notification by ID
  const removeNotification = useCallback((id) => {
    setNotifications((prev) =>
      prev.filter((notification) => notification.id !== id)
    );
  }, []);

  // Clear all notifications
  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  // Convenience methods for different notification types
  const success = useCallback(
    (message, timeout) => {
      return addNotification(message, NOTIFICATION_TYPES.SUCCESS, timeout);
    },
    [addNotification]
  );

  const error = useCallback(
    (message, timeout) => {
      return addNotification(message, NOTIFICATION_TYPES.ERROR, timeout);
    },
    [addNotification]
  );

  const warning = useCallback(
    (message, timeout) => {
      return addNotification(message, NOTIFICATION_TYPES.WARNING, timeout);
    },
    [addNotification]
  );

  const info = useCallback(
    (message, timeout) => {
      return addNotification(message, NOTIFICATION_TYPES.INFO, timeout);
    },
    [addNotification]
  );

  // The value to be provided to consumers - wrapped in useMemo to prevent unnecessary rerenders
  const value = useMemo(
    () => ({
      notifications,
      addNotification,
      removeNotification,
      clearNotifications,
      success,
      error,
      warning,
      info,
    }),
    [
      notifications,
      addNotification,
      removeNotification,
      clearNotifications,
      success,
      error,
      warning,
      info,
    ]
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <NotificationContainer />
    </NotificationContext.Provider>
  );
};

NotificationProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

// Notification container component
const NotificationContainer = () => {
  const { notifications, removeNotification } = useNotification();

  if (notifications.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
      {notifications.map((notification) => (
        <Notification
          key={notification.id}
          notification={notification}
          onClose={() => removeNotification(notification.id)}
        />
      ))}
    </div>
  );
};

// Individual notification component
const Notification = ({ notification, onClose }) => {
  const { message, type } = notification;

  // Determine styles based on notification type
  const getTypeStyles = () => {
    switch (type) {
      case NOTIFICATION_TYPES.SUCCESS:
        return {
          container: "bg-green-50 border-green-500",
          icon: "text-green-500",
          iconPath:
            "M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z",
          text: "text-green-800",
        };
      case NOTIFICATION_TYPES.ERROR:
        return {
          container: "bg-red-50 border-red-500",
          icon: "text-red-500",
          iconPath:
            "M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z",
          text: "text-red-800",
        };
      case NOTIFICATION_TYPES.WARNING:
        return {
          container: "bg-yellow-50 border-yellow-500",
          icon: "text-yellow-500",
          iconPath:
            "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
          text: "text-yellow-800",
        };
      case NOTIFICATION_TYPES.INFO:
      default:
        return {
          container: "bg-blue-50 border-blue-500",
          icon: "text-blue-500",
          iconPath: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
          text: "text-blue-800",
        };
    }
  };

  const styles = getTypeStyles();

  return (
    <div
      className={`p-4 rounded-md shadow-md border-l-4 ${styles.container} transform transition-all duration-300 ease-in-out`}
      role="alert"
    >
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className={`h-5 w-5 ${styles.icon}`}
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path fillRule="evenodd" d={styles.iconPath} clipRule="evenodd" />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <p className={`text-sm ${styles.text}`}>{message}</p>
        </div>
        <div className="ml-auto pl-3">
          <div className="-mx-1.5 -my-1.5">
            <button
              onClick={onClose}
              className={`inline-flex rounded-md p-1.5 ${styles.text} hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-50 focus:ring-gray-600`}
            >
              <span className="sr-only">Dismiss</span>
              <svg
                className="h-5 w-5"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

Notification.propTypes = {
  notification: PropTypes.shape({
    id: PropTypes.string.isRequired,
    message: PropTypes.string.isRequired,
    type: PropTypes.string.isRequired,
    timestamp: PropTypes.instanceOf(Date).isRequired,
  }).isRequired,
  onClose: PropTypes.func.isRequired,
};

export default NotificationProvider;
