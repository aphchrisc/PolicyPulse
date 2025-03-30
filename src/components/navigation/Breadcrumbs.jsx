import React from "react";
import { Link, useLocation } from "react-router-dom";

/**
 * Breadcrumbs component for navigation
 *
 * @param {Object} props - Component props
 * @param {Array} props.crumbs - Array of breadcrumb items with path and label
 * @param {string} props.className - Additional CSS classes
 */
const Breadcrumbs = ({ crumbs = [], className = "" }) => {
  const location = useLocation();

  // If no crumbs are provided, generate them from the current path
  if (crumbs.length === 0) {
    const pathSegments = location.pathname.split("/").filter(Boolean);

    // Start with home
    crumbs = [{ path: "/", label: "Home" }];

    // Add each path segment
    let currentPath = "";
    pathSegments.forEach((segment, index) => {
      currentPath += `/${segment}`;

      // Format the label (capitalize, replace hyphens with spaces)
      let label = segment
        .replace(/-/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());

      // Special case for IDs - if it's a number or looks like an ID, add "Details"
      if (/^\d+$/.test(segment) || /^[a-f0-9]{8,}$/i.test(segment)) {
        label = "Details";
      }

      crumbs.push({
        path: currentPath,
        label: label,
        isLast: index === pathSegments.length - 1,
      });
    });
  }

  // If there's only one crumb (home), don't show breadcrumbs
  if (crumbs.length <= 1) {
    return null;
  }

  return (
    <nav aria-label="Breadcrumb" className={`mb-4 ${className}`}>
      <ol className="flex flex-wrap items-center text-sm text-gray-600 dark:text-gray-400">
        {crumbs.map((crumb, index) => {
          const isLast = index === crumbs.length - 1 || crumb.isLast;

          return (
            <li key={crumb.path} className="flex items-center">
              {isLast ? (
                <span
                  className="font-medium text-gray-800 dark:text-gray-200"
                  aria-current="page"
                >
                  {crumb.label}
                </span>
              ) : (
                <>
                  <Link
                    to={crumb.path}
                    className="hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                  >
                    {crumb.label}
                  </Link>
                  <svg
                    className="icon-xs w-3 h-3 mx-2 text-gray-400"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                    aria-hidden="true"
                    width="12"
                    height="12"
                  >
                    <path
                      fillRule="evenodd"
                      d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

export default Breadcrumbs;
