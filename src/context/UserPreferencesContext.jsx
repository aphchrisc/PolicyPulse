import React, {
  createContext,
  useState,
  useEffect,
  useContext,
  useMemo,
} from "react";
import PropTypes from "prop-types";
import { toast } from "react-toastify";
import logger from "../utils/logger";

// Create context
export const UserPreferencesContext = createContext();

// Default preferences
const defaultPreferences = {
  theme: "light", // light or dark
  fontSize: "medium", // small, medium, or large
  billsPerPage: 10, // number of bills to display per page
  defaultView: "list", // list or grid
  savedFilters: [], // saved search filters
  favoriteTopics: [], // favorite legislative topics
  notificationsEnabled: true,
  dataRefreshInterval: 30, // minutes
  notifications: {
    enabled: false,
    billUpdates: true,
    newBills: false,
    frequency: "daily", // daily, weekly, immediate
  },
};

// Get the currently preferred color scheme from system
const getSystemThemePreference = () => {
  return window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

// Function to apply theme to document - moved before it's used
const applyTheme = (theme) => {
  if (theme === "dark") {
    document.documentElement.classList.add("dark");
    document.documentElement.classList.remove("light");
  } else {
    document.documentElement.classList.remove("dark");
    document.documentElement.classList.add("light");
  }
};

export const UserPreferencesProvider = ({ children }) => {
  // Initialize state with localStorage or defaults
  const [preferences, setPreferences] = useState(() => {
    try {
      // Try to get from localStorage first
      const savedPreferences = localStorage.getItem("userPreferences");

      if (savedPreferences) {
        const parsedPreferences = JSON.parse(savedPreferences);
        // Apply the theme immediately on initial load
        applyTheme(parsedPreferences.theme);
        return parsedPreferences;
      } else {
        // If nothing in localStorage, check system preference
        const systemTheme = getSystemThemePreference();
        // Apply it immediately
        applyTheme(systemTheme);
        return {
          ...defaultPreferences,
          theme: systemTheme,
        };
      }
    } catch (error) {
      logger.error("Failed to load preferences from localStorage", { error });
      // Return default preferences but with system theme preference
      const systemTheme = getSystemThemePreference();
      applyTheme(systemTheme);
      return {
        ...defaultPreferences,
        theme: systemTheme,
      };
    }
  });

  // Listen for system theme preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const handleChange = (e) => {
      // Only update if the user hasn't explicitly set a preference
      if (!localStorage.getItem("userPreferences")) {
        const newTheme = e.matches ? "dark" : "light";
        setPreferences((prev) => ({
          ...prev,
          theme: newTheme,
        }));
        applyTheme(newTheme);
      }
    };

    // Add event listener - using modern method
    mediaQuery.addEventListener("change", handleChange);

    // Cleanup function - using modern method
    return () => {
      mediaQuery.removeEventListener("change", handleChange);
    };
  }, []);

  // Save preferences to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem("userPreferences", JSON.stringify(preferences));
      // Apply theme when preferences change
      applyTheme(preferences.theme);
    } catch (error) {
      logger.error("Failed to save preferences to localStorage", { error });
      toast.error("Failed to save your preferences");
    }
  }, [preferences]);

  // Update a specific preference
  const updatePreference = (key, value) => {
    setPreferences((prev) => {
      // Handle nested preferences
      if (typeof key === "string" && key.includes(".")) {
        const [parentKey, childKey] = key.split(".");
        return {
          ...prev,
          [parentKey]: {
            ...prev[parentKey],
            [childKey]: value,
          },
        };
      }

      // Handle top-level preferences
      return {
        ...prev,
        [key]: value,
      };
    });

    // If updating theme, show toast
    if (key === "theme") {
      toast.success(
        `${value.charAt(0).toUpperCase() + value.slice(1)} mode activated`
      );
    } else {
      toast.success("Preferences updated");
    }
  };

  // Reset preferences to default
  const resetPreferences = () => {
    const systemTheme = getSystemThemePreference();
    const resetDefaults = {
      ...defaultPreferences,
      theme: systemTheme,
    };
    setPreferences(resetDefaults);
    applyTheme(systemTheme);
    toast.info("Preferences reset to default");
  };

  // Add a saved filter
  const addSavedFilter = (filter) => {
    setPreferences((prev) => ({
      ...prev,
      savedFilters: [...prev.savedFilters, filter],
    }));
    toast.success("Filter saved");
  };

  // Remove a saved filter
  const removeSavedFilter = (filterId) => {
    setPreferences((prev) => ({
      ...prev,
      savedFilters: prev.savedFilters.filter(
        (filter) => filter.id !== filterId
      ),
    }));
    toast.info("Filter removed");
  };

  // Toggle a favorite topic
  const toggleFavoriteTopic = (topic) => {
    setPreferences((prev) => {
      const topicExists = prev.favoriteTopics.includes(topic);
      return {
        ...prev,
        favoriteTopics: topicExists
          ? prev.favoriteTopics.filter((t) => t !== topic)
          : [...prev.favoriteTopics, topic],
      };
    });
  };

  // Memoize the context value to prevent unnecessary re-renders
  const contextValue = useMemo(
    () => ({
      preferences,
      updatePreference,
      resetPreferences,
      addSavedFilter,
      removeSavedFilter,
      toggleFavoriteTopic,
    }),
    [preferences]
  );

  return (
    <UserPreferencesContext.Provider value={contextValue}>
      {children}
    </UserPreferencesContext.Provider>
  );
};

// Add PropTypes validation
UserPreferencesProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

// Custom hook for using preferences
export const useUserPreferences = () => {
  const context = useContext(UserPreferencesContext);
  if (!context) {
    throw new Error(
      "useUserPreferences must be used within a UserPreferencesProvider"
    );
  }
  return context;
};
