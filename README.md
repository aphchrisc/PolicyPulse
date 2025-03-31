# PolicyPulse: AI-Powered Legislative Analysis Platform

## Overview

PolicyPulse is a sophisticated application designed to track, analyze, and provide insights on legislation, with a focus on its potential impact on public health and local government. It leverages external data sources like LegiScan, employs AI (OpenAI) for in-depth analysis of legislative text (including PDFs), and presents findings through an intuitive web interface.

This platform aims to empower public health officials, local government staff, researchers, and advocates by providing timely, relevant, and actionable intelligence on legislative developments.

## Core Features

*   **Automated Legislation Tracking:** Regularly fetches new and updated bills from sources like LegiScan for monitored jurisdictions (US, TX).
*   **AI-Powered Analysis:** Analyzes bill text and PDFs to generate structured summaries, identify key points, assess potential impacts (public health, local government, economic, etc.), and determine relevance.
*   **Interactive Dashboard:** Provides a high-level overview of legislative activity, key analyses, and trends.
*   **Bill Discovery & Details:** Allows users to browse, filter, and view detailed information about specific bills, including text, status, history, sponsors, and AI analysis.
*   **Alerts:** Notifies users about significant events or bills matching their interests (partially implemented).
*   **(Planned/Pending):** Advanced Search, User Accounts & Preferences, Bookmarking, Data Export, Email-based Alert Notifications.

## Architecture Overview

PolicyPulse employs a modular architecture consisting of several key components:

1.  **Frontend (`/src`):** A React-based Single Page Application (SPA) built with Vite and styled using Tailwind CSS. It provides the user interface for interacting with the platform. See [Frontend Documentation](./README_frontend.md) for details.
2.  **Backend API (`/app/api`):** A FastAPI application serving as the central hub. It exposes RESTful endpoints for the frontend to consume data and trigger actions.
3.  **Data Acquisition (`/app/legiscan`):** Handles fetching and processing data from the LegiScan API.
4.  **AI Analysis Engine (`/app/ai_analysis`):** Orchestrates the analysis of legislation using OpenAI models, including text preprocessing, chunking for large documents, PDF analysis (vision-enabled), and structuring the output.
5.  **Data Storage (`/app/models`, `/app/data`, `/db`):** Uses PostgreSQL with SQLAlchemy ORM to store legislation, analysis results, user data, and application metadata. See [Data Model Documentation](./README_data.md) for details.
6.  **Background Scheduler (`/app/scheduler`):** Uses APScheduler to run recurring tasks like data synchronization with LegiScan and triggering AI analysis jobs.

For a detailed breakdown of the backend components and workflows, see the [Backend Documentation](./README_Backend.md). Architectural notes and potential improvements are captured in [Architecture Notes](./docs/architecture_notes.md).

## Technology Stack

*   **Frontend:** React, Vite, React Router, Axios, Tailwind CSS, React Context API
*   **Backend:** Python, FastAPI, Uvicorn
*   **Database:** PostgreSQL, SQLAlchemy
*   **AI:** OpenAI API (GPT-4o series)
*   **Scheduling:** APScheduler
*   **Data Source:** LegiScan API
*   **(Planned):** Docker (for containerization)

## Current Project Status (As of March 30, 2025)

The PolicyPulse project is currently **in active development**.

**Completed / Functional:**

*   **Backend:**
    *   LegiScan data fetching and storage pipeline.
    *   Core AI analysis pipeline (text & PDF processing, chunking, structured output).
    *   Database schema and models for core entities.
    *   Background scheduler for sync and maintenance jobs.
    *   FastAPI application structure with core routes.
*   **Frontend:**
    *   Core application structure (Routing, Context Providers).
    *   API service layer (`axios` integration).
    *   Main Dashboard page (`/dashboard`).
    *   Bill Listing page (`/bills`) with basic filtering.
    *   Bill Detail page (`/bills/:billId`) displaying bill info and analysis.
    *   Alerts page (`/alerts`) UI structure.
    *   UI styling largely implemented with Tailwind CSS.

**Pending / To Be Completed:**

*   **Frontend Features:**
    *   Advanced Search functionality.
    *   Full User Features (Authentication, Profiles - * planned*).
    *   Bookmarking functionality.
    *   User Preferences page implementation (linking to context/API).
    *   Data Export feature implementation (`/export`).
    *   UI Tweaks & Refinements across components.
    *   Day/Night Mode (Dark/Light theme switching).
    *   Functional Dashbaord Widgets (using mock data for placement)
*   **Backend Features:**
    *   Full Alerts System: Implementing logic for matching user preferences (`alert_preferences`) to new bills/updates and triggering notifications (e.g., **emailing users**). Requires integration with an email service.
    *   User Authentication & Authorization endpoints (if user features are planned).
    *   API endpoints to support pending frontend features (Search, Bookmarks, Preferences, Export).
*   **Infrastructure:**
    *   **Containerization:** The application needs to be containerized using Docker (creating `Dockerfile`s for frontend and backend, `docker-compose.yml` for local development/deployment).
    *   Deployment strategy definition.
*   **Testing:** Comprehensive unit, integration, and end-to-end tests need to be developed/expanded.
*   **Documentation:** Ongoing updates to documentation as features are added/changed.

## Getting Started

This section provides basic steps. Refer to the specific README files linked below for detailed setup instructions.

1.  **Prerequisites:** Python 3.x, Node.js & npm/yarn, PostgreSQL server.
2.  **Clone Repository:** `git clone <repository-url>`
3.  **Environment Variables:** Create `.env` files for both backend (`./.env`) and frontend (`./src/.env` or similar, depending on frontend setup) based on the respective `.env.example` or `.env.template` files. Populate necessary values (Database URL, API Keys, etc.).
4.  **Backend Setup:** See [Backend Documentation](./README_Backend.md#getting-started--development).
5.  **Frontend Setup:** See [Frontend Documentation](./README_frontend.md#7-getting-started-for-new-developers).
6.  **Database Setup:** See [Data Model Documentation](./README_data.md#4-database-connection--setup) and [Database Setup Guide](./docs/DATABASE_SETUP.md).
7.  **Run:** Start the backend API server and the frontend development server as described in their respective READMEs. Start the backend scheduler (`python app/run_scheduler.py`) if needed for background tasks.

## Further Documentation

*   **Backend Details:** [README_Backend.md](./README_Backend.md)
*   **Frontend Details:** [README_frontend.md](./README_frontend.md)
*   **Data Model Details:** [README_data.md](./README_data.md)
*   **Database Setup:** [docs/DATABASE_SETUP.md](./docs/DATABASE_SETUP.md)
*   **Architecture Notes:** [docs/architecture_notes.md](./docs/architecture_notes.md)
*   **(Other docs in `/docs` as available)**