/**
 * Utility functions to handle unused variables in a linting-friendly way
 *
 * This file provides utilities to mark variables as intentionally unused,
 * which helps prevent ESLint warnings without removing potentially useful
 * code that might be needed in the future.
 */

/**
 * Marks a variable as intentionally unused to avoid linting errors
 * This is useful for parameters in functions that are required by an API
 * but not currently used in the implementation.
 *
 * @param {*} variable - The variable to mark as unused
 * @param {string} [reason] - Optional reason why the variable is unused
 * @returns {void}
 */
export const markUnused = (variable, reason = "") => {
  // This function does nothing with the variable but prevents
  // ESLint from complaining about unused variables
  if (import.meta.env.DEV) {
    // In development, log the unused variable for debugging
    const variableName = getVariableName(variable);
    if (reason) {
      console.debug(`Unused variable ${variableName}: ${reason}`);
    }
  }
  return;
};

/**
 * Helper function to try to get a meaningful name for a variable
 * @param {*} variable - The variable to name
 * @returns {string} A name for the variable
 */
const getVariableName = (variable) => {
  if (variable === null) return "null";
  if (variable === undefined) return "undefined";

  try {
    if (typeof variable === "object") {
      return variable.constructor?.name || "Object";
    } else {
      return typeof variable;
    }
  } catch (e) {
    return "unknown";
  }
};

/**
 * Utility for explicitly marking multiple parameters as unused
 * Useful in callback functions where many parameters are provided
 * but only some are actually used
 *
 * @param {Object} params - Object containing variables to mark as unused
 * @param {string} [reason] - Optional reason for why they're unused
 * @returns {void}
 */
export const markUnusedParams = (params, reason = "") => {
  // Handle null/undefined
  if (!params) return;

  // Handle array-like parameters
  if (Array.isArray(params)) {
    params.forEach((param) => markUnused(param, reason));
    return;
  }

  // Handle object parameters
  Object.keys(params).forEach((key) => {
    markUnused(params[key], `${key} ${reason}`);
  });
};

export default {
  markUnused,
  markUnusedParams,
};
