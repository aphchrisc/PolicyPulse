import React from "react";
import PropTypes from "prop-types";

/**
 * Loading spinner component
 *
 * @param {Object} props - Component props
 * @param {string} props.size - Size of the spinner (sm, md, lg)
 * @returns {JSX.Element} LoadingSpinner component
 */
const LoadingSpinner = ({ size = "md" }) => {
  const sizeClasses = {
    sm: "h-8 w-8",
    md: "h-12 w-12",
    lg: "h-16 w-16",
  };

  const spinnerSize = sizeClasses[size] || sizeClasses.md;

  return (
    <div className="flex justify-center items-center">
      <div
        className={`animate-spin rounded-full ${spinnerSize} border-t-2 border-b-2 border-blue-500`}
      ></div>
    </div>
  );
};

LoadingSpinner.propTypes = {
  size: PropTypes.oneOf(["sm", "md", "lg"]),
};

export default LoadingSpinner;
