import React from "react";
import { Link } from "react-router-dom";
import Card from "../../ui/Card";
import { BookmarkIcon } from "../../icons/DashboardIcons";

/**
 * Card displaying the number of bookmarked bills
 *
 * @returns {JSX.Element} BookmarksCard component
 */
const BookmarksCard = () => {
  return (
    <Card title="Your Bookmarks" icon={<BookmarkIcon />}>
      <div className="text-center">
        <div className="text-4xl font-bold text-blue-600 dark:text-blue-400 mb-2">
          12
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Bookmarked Bills
        </div>
        <div className="mt-4 flex items-center justify-center text-blue-600 dark:text-blue-400">
          <Link
            to="/bookmarks"
            className="text-sm font-medium flex items-center"
          >
            View Bookmarks
            <svg
              className="w-4 h-4 ml-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </Link>
        </div>
      </div>
    </Card>
  );
};

export default BookmarksCard;
