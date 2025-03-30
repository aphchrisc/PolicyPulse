import React, { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";

/**
 * AlertTicker - A component that displays high-impact legislation alerts in a ticker-tape style
 *
 * Features:
 * - Red banner with white text (non-blinking)
 * - Auto-scrolls through multiple alerts with a smooth transition
 * - Clickable links to individual bill pages
 * - Pause on hover
 * - Progress indicator for timing
 * - Auto-hides on scroll (NEW)
 */
const AlertTicker = ({ alerts = [] }) => {
  const [currentAlertIndex, setCurrentAlertIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [progress, setProgress] = useState(100);
  const [isVisible, setIsVisible] = useState(true);
  const [scrollTimeout, setScrollTimeout] = useState(null);
  const tickerRef = useRef(null);
  const intervalRef = useRef(null);
  const progressIntervalRef = useRef(null);

  // No alerts to display
  if (!alerts || alerts.length === 0) {
    return null;
  }

  // Initialize rotation timer on mount and handle transitions between alerts
  useEffect(() => {
    // Function to handle the transition to the next alert
    const rotateAlert = () => {
      // Skip rotation if paused or only one alert
      if (isPaused || alerts.length <= 1) return;

      // Start transition effect
      setIsTransitioning(true);
      setProgress(0); // Reset progress

      // After 1000ms (transition duration), change the alert
      setTimeout(() => {
        setCurrentAlertIndex((prevIndex) => (prevIndex + 1) % alerts.length);

        // Reset transition state after the alert has changed
        setTimeout(() => {
          setIsTransitioning(false);

          // Start progress animation for next rotation
          setProgress(100);
        }, 200);
      }, 1000);
    };

    // Immediately initialize first transition if more than one alert
    if (alerts.length > 1) {
      // Short delay before starting animation to ensure component is fully mounted
      const initialTimeout = setTimeout(() => {
        setProgress(100); // Start with full progress
        rotateAlert();
      }, 2000);

      // Set up the interval for subsequent rotations
      intervalRef.current = setInterval(rotateAlert, 6000); // Rotate every 6 seconds

      // Set up progress bar animation
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }

      progressIntervalRef.current = setInterval(() => {
        if (!isPaused) {
          setProgress((prevProgress) => {
            // Decrease by approximately 1.67% every 100ms to reach 0 in 6 seconds
            const newProgress = prevProgress - 1.67;
            return newProgress < 0 ? 0 : newProgress;
          });
        }
      }, 100);

      return () => {
        clearTimeout(initialTimeout);
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
        }
      };
    }
  }, [alerts.length, isPaused]);

  // Handle auto-hiding on scroll
  useEffect(() => {
    const handleScroll = () => {
      // Show the banner when scroll action starts
      setIsVisible(true);

      // Clear any existing timeout
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
      }

      // Set a new timeout to hide the banner after scrolling stops
      const timeout = setTimeout(() => {
        // Only hide if we've scrolled down a bit (> 100px)
        if (window.scrollY > 100) {
          setIsVisible(false);
        }
      }, 1500); // Hide 1.5 seconds after scroll stops

      setScrollTimeout(timeout);
    };

    // Add scroll event listener
    window.addEventListener("scroll", handleScroll);

    // Clean up
    return () => {
      window.removeEventListener("scroll", handleScroll);
      if (scrollTimeout) {
        clearTimeout(scrollTimeout);
      }
    };
  }, [scrollTimeout]);

  const currentAlert = alerts[currentAlertIndex];

  // Handle manual navigation with dots
  const goToAlert = (index) => {
    if (currentAlertIndex === index) return;

    // Clear existing intervals to prevent conflicts
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }

    // Start the transition effect
    setIsTransitioning(true);
    setProgress(0);

    // After transition duration, change to selected alert
    setTimeout(() => {
      setCurrentAlertIndex(index);

      // Reset transition state
      setTimeout(() => {
        setIsTransitioning(false);
        setProgress(100);
      }, 200);

      // Restart the interval
      intervalRef.current = setInterval(() => {
        // Start transition effect
        setIsTransitioning(true);
        setProgress(0);

        // After transition duration, change the alert
        setTimeout(() => {
          setCurrentAlertIndex((prevIndex) => (prevIndex + 1) % alerts.length);

          // Reset transition state
          setTimeout(() => {
            setIsTransitioning(false);
            setProgress(100);
          }, 200);
        }, 1000);
      }, 6000);

      // Restart progress animation
      progressIntervalRef.current = setInterval(() => {
        if (!isPaused) {
          setProgress((prevProgress) => {
            const newProgress = prevProgress - 1.67;
            return newProgress < 0 ? 0 : newProgress;
          });
        }
      }, 100);
    }, 1000);
  };

  // The transition classes for sliding in/out
  const alertTransitionClass = isTransitioning
    ? "opacity-0 translate-y-[-20px]"
    : "opacity-100 translate-y-0";

  // The visibility class for auto-hiding
  const visibilityClass = isVisible
    ? "translate-y-0 opacity-100"
    : "translate-y-[-100%] opacity-0";

  return (
    <div
      ref={tickerRef}
      className={`fixed top-0 left-0 right-0 z-50 bg-red-600 text-white overflow-hidden transition-transform duration-300 ease-in-out ${visibilityClass}`}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Progress indicator */}
      {alerts.length > 1 && (
        <div className="absolute bottom-0 left-0 w-full h-0.5 bg-red-800">
          <div
            className="h-full bg-white transition-all duration-100 ease-linear"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      )}

      <div className="container mx-auto h-full">
        <div className="flex items-center justify-between h-full">
          <div
            className="flex-grow overflow-hidden relative h-full flex items-center"
            style={{ minHeight: "32px" }}
          >
            <div
              className={`
                absolute inset-0 flex items-center
                transition-all duration-1000 cubic-bezier(0.34, 1.56, 0.64, 1)
                ${alertTransitionClass}
              `}
            >
              <span className="font-bold mr-3 text-white bg-red-700 px-3 py-1 rounded">
                ALERT
              </span>
              <Link
                to={`/bills/${currentAlert.id}`}
                className="text-white hover:underline truncate flex-grow ml-2"
              >
                {currentAlert.title}
                <span className="mx-2">|</span>
                {currentAlert.description}
              </Link>
            </div>
          </div>

          <div className="flex items-center ml-4 flex-shrink-0">
            {alerts.length > 1 && (
              <div className="flex items-center space-x-3 mr-4">
                {alerts.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => goToAlert(index)}
                    className={`h-2.5 w-2.5 rounded-full transition-all duration-500 ${
                      index === currentAlertIndex
                        ? "bg-white scale-125"
                        : "bg-white bg-opacity-50 hover:bg-opacity-75"
                    }`}
                    aria-label={`View alert ${index + 1} of ${alerts.length}`}
                  />
                ))}
              </div>
            )}

            <Link
              to="/alerts"
              className="whitespace-nowrap text-white hover:underline text-sm font-medium border-l border-white pl-4"
            >
              View All Alerts →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AlertTicker;
