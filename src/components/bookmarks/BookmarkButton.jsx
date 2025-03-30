import React from "react";
import PropTypes from "prop-types";
import { useBookmarks } from "../../context/BookmarkContext";

/**
 * Bookmark button component for toggling bill bookmark status
 *
 * @param {Object} props - Component props
 * @param {Object} props.bill - The bill to bookmark
 * @param {string} props.size - Button size ('sm', 'md', or 'lg')
 * @param {boolean} props.showText - Whether to show text label
 * @param {string} props.className - Additional CSS classes
 */
const BookmarkButton = ({
  bill,
  size = "md",
  showText = true,
  className = "",
}) => {
  const { isBookmarked, toggleBookmark } = useBookmarks();

  if (!bill?.id) {
    return null;
  }

  const bookmarked = isBookmarked(bill.id);

  // Determine styling based on size
  const getButtonPadding = () => {
    const paddings = {
      sm: showText ? "px-2 py-1" : "p-1",
      md: showText ? "px-3 py-1.5" : "p-1.5",
      lg: showText ? "px-4 py-2" : "p-2",
    };
    return paddings[size] || paddings.md;
  };

  const getTextSize = () => {
    const sizes = {
      sm: "text-xs",
      md: "text-sm",
      lg: "text-base",
    };
    return sizes[size] || sizes.md;
  };

  // Get icon class based on size
  const getIconClass = () => {
    let sizeClass;
    if (size === "sm") {
      sizeClass = "icon-sm";
    } else if (size === "lg") {
      sizeClass = "icon-lg";
    } else {
      sizeClass = "icon-md";
    }

    return `${sizeClass} ${
      showText ? "mr-1.5" : ""
    } inline-block flex-shrink-0`;
  };

  // Determine button style based on bookmark status
  const getButtonStyle = () => {
    return bookmarked
      ? "bg-blue-50 text-blue-600 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
      : "bg-gray-50 text-gray-700 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700";
  };

  return (
    <button
      onClick={() => toggleBookmark(bill)}
      className={`
        inline-flex items-center justify-center
        ${getButtonPadding()}
        ${getButtonStyle()}
        rounded-md transition-all duration-300 shadow-sm
        focus:outline-none focus:ring-2 focus:ring-blue-500
        ${className}
      `}
      aria-label={bookmarked ? "Remove bookmark" : "Add bookmark"}
      title={bookmarked ? "Remove bookmark" : "Add bookmark"}
    >
      {bookmarked ? (
        <svg className={getIconClass()} fill="currentColor" viewBox="0 0 20 20">
          <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
        </svg>
      ) : (
        <svg
          className={getIconClass()}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
          />
        </svg>
      )}

      {showText && (
        <span className={`${getTextSize()} font-medium`}>
          {bookmarked ? "Bookmarked" : "Bookmark"}
        </span>
      )}
    </button>
  );
};

BookmarkButton.propTypes = {
  bill: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  }).isRequired,
  size: PropTypes.oneOf(["sm", "md", "lg"]),
  showText: PropTypes.bool,
  className: PropTypes.string,
};

BookmarkButton.defaultProps = {
  size: "md",
  showText: true,
  className: "",
};

export default BookmarkButton;
