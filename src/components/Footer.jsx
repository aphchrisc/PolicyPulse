import React from "react";
import { Link } from "react-router";

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-gradient-to-r from-blue-900 to-indigo-900 text-gray-300">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-lg font-semibold mb-4 text-white flex items-center">
              <img
                src="/logo.svg"
                alt="PolicyPulse Logo"
                className="w-6 h-6 mr-2"
              />
              PolicyPulse
            </h3>
            <p className="text-sm text-gray-400">
              Tracking legislation that matters to you. Stay informed about
              bills and policies affecting public health and local government.
            </p>
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4 text-white">
              Quick Links
            </h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link
                  to="/"
                  className="hover:text-white transition duration-300 flex items-center"
                >
                  <span className="w-1 h-1 bg-blue-400 rounded-full mr-2"></span>
                  Home
                </Link>
              </li>
              <li>
                <Link
                  to="/dashboard"
                  className="hover:text-white transition duration-300 flex items-center"
                >
                  <span className="w-1 h-1 bg-blue-400 rounded-full mr-2"></span>
                  Dashboard
                </Link>
              </li>
              <li>
                <Link
                  to="/bills"
                  className="hover:text-white transition duration-300 flex items-center"
                >
                  <span className="w-1 h-1 bg-blue-400 rounded-full mr-2"></span>
                  Bills
                </Link>
              </li>
              <li>
                <Link
                  to="/preferences"
                  className="hover:text-white transition duration-300 flex items-center"
                >
                  <span className="w-1 h-1 bg-blue-400 rounded-full mr-2"></span>
                  Preferences
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4 text-white">Resources</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link
                  to="/status"
                  className="hover:text-white transition duration-300 flex items-center"
                >
                  <span className="w-1 h-1 bg-blue-400 rounded-full mr-2"></span>
                  System Status
                </Link>
              </li>
              <li>
                <Link
                  to="/api-status"
                  className="hover:text-white transition duration-300 flex items-center"
                >
                  <span className="w-1 h-1 bg-blue-400 rounded-full mr-2"></span>
                  API Status
                </Link>
              </li>
              <li>
                <a
                  href="https://www.legiscan.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition duration-300 flex items-center"
                >
                  <span className="w-1 h-1 bg-blue-400 rounded-full mr-2"></span>
                  LegiScan
                </a>
              </li>
              <li>
                <a
                  href="https://www.congress.gov/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition duration-300 flex items-center"
                >
                  <span className="w-1 h-1 bg-blue-400 rounded-full mr-2"></span>
                  Congress.gov
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4 text-white">Contact</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href="mailto:support@policypulse.example.com"
                  className="hover:text-white transition duration-300 flex items-center"
                >
                  <svg
                    className="w-4 h-4 mr-2 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                    <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                  </svg>
                  <span className="truncate">
                    support@policypulse.example.com
                  </span>
                </a>
              </li>
              <li>
                <a
                  href="https://twitter.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition duration-300 flex items-center"
                >
                  <svg
                    className="w-4 h-4 mr-2 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723 10.054 10.054 0 01-3.127 1.184 4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" />
                  </svg>
                  <span>@PolicyPulse</span>
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition duration-300 flex items-center"
                >
                  <svg
                    className="w-4 h-4 mr-2 flex-shrink-0"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
                  </svg>
                  <span>GitHub</span>
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-gray-700 text-sm text-center text-gray-400">
          <p>
            {String.fromCharCode(169)} {currentYear} PolicyPulse. All rights
            reserved.
          </p>
          <div className="mt-2 flex justify-center space-x-4">
            <Link
              to="/privacy"
              className="hover:text-white transition duration-300"
            >
              Privacy Policy
            </Link>
            <Link
              to="/terms"
              className="hover:text-white transition duration-300"
            >
              Terms of Service
            </Link>
            <Link
              to="/accessibility"
              className="hover:text-white transition duration-300"
            >
              Accessibility
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
