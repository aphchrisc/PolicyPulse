import React from 'react';
import PropTypes from 'prop-types';

/**
 * Helper function to get Tailwind CSS classes for impact level badges.
 * @param {string} level - The impact level string (e.g., 'high', 'moderate', 'low').
 * @returns {string} - Tailwind classes.
 */
const getImpactLevelColor = (level) => {
  switch (level?.toLowerCase()) {
    case 'high':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
    case 'moderate':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
    case 'low':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'; // Default/unknown
  }
};

/**
 * Helper function to format category names.
 */
const formatCategory = (category) => {
  if (typeof category !== 'string') return 'Unknown';
  return category
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

/**
 * Renders a visualization for the impact ratings array.
 */
const ImpactRatingsVisualization = ({ ratings }) => {
  if (!Array.isArray(ratings) || ratings.length === 0) {
    return <p className="text-gray-500 dark:text-gray-400 text-sm italic">No impact ratings available.</p>;
  }

  return (
    <div className="space-y-4">
      {ratings.map((rating) => (
        <div key={rating.id} className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 shadow-sm">
          <div className="flex flex-wrap justify-between items-center mb-2 gap-2">
            <h4 className="text-md font-semibold text-gray-800 dark:text-gray-200">
              {formatCategory(rating.category)} Impact
            </h4>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getImpactLevelColor(rating.level)}`}>
              {rating.level ? formatCategory(rating.level) : 'N/A'}
            </span>
          </div>

          {rating.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">{rating.description}</p>
          )}

          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-500">
            <span>
              Confidence: {typeof rating.confidence === 'number' ? `${(rating.confidence * 100).toFixed(0)}%` : 'N/A'}
            </span>
            <span>
              {rating.is_ai_generated ? 'AI Generated' : 'Manual Entry'}
            </span>
          </div>
           {/* Optional: Add review info if needed later */}
           {/* {rating.reviewed_by && (
             <p className="text-xs text-gray-400 mt-1">Reviewed by: {rating.reviewed_by} on {rating.review_date ? new Date(rating.review_date).toLocaleDateString() : ''}</p>
           )} */}
        </div>
      ))}
    </div>
  );
};

ImpactRatingsVisualization.propTypes = {
  ratings: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.number.isRequired,
    category: PropTypes.string,
    level: PropTypes.string,
    description: PropTypes.string,
    confidence: PropTypes.number,
    is_ai_generated: PropTypes.bool,
    reviewed_by: PropTypes.string,
    review_date: PropTypes.string,
  })),
};

export default ImpactRatingsVisualization;