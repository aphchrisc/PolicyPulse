/**
 * Filter bills based on selected filter criteria
 * @param {Array} bills - List of bills to filter
 * @param {Object} filters - Filter criteria
 * @returns {Array} - Filtered list of bills
 */
export const filterBills = (bills, filters) => {
  if (!bills || !Array.isArray(bills)) {
    return [];
  }

  return bills.filter((bill) => {
    // Apply jurisdiction filter
    if (
      filters.jurisdiction !== "all" &&
      bill.jurisdiction !== filters.jurisdiction
    ) {
      return false;
    }

    // Apply status filter
    if (filters.status !== "all" && bill.status !== filters.status) {
      return false;
    }

    // Apply date filter
    if (filters.dateRange !== "all") {
      const billDate = new Date(bill.date || bill.last_action_date);

      switch (filters.dateRange) {
        case "lastWeek": {
          const lastWeek = new Date();
          lastWeek.setDate(lastWeek.getDate() - 7);
          if (billDate < lastWeek) {
            return false;
          }
          break;
        }
        case "lastMonth": {
          const lastMonth = new Date();
          lastMonth.setMonth(lastMonth.getMonth() - 1);
          if (billDate < lastMonth) {
            return false;
          }
          break;
        }
        case "lastQuarter": {
          const lastQuarter = new Date();
          lastQuarter.setMonth(lastQuarter.getMonth() - 3);
          if (billDate < lastQuarter) {
            return false;
          }
          break;
        }
        case "lastYear": {
          const lastYear = new Date();
          lastYear.setFullYear(lastYear.getFullYear() - 1);
          if (billDate < lastYear) {
            return false;
          }
          break;
        }
        default:
          // No date filter or unknown filter
          break;
      }
    }

    return true;
  });
};

/**
 * Get unique values for a property from an array of objects
 * Useful for populating filter dropdowns dynamically
 *
 * @param {Array} items - Array of objects
 * @param {string} property - Property to extract values from
 * @returns {Array} - Array of unique values
 */
export const getUniqueValues = (items, property) => {
  if (!items || !Array.isArray(items) || items.length === 0) {
    return [];
  }

  const values = items.map((item) => item[property]).filter(Boolean);
  return [...new Set(values)];
};
