import React, { useState, useEffect } from 'react';

/**
 * Advanced date range filter component for legislation
 * 
 * @param {Object} props - Component props
 * @param {Function} props.onApplyFilter - Callback function when filter is applied
 * @param {Object} props.initialRange - Initial date range values
 * @param {Function} props.onReset - Callback function when filter is reset
 * @param {string} props.className - Additional CSS classes
 */
const DateRangeFilter = ({
  onApplyFilter,
  initialRange = {},
  onReset,
  className = ''
}) => {
  // Predefined date ranges
  const PREDEFINED_RANGES = {
    ALL: 'all',
    LAST_WEEK: 'last_week',
    LAST_MONTH: 'last_month',
    LAST_3_MONTHS: 'last_3_months',
    LAST_6_MONTHS: 'last_6_months',
    LAST_YEAR: 'last_year',
    CURRENT_SESSION: 'current_session',
    CUSTOM: 'custom'
  };

  // Get current legislative session dates (approximate for Texas)
  const getCurrentSessionDates = () => {
    const currentYear = new Date().getFullYear();
    // Texas legislature typically meets in odd-numbered years starting in January
    const isSessionYear = currentYear % 2 === 1;
    
    if (isSessionYear) {
      // Session runs from January to May in session years
      return {
        start: `${currentYear}-01-01`,
        end: `${currentYear}-05-31`
      };
    } else {
      // Use previous year's session
      return {
        start: `${currentYear - 1}-01-01`,
        end: `${currentYear - 1}-05-31`
      };
    }
  };

  // Initialize state
  const [selectedRange, setSelectedRange] = useState(
    initialRange.predefined || PREDEFINED_RANGES.LAST_3_MONTHS
  );
  const [customRange, setCustomRange] = useState({
    startDate: initialRange.startDate || '',
    endDate: initialRange.endDate || ''
  });
  const [isCustom, setIsCustom] = useState(
    initialRange.predefined === PREDEFINED_RANGES.CUSTOM
  );

  // Calculate date for predefined ranges
  const getDateForRange = (range) => {
    const today = new Date();
    let startDate = '';
    let endDate = today.toISOString().split('T')[0]; // Today as YYYY-MM-DD
    
    switch (range) {
      case PREDEFINED_RANGES.LAST_WEEK:
        const lastWeek = new Date(today);
        lastWeek.setDate(today.getDate() - 7);
        startDate = lastWeek.toISOString().split('T')[0];
        break;
        
      case PREDEFINED_RANGES.LAST_MONTH:
        const lastMonth = new Date(today);
        lastMonth.setMonth(today.getMonth() - 1);
        startDate = lastMonth.toISOString().split('T')[0];
        break;
        
      case PREDEFINED_RANGES.LAST_3_MONTHS:
        const last3Months = new Date(today);
        last3Months.setMonth(today.getMonth() - 3);
        startDate = last3Months.toISOString().split('T')[0];
        break;
        
      case PREDEFINED_RANGES.LAST_6_MONTHS:
        const last6Months = new Date(today);
        last6Months.setMonth(today.getMonth() - 6);
        startDate = last6Months.toISOString().split('T')[0];
        break;
        
      case PREDEFINED_RANGES.LAST_YEAR:
        const lastYear = new Date(today);
        lastYear.setFullYear(today.getFullYear() - 1);
        startDate = lastYear.toISOString().split('T')[0];
        break;
        
      case PREDEFINED_RANGES.CURRENT_SESSION:
        const sessionDates = getCurrentSessionDates();
        startDate = sessionDates.start;
        endDate = sessionDates.end;
        break;
        
      case PREDEFINED_RANGES.ALL:
      default:
        startDate = '';
        break;
    }
    
    return { startDate, endDate };
  };

  // Handle predefined range selection
  const handleRangeChange = (e) => {
    const range = e.target.value;
    setSelectedRange(range);
    setIsCustom(range === PREDEFINED_RANGES.CUSTOM);
    
    if (range !== PREDEFINED_RANGES.CUSTOM) {
      const dates = getDateForRange(range);
      setCustomRange(dates);
    }
  };

  // Handle custom date changes
  const handleCustomDateChange = (field, value) => {
    setCustomRange(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Apply the filter
  const handleApplyFilter = () => {
    const filterData = {
      predefined: selectedRange,
      ...customRange
    };
    
    onApplyFilter(filterData);
  };

  // Reset the filter
  const handleResetFilter = () => {
    setSelectedRange(PREDEFINED_RANGES.LAST_3_MONTHS);
    setIsCustom(false);
    setCustomRange({
      startDate: '',
      endDate: ''
    });
    
    if (onReset) {
      onReset();
    }
  };

  // Update custom range when predefined range changes
  useEffect(() => {
    if (!isCustom) {
      const dates = getDateForRange(selectedRange);
      setCustomRange(dates);
    }
  }, [selectedRange, isCustom]);

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}>
      <h3 className="text-lg font-semibold mb-4">Date Range Filter</h3>
      
      <div className="space-y-4">
        <div>
          <label htmlFor="dateRange" className="block font-medium mb-2">Select Range</label>
          <select
            id="dateRange"
            value={selectedRange}
            onChange={handleRangeChange}
            className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            <option value={PREDEFINED_RANGES.ALL}>All Time</option>
            <option value={PREDEFINED_RANGES.LAST_WEEK}>Last Week</option>
            <option value={PREDEFINED_RANGES.LAST_MONTH}>Last Month</option>
            <option value={PREDEFINED_RANGES.LAST_3_MONTHS}>Last 3 Months</option>
            <option value={PREDEFINED_RANGES.LAST_6_MONTHS}>Last 6 Months</option>
            <option value={PREDEFINED_RANGES.LAST_YEAR}>Last Year</option>
            <option value={PREDEFINED_RANGES.CURRENT_SESSION}>Current Legislative Session</option>
            <option value={PREDEFINED_RANGES.CUSTOM}>Custom Range</option>
          </select>
        </div>
        
        {isCustom && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="startDate" className="block font-medium mb-2">Start Date</label>
              <input
                type="date"
                id="startDate"
                value={customRange.startDate}
                onChange={(e) => handleCustomDateChange('startDate', e.target.value)}
                className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
            
            <div>
              <label htmlFor="endDate" className="block font-medium mb-2">End Date</label>
              <input
                type="date"
                id="endDate"
                value={customRange.endDate}
                onChange={(e) => handleCustomDateChange('endDate', e.target.value)}
                className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>
        )}
        
        {!isCustom && selectedRange !== PREDEFINED_RANGES.ALL && (
          <div className="text-sm text-gray-500 dark:text-gray-400">
            <p>
              {selectedRange === PREDEFINED_RANGES.CURRENT_SESSION 
                ? 'Showing bills from the current legislative session' 
                : `Showing bills from ${customRange.startDate || 'the beginning'} to ${customRange.endDate || 'today'}`}
            </p>
          </div>
        )}
        
        <div className="flex justify-between pt-4">
          <button
            onClick={handleResetFilter}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
          >
            Reset
          </button>
          <button
            onClick={handleApplyFilter}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition dark:bg-blue-700 dark:hover:bg-blue-600"
          >
            Apply Filter
          </button>
        </div>
      </div>
    </div>
  );
};

export default DateRangeFilter; 