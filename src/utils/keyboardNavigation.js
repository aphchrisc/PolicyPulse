/**
 * Utility to handle keyboard navigation and focus management
 */

/**
 * Initialize keyboard navigation detection
 * This adds a class to the body when mouse is used and removes it when keyboard is used
 */
export const initKeyboardNavigation = () => {
  // Add event listeners to detect keyboard vs mouse navigation
  document.body.addEventListener('mousedown', () => {
    document.body.classList.add('using-mouse');
  });

  document.body.addEventListener('keydown', (event) => {
    // Only remove the class if Tab key is pressed
    if (event.key === 'Tab') {
      document.body.classList.remove('using-mouse');
    }
  });

  // Add skip to content link
  addSkipToContentLink();
};

/**
 * Add a skip to content link for keyboard navigation
 */
const addSkipToContentLink = () => {
  // Check if the link already exists
  if (document.querySelector('.skip-to-content')) {
    return;
  }

  // Create the skip link
  const skipLink = document.createElement('a');
  skipLink.href = '#main-content';
  skipLink.className = 'skip-to-content';
  skipLink.textContent = 'Skip to content';
  
  // Add the link to the beginning of the body
  document.body.insertBefore(skipLink, document.body.firstChild);
  
  // Add id to the main content if it doesn't exist
  const mainContent = document.querySelector('main');
  if (mainContent && !mainContent.id) {
    mainContent.id = 'main-content';
  }
};

/**
 * Focus trap for modals and dialogs
 * @param {HTMLElement} element - The element to trap focus within
 * @returns {Function} - Function to remove the focus trap
 */
export const createFocusTrap = (element) => {
  // Find all focusable elements
  const focusableElements = element.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  
  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];
  
  // Focus the first element
  if (firstElement) {
    firstElement.focus();
  }
  
  // Handle tab key to trap focus
  const handleKeyDown = (event) => {
    if (event.key === 'Tab') {
      // Shift + Tab
      if (event.shiftKey) {
              if (document.activeElement === firstElement) {
                event.preventDefault();
                lastElement.focus();
              }
            }
      else if (document.activeElement === lastElement) {
                event.preventDefault();
                firstElement.focus();
              }
    }
    
    // Close on Escape
    if (event.key === 'Escape') {
      // Dispatch a custom event that components can listen for
      element.dispatchEvent(new CustomEvent('escape-key-pressed'));
    }
  };
  
  // Add event listener
  element.addEventListener('keydown', handleKeyDown);
  
  // Return function to remove the focus trap
  return () => {
    element.removeEventListener('keydown', handleKeyDown);
  };
};

/**
 * Set focus to an element when it mounts
 * @param {React.RefObject} ref - React ref object for the element
 */
export const setFocusOnMount = (ref) => {
  if (ref.current) {
    ref.current.focus();
  }
};

/**
 * Restore focus to a previously focused element
 * @param {HTMLElement} previouslyFocusedElement - Element to restore focus to
 */
export const restoreFocus = (previouslyFocusedElement) => {
  if (previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') {
    previouslyFocusedElement.focus();
  }
}; 