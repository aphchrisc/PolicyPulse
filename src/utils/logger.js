/**
 * Logger utility for structured logging
 *
 * This utility provides safe logging functions that can be controlled via environment settings
 * and can be easily disabled in production to avoid leaking sensitive information.
 */

// Environment check for disabling logs in production
const isProduction = import.meta.env.PROD;
const logLevels = {
  ERROR: "error",
  WARN: "warn",
  INFO: "info",
  DEBUG: "debug",
  TRACE: "trace",
};

// Default minimum log level
const DEFAULT_MIN_LOG_LEVEL = logLevels.INFO;

// Get configured minimum log level
const getMinLogLevel = () => {
  const configuredLevel =
    import.meta.env.VITE_LOG_LEVEL || DEFAULT_MIN_LOG_LEVEL;
  return configuredLevel.toLowerCase();
};

// Check if a given log level should be output based on minimum level
const shouldLog = (level) => {
  if (isProduction) {
    // Only log errors and warnings in production
    return level === logLevels.ERROR || level === logLevels.WARN;
  }

  const minLevel = getMinLogLevel();
  const levels = Object.values(logLevels);
  const minLevelIndex = levels.indexOf(minLevel);
  const currentLevelIndex = levels.indexOf(level);

  // Log if current level is at or above the minimum level in the hierarchy
  return currentLevelIndex <= minLevelIndex;
};

// Format the log message with additional context
const formatMessage = (message, context) => {
  if (!context) return message;

  try {
    const contextStr =
      typeof context === "object" ? JSON.stringify(context) : context;
    return `${message} ${contextStr}`;
  } catch (error) {
    // If JSON serialization fails, still log something useful
    return `${message} [Context serialization failed]`;
  }
};

// Internal safe console methods to avoid no-console linting warnings
// These are not exported and only used within this module
const safeConsole = {
  error: (...args) => {
    // eslint-disable-next-line no-console
    if (!isProduction || (isProduction && shouldLog(logLevels.ERROR)))
      console.error(...args);
  },
  warn: (...args) => {
    // eslint-disable-next-line no-console
    if (!isProduction || (isProduction && shouldLog(logLevels.WARN)))
      console.warn(...args);
  },
  info: (...args) => {
    // eslint-disable-next-line no-console
    if (!isProduction || (isProduction && shouldLog(logLevels.INFO)))
      console.info(...args);
  },
  debug: (...args) => {
    // eslint-disable-next-line no-console
    if (!isProduction || (isProduction && shouldLog(logLevels.DEBUG)))
      console.debug(...args);
  },
  log: (...args) => {
    // eslint-disable-next-line no-console
    if (!isProduction || (isProduction && shouldLog(logLevels.TRACE)))
      console.log(...args);
  },
};

/**
 * Log an error message
 * @param {string} message - The error message
 * @param {object|Error} [error] - Optional error object or context
 */
export const logError = (message, error) => {
  if (shouldLog(logLevels.ERROR)) {
    if (error instanceof Error) {
      safeConsole.error(`[ERROR] ${message}`, error);
    } else {
      safeConsole.error(`[ERROR] ${formatMessage(message, error)}`);
    }
  }
};

/**
 * Log a warning message
 * @param {string} message - The warning message
 * @param {*} [context] - Optional context data
 */
export const logWarning = (message, context) => {
  if (shouldLog(logLevels.WARN)) {
    safeConsole.warn(`[WARNING] ${formatMessage(message, context)}`);
  }
};

/**
 * Log an informational message
 * @param {string} message - The info message
 * @param {*} [context] - Optional context data
 */
export const logInfo = (message, context) => {
  if (shouldLog(logLevels.INFO)) {
    safeConsole.info(`[INFO] ${formatMessage(message, context)}`);
  }
};

/**
 * Log a debug message
 * @param {string} message - The debug message
 * @param {*} [context] - Optional context data
 */
export const logDebug = (message, context) => {
  if (shouldLog(logLevels.DEBUG)) {
    safeConsole.debug(`[DEBUG] ${formatMessage(message, context)}`);
  }
};

/**
 * Log a trace message (lowest level)
 * @param {string} message - The trace message
 * @param {*} [context] - Optional context data
 */
export const logTrace = (message, context) => {
  if (shouldLog(logLevels.TRACE)) {
    safeConsole.log(`[TRACE] ${formatMessage(message, context)}`);
  }
};

// Export default logger object
export default {
  error: logError,
  warning: logWarning,
  warn: logWarning, // Alias
  info: logInfo,
  debug: logDebug,
  trace: logTrace,
  levels: logLevels,
};
