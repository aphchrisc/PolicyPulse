/**
 * Calculate progress percentage based on legislative status
 * @param {string} status - The current status of legislation
 * @returns {number} - Progress percentage (0-100)
 */
export const calculateProgress = (status) => {
  if (!status) {
    return 0;
  }

  const statusMap = {
    introduced: 10,
    referred: 20,
    committee: 30,
    amended: 45,
    passed_first: 60,
    passed_second: 75,
    sent_to_executive: 85,
    signed: 95,
    enacted: 100,
    vetoed: 90,
    failed: 15,
  };

  // Convert the status to snake_case for matching
  const normalizedStatus = status.toLowerCase().replace(/\s+/g, "_");

  // Return the mapped progress or a default value
  return statusMap[normalizedStatus] || 10;
};
