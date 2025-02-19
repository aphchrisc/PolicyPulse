# Congress Legislation Monitor – Developer Springboard

Welcome to the Congress Legislation Monitor project! This prototype is designed as a hands-on starting point for developers and policy analysts who want to explore, deploy, and extend a legislative monitoring tool. It integrates live data from Congress.gov, leverages AI for detailed legislative analysis, and offers a modern Streamlit-based UI for easy browsing, analysis, and maintenance. While many features work well, some parts are a bit rough around the edges and may require further refinement. Consider this project your springboard for building something truly great.

---

## Table of Contents

- [Overview](#overview)
- [Key Components](#key-components)
  - [AI Processing](#ai-processing)
  - [Alert System](#alert-system)
  - [Congress.gov API Integration](#congressgov-api-integration)
  - [Streamlit UI & Main Application](#streamlit-ui--main-application)
  - [Utilities & Testing](#utilities--testing)
- [Database Model & Data Structures](#database-model--data-structures)
- [Getting Started](#getting-started)
- [Deployment & Configuration](#deployment--configuration)
- [Potential Improvements](#potential-improvements)
- [Final Notes](#final-notes)

---

## Overview

The Congress Legislation Monitor is a prototype application that:
- **Fetches and displays legislative data:** Uses the Congress.gov API to pull recent bills, complete with details such as bill number, title, sponsors, and actions.
- **Analyzes legislation using AI:** Processes bill text (or summaries) via an AI module that generates structured analyses and impact assessments on public health and local government.
- **Sends alerts:** Provides an email alert mechanism to notify users of new or updated legislation.
- **Offers an interactive UI:** Built with Streamlit, the application presents tabs for the latest legislation, search history, an analysis dashboard, and database maintenance functions.

This project is ideal for those looking to deploy a real-world legislative tracking tool, learn from its design, or repurpose parts of it for their own custom solutions.

---

## Key Components

### AI Processing
- **File:** [ai_processor.py](&#8203;:contentReference[oaicite:0]{index=0})
- **Purpose:**  
  - Uses OpenAI's API to analyze legislative texts.
  - Generates detailed JSON analyses including summaries, key points, and impact assessments.
  - Contains helper functions to extract JSON from responses and update the database with impact levels.
- **Notes:**  
  - The AI analysis is tailored to focus on public health and local government impacts.
  - Some API interactions (e.g., token limits, formatting) are implemented in a rudimentary way—refinement may be needed for production use.

### Alert System
- **File:** [alert_system.py](&#8203;:contentReference[oaicite:1]{index=1})
- **Purpose:**  
  - Manages email alerts via SMTP.
  - Formats legislation update emails in HTML.
  - Provides basic functionality for updating and sending alerts.
- **Notes:**  
  - Currently, the email update function is simplistic. Real-world usage might require robust email validation and error handling.

### Congress.gov API Integration
- **File:** [congress_api.py](&#8203;:contentReference[oaicite:2]{index=2})
- **Purpose:**  
  - Retrieves legislation data and full bill texts from Congress.gov.
  - Implements rate limiting, error handling, and data formatting.
  - Supports saving detailed bill data to a database.
- **Notes:**  
  - The API calls include progress tracking and resume capability.
  - Some endpoints and error conditions might be improved for reliability.

### Streamlit UI & Main Application
- **File:** [main.py](&#8203;:contentReference[oaicite:3]{index=3})
- **Purpose:**  
  - Provides the user interface for exploring and analyzing legislation.
  - Implements multiple tabs: Latest Legislation, Search History, Analysis Dashboard, and Database Maintenance.
  - Integrates the API, AI processor, and alert system.
- **Notes:**  
  - The sidebar is minimal, focusing solely on search functionality.
  - The design aims to be both informative and interactive, though some UI components may require polishing.

### Utilities & Testing
- **Utilities:**  
  - **File:** [utils.py](&#8203;:contentReference[oaicite:4]{index=4})  
    - Contains helper functions such as custom CSS loading for Streamlit.
- **Testing:**  
  - **File:** [test_congress_api.py](&#8203;:contentReference[oaicite:5]{index=5})  
    - Provides basic tests for ensuring connectivity with the Congress.gov API.
- **Notes:**  
  - Testing is currently minimal and intended as a starting point. Expanding test coverage is recommended.

---

## Database Model & Data Structures

The application uses SQLAlchemy to interact with a relational database. With the updated `models.py` file, the schema has been expanded to manage not only legislative data but also user preferences and search history. Below are the key models and their roles:

### User Model
- **Purpose:** Stores user account details.
- **Fields:**  
  - `id`: Primary key.
  - `email`: Unique email address.
  - Relationships:
    - `preferences`: Links to a single `UserPreference`.
    - `searches`: A list of `SearchHistory` records for the user.

### UserPreference Model
- **Purpose:** Keeps user-specific settings.
- **Fields:**  
  - `id`: Primary key.
  - `user_id`: Foreign key linking to a User.
  - `keywords`: A JSON field storing an array of preferred keywords.
  - Timestamps: `created_at` and `updated_at` for tracking changes.

### SearchHistory Model
- **Purpose:** Logs user search queries and their results.
- **Fields:**  
  - `id`: Primary key.
  - `user_id`: Foreign key linking to a User.
  - `query`: The search query string.
  - `timestamp`: When the search was made.
  - `results`: A JSON field storing the search results.

### LegislationTracker Model
- **Purpose:** Tracks all details related to a bill.
- **Core Fields:**
  - **Identifiers:**  
    - `congress`: The congress number.
    - `bill_type`: The type of bill (e.g., H.R., S.).
    - `bill_number`: Unique bill identifier.
  - **Metadata:**  
    - `title`: Bill title.
    - `status`: A summary of the bill’s current state, typically including the latest action date and text.
    - `introduced_date`: Date the bill was introduced.
  - **Impact & Analysis:**  
    - `public_health_impact` and `local_gov_impact`: Impact levels (default is 'unknown').
    - `public_health_reasoning` and `local_gov_reasoning`: Textual explanations for the impact assessments.
    - `analysis`: A JSON field storing AI-generated analysis (including executive summary, key points, and detailed impact analysis).
    - `analysis_timestamp`: When the analysis was performed.
  - **Content Fields:**  
    - `raw_api_response`: Full API response stored as JSON.
    - `bill_text`: Full text or summary of the bill.
  - **Timestamps:**  
    - `first_stored_date`: When the bill was first added.
    - `last_api_check`: Timestamp for the last API update check.
    - `last_updated`: Timestamp for the latest record update.
- **Unique Constraint:**  
  - Enforced on the combination of `congress`, `bill_type`, and `bill_number` to prevent duplicate entries.

### DataStore Class
- **Purpose:** Provides a higher-level API for interacting with the database.
- **Capabilities:**  
  - Flushing the `LegislationTracker` table.
  - Retrieving bills that have not yet been analyzed.
  - Checking for updates on bills that haven’t been recently verified.
- **Usage:**  
  - The `DataStore` class is used throughout the application (in the UI and API modules) to encapsulate database operations.

These models and data structures form the backbone of the application, allowing seamless data retrieval, storage, and analysis while also maintaining user-specific settings and search history.

---

## Getting Started

1. **Clone the Repository**  
   *(Note: Specific terminal commands are omitted to keep formatting intact.)*

2. **Set Up a Virtual Environment and Install Dependencies**  
   Ensure you have Python 3.8+ installed and set up your environment accordingly.

3. **Configure Environment Variables**  
   The project requires environment variables for:
   - OpenAI API key
   - Congress.gov API key
   - SMTP credentials for email alerts
   - `DATABASE_URL` for database connectivity (with SSL settings)

4. **Initialize the Database**  
   Make sure the database (configured via SQLAlchemy) is set up. Run any necessary migration or initialization routines.

5. **Run the Application**  
   Launch the Streamlit application to start exploring legislative data and AI analysis.

6. **Run Tests**  
   Basic tests for API connectivity are provided to ensure the system works as expected.

---

## Deployment & Configuration

- **Local Deployment:**  
  Follow the setup instructions to run the application on your local machine.
  
- **Production Deployment:**  
  Consider containerizing the application (e.g., using Docker), securely managing environment variables, and using a robust production database.
  
- **Scheduler Integration:**  
  For automatic updates and background processing, integrate a scheduling mechanism (such as cron jobs or Celery workers).

---

## Potential Improvements

- **Enhanced Error Handling:**  
  Improve logging and error management for external API calls and database operations.
- **Refactor Cludgey Parts:**  
  Refine the API integration and AI processing modules for better performance and maintainability.
- **UI/UX Polishing:**  
  Further refine the Streamlit interface for a more intuitive and polished user experience.
- **Expanded Testing & CI/CD:**  
  Increase test coverage and integrate continuous integration pipelines.
- **Modularization:**  
  Break down larger modules into smaller, more maintainable components.

