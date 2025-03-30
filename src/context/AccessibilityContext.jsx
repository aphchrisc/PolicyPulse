import React, { createContext, useState, useContext, useEffect } from "react";
import PropTypes from "prop-types";
import logger from "../utils/logger";
import { contextPropTypes } from "../utils/propTypes";

// Create context
const AccessibilityContext = createContext();

/**
 * Custom hook to use the accessibility context
 * @returns {Object} Accessibility context value
 */
export const useAccessibility = () => {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error(
      "useAccessibility must be used within an AccessibilityProvider"
    );
  }
  return context;
};

/**
 * Provider component for managing accessibility settings
 *
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components
 */
export const AccessibilityProvider = ({ children }) => {
  // Initialize state from localStorage if available
  const [settings, setSettings] = useState(() => {
    try {
      const storedSettings = localStorage.getItem("accessibilitySettings");
      return storedSettings
        ? JSON.parse(storedSettings)
        : {
            highContrast: false,
            largeText: false,
            reduceMotion: false,
            screenReader: false,
          };
    } catch (error) {
      logger.error(
        "Error loading accessibility settings from localStorage:",
        error
      );
      return {
        highContrast: false,
        largeText: false,
        reduceMotion: false,
        screenReader: false,
      };
    }
  });

  // Save settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem("accessibilitySettings", JSON.stringify(settings));

      // Apply settings to document
      applyAccessibilitySettings(settings);
    } catch (error) {
      logger.error(
        "Error saving accessibility settings to localStorage:",
        error
      );
    }
  }, [settings]);

  // Apply accessibility settings to the document
  const applyAccessibilitySettings = (currentSettings) => {
    // High contrast mode
    if (currentSettings.highContrast) {
      document.documentElement.classList.add("high-contrast");
    } else {
      document.documentElement.classList.remove("high-contrast");
    }

    // Large text
    if (currentSettings.largeText) {
      document.documentElement.classList.add("large-text");
    } else {
      document.documentElement.classList.remove("large-text");
    }

    // Reduce motion
    if (currentSettings.reduceMotion) {
      document.documentElement.classList.add("reduce-motion");
    } else {
      document.documentElement.classList.remove("reduce-motion");
    }

    // Screen reader optimized
    if (currentSettings.screenReader) {
      document.documentElement.classList.add("sr-optimized");
    } else {
      document.documentElement.classList.remove("sr-optimized");
    }
  };

  /**
   * Update a specific accessibility setting
   * @param {string} setting - The setting to update
   * @param {boolean} value - The new value
   */
  const updateSetting = (setting, value) => {
    setSettings((prev) => ({
      ...prev,
      [setting]: value,
    }));
  };

  /**
   * Toggle a specific accessibility setting
   * @param {string} setting - The setting to toggle
   */
  const toggleSetting = (setting) => {
    setSettings((prev) => ({
      ...prev,
      [setting]: !prev[setting],
    }));
  };

  /**
   * Reset all accessibility settings to defaults
   */
  const resetSettings = () => {
    setSettings({
      highContrast: false,
      largeText: false,
      reduceMotion: false,
      screenReader: false,
    });
  };

  // Context value
  const value = {
    settings,
    updateSetting,
    toggleSetting,
    resetSettings,
  };

  return (
    <AccessibilityContext.Provider value={value}>
      {children}
    </AccessibilityContext.Provider>
  );
};

AccessibilityProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export default AccessibilityContext;
