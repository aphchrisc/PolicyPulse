import React from "react";
import PropTypes from "prop-types";
import { uiPropTypes } from "./propTypes";

/**
 * Card component for displaying content in a card-based layout
 *
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Card content
 * @param {string} props.title - Card title
 * @param {React.ReactNode} props.icon - Optional icon to display next to the title
 * @param {React.ReactNode} props.action - Optional action element (button, dropdown, etc.)
 * @param {string} props.className - Additional CSS classes
 * @param {boolean} props.noPadding - Whether to remove padding from the card body
 * @param {string} props.headerClassName - Additional CSS classes for the header
 * @param {string} props.bodyClassName - Additional CSS classes for the body
 */
const Card = ({
  children,
  title,
  icon,
  action,
  className = "",
  noPadding = false,
  headerClassName = "",
  bodyClassName = "",
}) => {
  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300 ${className}`}
    >
      {title && (
        <div
          className={`flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-700 ${headerClassName}`}
        >
          <div className="flex items-center">
            {icon && (
              <span className="mr-3 text-blue-600 dark:text-blue-400 flex-shrink-0 w-5 h-5">
                {icon}
              </span>
            )}
            <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
              {title}
            </h3>
          </div>
          {action && <div className="flex items-center">{action}</div>}
        </div>
      )}
      <div className={`${noPadding ? "" : "p-6"} ${bodyClassName}`}>
        {children}
      </div>
    </div>
  );
};

// Define prop types for the component
Card.propTypes = {
  children: PropTypes.node,
  title: PropTypes.node,
  icon: PropTypes.node,
  action: PropTypes.node,
  className: PropTypes.string,
  noPadding: PropTypes.bool,
  headerClassName: PropTypes.string,
  bodyClassName: PropTypes.string,
};

// Define default props
Card.defaultProps = {
  className: "",
  noPadding: false,
  headerClassName: "",
  bodyClassName: "",
};

export default Card;
