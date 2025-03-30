import React from "react";

/**
 * Welcome section for the dashboard
 *
 * @returns {JSX.Element} WelcomeSection component
 */
const WelcomeSection = () => {
  return (
    <div className="mb-8">
      <h1 className="text-2xl font-bold text-gray-800 dark:text-white mb-2">
        Welcome to PolicyPulse
      </h1>
      <p className="text-gray-600 dark:text-gray-300">
        Track and analyze legislation that matters to you. Stay informed about
        bills and policies affecting public health and local government.
      </p>
    </div>
  );
};

export default WelcomeSection;
