# PolicyPulse Frontend Documentation

## 1. Overview

This document provides a comprehensive overview of the PolicyPulse frontend application located in the `/src` directory. It's intended for developers joining the project to understand its structure, core concepts, technologies, and how different parts interact.

The frontend is a single-page application (SPA) built using React and Vite. It interacts with a backend API to fetch, display, and manage legislative data and analysis.

## 2. Technology Stack

The core technologies used in the frontend are:

-   **React**: Core UI library (v18+).
-   **React Router DOM**: Client-side routing and navigation (v6).
-   **Axios**: HTTP client for making API requests.
-   **Tailwind CSS**: Utility-first CSS framework for styling.
-   **Vite**: Frontend build tool and development server.
-   **React Context API**: For global state management across the application.
-   **React Toastify**: Library for displaying toast notifications.
-   **(Prop-Types)**: Used for runtime prop type checking (consider migrating to TypeScript for static typing).

## 3. Project Structure

The `/src` directory is organized into the following main subdirectories:

```
src/
├── App.jsx                 # Main application component (routing, context providers, layout structure)
├── index.css               # Global CSS styles (Tailwind base, custom styles)
├── main.jsx                # Application entry point (React root rendering, global setup, error handling)
├── components/             # Reusable UI components, organized by feature/domain
│   ├── accessibility/      # Accessibility-related components (e.g., buttons, panels)
│   ├── alerts/             # Alert components (e.g., AlertTicker)
│   ├── analysis/           # Components for displaying bill analysis data
│   ├── bills/              # Components related to bill lists, search, filters, details
│   ├── bookmarks/          # Components for managing bookmarks
│   ├── dashboard/          # Components specific to the main dashboard view
│   ├── export/             # Components related to data export features
│   ├── filters/            # Reusable filter components (e.g., date range)
│   ├── icons/              # SVG icon components
│   ├── navigation/         # Navigation components (e.g., Breadcrumbs)
│   ├── notifications/      # Notification center and item components
│   ├── ui/                 # Generic, reusable UI elements (Card, Button, ErrorDisplay, LoadingOverlay)
│   └── visualizations/     # Data visualization components (charts, graphs)
├── context/                # React Context providers for global state management
│   ├── AccessibilityContext.jsx
│   ├── AlertContext.jsx
│   ├── BookmarkContext.jsx
│   ├── NotificationContext.jsx
│   └── UserPreferencesContext.jsx
├── hooks/                  # Custom React Hooks for reusable stateful logic
│   └── useDashboardData.js # Example hook for fetching dashboard data
├── pages/                  # Top-level page components corresponding to application routes
│   ├── AlertsPage.jsx
│   ├── BillDetail.jsx
│   ├── BillsPage.jsx
│   ├── BookmarksPage.jsx
│   ├── Dashboard.jsx
│   ├── ExportDashboard.jsx
│   ├── LandingPage.jsx
│   ├── NotFound.jsx
│   ├── StatusPage.jsx
│   └── UserPreferences.jsx
├── services/               # Modules for interacting with the backend API and other external services
│   ├── api.js              # Axios instance setup, interceptors, core API endpoint functions, billService
│   ├── apiEndpointService.js # Service for API status checks (likely related to StatusPage)
│   ├── billFilters.js      # Utilities related to bill filtering logic
│   └── visualizationService.js # API calls specific to visualizations
├── styles/                 # Additional CSS files or styling assets
│   └── screenReaderOptimizations.css # Specific styles targeting screen readers
└── utils/                  # Utility functions and helpers
    ├── helpers.js          # General helper functions
    ├── keyboardNavigation.js # Keyboard navigation utilities
    ├── logger.js           # Client-side logging utility
    ├── propTypes.js        # Shared PropTypes definitions (consider replacing with TypeScript)
    ├── statusUtils.js      # Utilities for handling bill statuses
    └── unusedUtils.js      # Potentially deprecated utilities (review and remove if necessary)
```

## 4. Application Flow & Key Components

### 4.1 Initialization Flow

1.  The application starts in `src/main.jsx`. This file:
    *   Renders the main `App` component into the DOM (`#root`).
    *   Imports global CSS (`index.css`, `screenReaderOptimizations.css`).
    *   Sets up global JavaScript error handlers (uncaught errors, unhandled promise rejections) that log via the `logger` utility.
    *   Includes a basic fallback UI if the initial React render fails catastrophically.
2.  `src/App.jsx` takes over and sets up the main application structure:
    *   Initializes and manages the API health check state (`apiStatus`).
    *   Defines the application's routes using `createBrowserRouter` from `react-router-dom`.
    *   Wraps the entire application in necessary global Context Providers (`UserPreferencesProvider`, `NotificationProvider`, `BookmarkProvider`, `AccessibilityProvider`, `AlertProvider`).
    *   Includes accessibility features like a "Skip to content" link.
    *   Renders the `RouterProvider` to enable routing.
    *   Renders the `ToastContainer` for displaying notifications.

### 4.2 Key Component Types

-   **Entry Points:**
    -   `main.jsx`: Initializes React, sets up global error handling.
    -   `App.jsx`: Configures routing, context providers, API health checks, and overall app structure.
-   **Layout Components:**
    -   `components/Layout.jsx`: Provides the consistent page structure (header, sidebar, main content area, footer) used by most pages.
    -   `Root` (defined within `App.jsx`): Wraps the main `Outlet` for routes and includes elements outside the standard layout, like the `AlertTicker`.
-   **Page Components (`src/pages/`):** Top-level components rendered by the router for specific URL paths. They orchestrate data fetching and compose feature/UI components.
-   **Feature Components (`src/components/[feature]/`):** Components specific to a particular domain or feature (e.g., `components/bills/BillListCards.jsx`, `components/analysis/AnalysisDashboard.jsx`).
-   **Common/UI Components (`src/components/ui/`):** Generic, reusable UI elements like buttons, cards, loading indicators, error displays.

## 5. Core Concepts

### 5.1 Routing

-   **Library:** `react-router-dom` v6.
-   **Configuration:** Defined in `src/App.jsx` using `createBrowserRouter`.
-   **Structure:** Routes map URL paths (e.g., `/dashboard`, `/bills/:billId`) to components in `src/pages/`.
-   **Layout:** Most page routes are nested within the `Layout` component for consistent UI.
-   **Not Found:** A wildcard route `*` redirects to `/404`, rendering `src/pages/NotFound.jsx`.
-   **Key Routes:**
    -   `/`: Landing page
    -   `/status`: API status information
    -   `/dashboard`: Main dashboard view
    -   `/bills`: Bill listing page
    -   `/bills/:billId`: Bill detail page
    -   `/bookmarks`: User's bookmarked items
    -   `/alerts`: Alerts and notifications page
    -   `/preferences`: User preference settings
    -   `/export`: Data export functionality

### 5.2 State Management

-   **Local State:** Managed within individual components using React hooks like `useState` and `useReducer`.
-   **Global State:** Managed via React Context API for state needed across different parts of the application. Providers are defined in `src/context/` and wrapped in `src/App.jsx`.
    -   `UserPreferencesContext`: Manages user settings (e.g., theme).
    -   `NotificationContext`: Manages application-wide notifications (integrates with `react-toastify`).
    -   `BookmarkContext`: Stores and manages user's bookmarked bills.
    -   `AccessibilityContext`: Manages accessibility-related state/settings (e.g., font size, contrast).
    -   `AlertContext`: Manages system-level alerts displayed in the `AlertTicker`.

### 5.3 Data Fetching & API Integration

-   **Library:** `axios` for making HTTP requests.
-   **Central Service (`src/services/api.js`):**
    -   Configures a central Axios instance (`api`) with base URL (`/api`), headers, timeout, and interceptors.
    -   The `/api` base URL ensures requests use the Vite proxy in development.
    -   Interceptors log request/response details (dev only) and handle basic error logging.
    -   Exports functions for specific API endpoints (e.g., `getLegislation`, `getLegislationById`, `searchLegislationAdvanced`, `getImpactSummary`, `healthCheck`).
    -   Includes robust error handling and data normalization logic, especially in `getLegislationById`.
    -   Provides a `billService` object aggregating common bill and dashboard-related API calls.
-   **Data Fetching Pattern:**
    1.  Components (often page components) initiate data fetching, typically within `useEffect` hooks or via custom hooks.
    2.  Custom hooks (`src/hooks/`) or components call functions from API services (`src/services/`).
    3.  Loading states are managed (e.g., using `useState`) and displayed to the user (spinners, skeletons).
    4.  API services make requests using the configured Axios instance.
    5.  Responses are processed; data might be transformed or normalized within the service or component.
    6.  Fetched data is stored in component state or global context.
    7.  Error states are handled, displaying appropriate messages or fallback UI.
-   **API Health Check:** `src/App.jsx` periodically calls the `healthCheck` service function to monitor backend availability and updates the `apiStatus` state, which can be used by components.

### 5.4 Styling

-   **Framework:** Tailwind CSS. Configuration is in `tailwind.config.js` and `postcss.config.js`.
-   **Implementation:** Primarily uses Tailwind utility classes directly within JSX elements.
-   **Global Styles:** Base Tailwind styles and custom global styles are defined in `src/index.css`.
-   **Specific Styles:** Additional CSS files like `src/styles/screenReaderOptimizations.css` provide targeted styles.

### 5.5 Logging

-   A simple `logger` utility (`src/utils/logger.js`) provides `info`, `warn`, `error`, and `debug` methods, wrapping `console` calls.
-   Used throughout the application (entry point, App component, services) for debugging and monitoring.

### 5.6 Error Handling

Error handling is implemented at multiple levels:

-   **Global:** `main.jsx` catches uncaught JavaScript errors and unhandled promise rejections. React Error Boundaries could be added for component-level UI safety.
-   **API Layer (`services/api.js`):** Axios interceptors log network/HTTP errors. Specific service functions include `try...catch` blocks for handling errors during API calls, sometimes with retry logic (`fetchLegislationAnalysis`) or data normalization fallbacks (`getLegislationById`).
-   **Component Level:** Components manage loading and error states (e.g., using `useState`). Conditional rendering displays loading indicators or error messages (`components/ui/LoadingOverlay.jsx`, `components/ui/ErrorDisplay.jsx`).

### 5.7 Accessibility (A11y)

The application aims to be accessible, incorporating features like:

-   Semantic HTML.
-   ARIA attributes where appropriate.
-   Keyboard navigation support (`utils/keyboardNavigation.js`).
-   "Skip to content" link (`App.jsx`).
-   Screen reader specific styles (`styles/screenReaderOptimizations.css`).
-   Accessibility panel (`components/accessibility/`) likely controlled via `AccessibilityContext` for features like font size adjustment and high contrast modes.

## 6. Key Features Overview

-   **Dashboard (`/dashboard`):** Provides a high-level overview with summary cards, impact visualizations, trending topics, and recent activity feeds. Uses `useDashboardData` hook and components from `src/components/dashboard/`.
-   **Bill Discovery (`/bills`):** Allows users to browse, search (basic and advanced), and filter legislation. Uses components like `BillListCards`, `BillFilters`, `Pagination`.
-   **Bill Details (`/bills/:billId`):** Displays comprehensive information about a specific bill, including its text, status, history, sponsors, and AI-generated analysis. Composes various components from `src/components/analysis/` and `src/components/ui/`.
-   **Bookmarks (`/bookmarks`):** Allows users to save and manage bills of interest, managed via `BookmarkContext`.
-   **Alerts (`/alerts`, `AlertTicker`):** Notifies users about important updates or system events, managed via `AlertContext`.
-   **User Preferences (`/preferences`):** Allows users to customize their experience (e.g., theme), managed via `UserPreferencesContext`.
-   **Data Export (`/export`):** Provides functionality to export data (e.g., analysis reports).

## 7. Getting Started for New Developers

1.  **Setup:**
    *   Clone the repository.
    *   Install dependencies: `npm install` or `yarn install`.
    *   Set up environment variables: Copy `.env.example` to `.env` and fill in necessary values (especially `VITE_API_BASE_URL` for the backend).
    *   Run the development server: `npm run dev` or `yarn dev`.
2.  **Understanding the Codebase:**
    *   Start with `src/main.jsx` and `src/App.jsx` to grasp the application setup and routing.
    *   Explore the `src/pages/` directory to see how different routes are handled.
    *   Examine `src/services/api.js` to understand backend interaction.
    *   Review the providers in `src/context/` to understand global state.
    *   Pick a feature (e.g., Bill Details page) and trace the data flow from the page component through hooks/services to the UI components.
3.  **Making Changes:**
    *   Follow existing file structure and naming conventions.
    *   Create reusable components in `src/components/` organized by feature or UI type.
    *   Utilize Tailwind CSS for styling.
    *   Add API interactions via `src/services/api.js` or specific service files.
    *   Use Context API for state shared across multiple components.
    *   Write clear, commented code.
4.  **Testing Changes:**
    *   Verify functionality across different browsers (if applicable).
    *   Test different user flows and edge cases.
    *   Check responsiveness on various screen sizes.
    *   Ensure API interactions handle loading and error states gracefully.
    *   Test with the backend API running and simulate offline/error scenarios if possible.
    *   Perform basic accessibility checks (keyboard navigation, color contrast).

## 8. Building for Production

-   Run `npm run build` (or `yarn build`).
-   This command uses Vite to bundle the application, optimize assets, and output the static files to the `dist/` directory.
-   The contents of `dist/` can then be deployed to a static file server or hosting platform.

## 9. Conclusion

This frontend architecture utilizes modern React practices, emphasizing modularity, reusability, and clear separation of concerns. State management is handled through a combination of local state and the Context API, while API interactions are centralized in a service layer. Tailwind CSS provides efficient styling, and Vite enables a fast development experience. This structure should provide a solid foundation for ongoing development and maintenance.