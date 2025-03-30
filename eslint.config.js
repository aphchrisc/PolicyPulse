/* eslint-env node */
const reactPlugin = require("eslint-plugin-react");

module.exports = [
  {
    files: ["**/*.js", "**/*.jsx"],
    plugins: {
      react: reactPlugin,
    },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    rules: {
      // React rules
      "react/jsx-uses-react": "error",
      "react/jsx-uses-vars": "error",
      "react/prop-types": "warn", // Warn about missing prop types
      "react/no-unescaped-entities": "warn", // Warn about unescaped HTML entities
      "react/jsx-key": "error", // Require keys for array components
      "react/no-direct-mutation-state": "error", // Prevent direct mutation of state
      "react/no-deprecated": "error", // Prevent usage of deprecated methods

      // Common issues
      "no-unused-vars": "warn", // Warn about unused variables

      // Relaxed rules for development
      "no-console": "warn", // Allow console.* calls but warn
      "react/display-name": "off", // Don't require component display names
      "react/jsx-no-target-blank": "warn", // Warn about security issues with target="_blank"
    },
  },
];
