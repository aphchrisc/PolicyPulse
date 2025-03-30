import React, { useState } from 'react';

/**
 * Advanced filtering component for legislation based on impact categories and levels
 * 
 * @param {Object} props - Component props
 * @param {Function} props.onApplyFilters - Callback function when filters are applied
 * @param {Object} props.initialFilters - Initial filter values
 * @param {Function} props.onReset - Callback function when filters are reset
 * @param {string} props.className - Additional CSS classes
 */
const AdvancedFilters = ({ 
  onApplyFilters, 
  initialFilters = {}, 
  onReset,
  className = '' 
}) => {
  // Default filter state
  const defaultFilters = {
    impactCategories: {
      public_health: false,
      local_gov: false,
      economic: false,
      environmental: false,
      education: false,
      infrastructure: false
    },
    impactLevels: {
      critical: false,
      high: false,
      moderate: false,
      low: false
    },
    relevanceToTexas: {
      high: false,
      moderate: false,
      low: false
    }
  };

  // Initialize state with provided initial filters or defaults
  const [filters, setFilters] = useState({
    ...defaultFilters,
    ...initialFilters
  });

  // Handle checkbox changes for any filter group
  const handleCheckboxChange = (group, key) => {
    setFilters(prevFilters => ({
      ...prevFilters,
      [group]: {
        ...prevFilters[group],
        [key]: !prevFilters[group][key]
      }
    }));
  };

  // Apply filters
  const handleApplyFilters = () => {
    // Convert the filter state to a format expected by the parent component
    const formattedFilters = {
      impactCategories: Object.entries(filters.impactCategories)
        .filter(([_, isSelected]) => isSelected)
        .map(([category]) => category),
      impactLevels: Object.entries(filters.impactLevels)
        .filter(([_, isSelected]) => isSelected)
        .map(([level]) => level),
      relevanceToTexas: Object.entries(filters.relevanceToTexas)
        .filter(([_, isSelected]) => isSelected)
        .map(([level]) => level)
    };

    onApplyFilters(formattedFilters);
  };

  // Reset filters to default
  const handleResetFilters = () => {
    setFilters(defaultFilters);
    if (onReset) {
      onReset();
    }
  };

  // Check if any filters are active
  const hasActiveFilters = () => {
    return Object.values(filters.impactCategories).some(value => value) ||
           Object.values(filters.impactLevels).some(value => value) ||
           Object.values(filters.relevanceToTexas).some(value => value);
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}>
      <h3 className="text-lg font-semibold mb-4">Advanced Filters</h3>
      
      {/* Impact Categories */}
      <div className="mb-4">
        <h4 className="font-medium mb-2">Impact Categories</h4>
        <div className="grid grid-cols-2 gap-2">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.impactCategories.public_health}
              onChange={() => handleCheckboxChange('impactCategories', 'public_health')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span>Public Health</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.impactCategories.local_gov}
              onChange={() => handleCheckboxChange('impactCategories', 'local_gov')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span>Local Government</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.impactCategories.economic}
              onChange={() => handleCheckboxChange('impactCategories', 'economic')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span>Economic</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.impactCategories.environmental}
              onChange={() => handleCheckboxChange('impactCategories', 'environmental')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span>Environmental</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.impactCategories.education}
              onChange={() => handleCheckboxChange('impactCategories', 'education')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span>Education</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.impactCategories.infrastructure}
              onChange={() => handleCheckboxChange('impactCategories', 'infrastructure')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span>Infrastructure</span>
          </label>
        </div>
      </div>
      
      {/* Impact Levels */}
      <div className="mb-4">
        <h4 className="font-medium mb-2">Impact Levels</h4>
        <div className="grid grid-cols-2 gap-2">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.impactLevels.critical}
              onChange={() => handleCheckboxChange('impactLevels', 'critical')}
              className="rounded text-red-600 focus:ring-red-500"
            />
            <span className="text-red-600 dark:text-red-400 font-medium">Critical</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.impactLevels.high}
              onChange={() => handleCheckboxChange('impactLevels', 'high')}
              className="rounded text-orange-600 focus:ring-orange-500"
            />
            <span className="text-orange-600 dark:text-orange-400 font-medium">High</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.impactLevels.moderate}
              onChange={() => handleCheckboxChange('impactLevels', 'moderate')}
              className="rounded text-yellow-600 focus:ring-yellow-500"
            />
            <span className="text-yellow-600 dark:text-yellow-400 font-medium">Moderate</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.impactLevels.low}
              onChange={() => handleCheckboxChange('impactLevels', 'low')}
              className="rounded text-green-600 focus:ring-green-500"
            />
            <span className="text-green-600 dark:text-green-400 font-medium">Low</span>
          </label>
        </div>
      </div>
      
      {/* Relevance to Texas */}
      <div className="mb-4">
        <h4 className="font-medium mb-2">Relevance to Texas</h4>
        <div className="grid grid-cols-3 gap-2">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.relevanceToTexas.high}
              onChange={() => handleCheckboxChange('relevanceToTexas', 'high')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span>High</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.relevanceToTexas.moderate}
              onChange={() => handleCheckboxChange('relevanceToTexas', 'moderate')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span>Moderate</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.relevanceToTexas.low}
              onChange={() => handleCheckboxChange('relevanceToTexas', 'low')}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span>Low</span>
          </label>
        </div>
      </div>
      
      {/* Action buttons */}
      <div className="flex justify-between mt-6">
        <button
          onClick={handleResetFilters}
          className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
          disabled={!hasActiveFilters()}
        >
          Reset Filters
        </button>
        <button
          onClick={handleApplyFilters}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition dark:bg-blue-700 dark:hover:bg-blue-600"
        >
          Apply Filters
        </button>
      </div>
    </div>
  );
};

export default AdvancedFilters; 