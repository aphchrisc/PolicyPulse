# PolicyPulse Data Model Documentation

This document provides an overview of the PolicyPulse backend data model, storage mechanisms, and key considerations for developers, particularly those involved in data engineering tasks like integrating new data sources.

## Table of Contents

- [1. Overview](#1-overview)
- [2. Database Architecture](#2-database-architecture)
- [3. Data Models (ORM)](#3-data-models-orm)
- [4. Database Connection & Setup](#4-database-connection--setup)
- [5. Data Access Layer (DAL)](#5-data-access-layer-dal)
- [6. Existing API Integrations (LegiScan)](#6-existing-api-integrations-legiscan)
- [7. Data Flow](#7-data-flow)
- [8. Integrating New Data Sources](#8-integrating-new-data-sources)
- [9. Development Guidelines](#9-development-guidelines)
- [10. Other Considerations](#10-other-considerations)


## 1. Overview

The PolicyPulse database is designed to store, manage, and analyze legislative information, focusing on its potential impact on public health and local governments. It uses PostgreSQL as the underlying database technology and SQLAlchemy as the Object-Relational Mapper (ORM) in the Python backend.

The core goals of the data model are:
*   **Store comprehensive legislative data:** Capture details about bills, their text, sponsors, amendments, and status updates.
*   **Track data provenance:** Identify the source of the data (e.g., Legiscan, Congress.gov).
*   **Manage versions:** Keep track of different versions of bill text and AI analysis results.
*   **Facilitate analysis:** Store structured AI analysis outputs, impact ratings, and prioritization scores.
*   **Enable efficient querying:** Support searching, filtering, and retrieval of legislation based on various criteria, including full-text search.

## 2. Database Architecture

PolicyPulse uses a PostgreSQL database. The schema is defined in `db/policypulse_schema.sql`.

### Key Database Features

*   **PostgreSQL Extensions**: The application utilizes `pg_trgm` for trigram-based text search and `unaccent` for accent-insensitive search (enabled via `CREATE EXTENSION IF NOT EXISTS ...`).
*   **Custom ENUM Types**: Several custom ENUM types are defined in the schema to ensure data consistency for specific fields:
    *   `data_source_enum`: ('legiscan', 'congress_gov', 'other')
    *   `govt_type_enum`: ('federal', 'state', 'county', 'city')
    *   `bill_status_enum`: ('new', 'introduced', 'updated', 'passed', 'defeated', 'vetoed', 'enacted', 'pending')
    *   `impact_level_enum`: ('low', 'moderate', 'high', 'critical')
    *   `impact_category_enum`: ('public_health', 'local_gov', 'economic', 'environmental', 'education', 'infrastructure', 'healthcare', 'social_services', 'justice')
    *   `amendment_status_enum`: ('proposed', 'adopted', 'rejected', 'withdrawn')
    *   `notification_type_enum`: ('high_priority', 'new_bill', 'status_change', 'analysis_complete')
    *   `sync_status_enum`: ('pending', 'in_progress', 'completed', 'failed', 'partial')
*   **Full-Text Search**: Implemented using a `search_vector` column on the `legislation` table (updated by a trigger) and a GIN index.
*   **Indexing**: Strategic indexes are defined on various tables to optimize common query patterns (e.g., filtering by status, dates, relevance scores).
*   **Constraints**: Unique constraints ensure data integrity (e.g., `unique_bill_identifier`).
*   **Audit Fields & Triggers**: Most tables include `created_at` and `updated_at` fields, automatically managed by the `update_modified_column()` trigger function.

## 3. Data Models (ORM)

The application uses SQLAlchemy ORM for database interactions. Models are defined in Python classes within the `app/models/` directory.

### Base Model & Types
*   **`BaseModel` (`app/models/base.py`):** An abstract base class providing common audit fields (`created_at`, `updated_at`, `created_by`, `updated_by`) and utility methods (like `set_content_field`) for all models.
*   **`FlexibleContentType` (`app/models/base.py`):** A custom SQLAlchemy type used in `LegislationText` and `Amendment` to handle storage of both text (TEXT) and binary (BYTEA) content within the same database column, based on the `is_binary` flag.

### Core Data Entities (Tables & Models)

The primary data entities correspond to tables in the database:

*   **`Legislation` (`legislation` table) (`app/models/legislation_models.py`):**
    *   The central entity representing a single piece of legislation (a bill).
    *   Stores core metadata: `external_id` (from the source), `data_source`, `govt_type`, `govt_source` (e.g., 'TX', 'US'), `bill_number`, `title`, `description`, `bill_status`, key dates (`bill_introduced_date`, `bill_last_action_date`), URLs (`url`, `state_link`).
    *   Includes `raw_api_response` (JSONB) to store the original data from the source API.
    *   Contains a `search_vector` (TSVector) column for full-text search on `title` and `description`.
    *   Has relationships to almost all other legislation-related tables.

*   **`LegislationText` (`legislation_text` table):**
    *   Stores the actual text content of a bill.
    *   Linked one-to-many with `Legislation`.
    *   Supports versioning via `version_num`.
    *   Handles both plain text (`text_content` as TEXT) and binary content (e.g., PDFs, stored in `text_content` as BYTEA when `is_binary` is true). The `FlexibleContentType` handles this abstraction.
    *   Stores metadata like `text_type`, `text_date`, `text_hash`, `content_type`, and `file_size`.

*   **`LegislationAnalysis` (`legislation_analysis` table):**
    *   Stores the results of AI analysis performed on legislation text.
    *   Linked one-to-many with `Legislation`.
    *   Supports versioning via `analysis_version` and links to `previous_version_id`.
    *   Stores structured analysis outputs in JSONB columns (e.g., `summary`, `key_points`, `public_health_impacts`, `local_gov_impacts`, `stakeholder_impacts`, `recommended_actions`).
    *   Includes metadata about the analysis process (`model_version`, `confidence_score`, `processing_time`).
    *   Has an `insufficient_text` flag to indicate if analysis couldn't be performed due to lack of text.

*   **`LegislationSponsor` (`legislation_sponsors` table):**
    *   Stores information about bill sponsors.
    *   Linked one-to-many with `Legislation`.

*   **`Amendment` (`amendments` table):**
    *   Stores details about amendments proposed or adopted for a bill.
    *   Linked one-to-many with `Legislation`.
    *   Includes fields for `status`, `amendment_date`, `title`, `description`, and `amendment_text` (also using `FlexibleContentType`).

*   **`LegislationPriority` (`legislation_priorities` table):**
    *   Stores relevance and priority scores (e.g., `public_health_relevance`, `local_govt_relevance`, `overall_priority`).
    *   Linked one-to-one with `Legislation`.
    *   Tracks manual review status (`manually_reviewed`, `reviewer_notes`).

*   **`ImpactRating` (`impact_ratings` table):**
    *   Stores specific, categorized impact assessments (e.g., category: 'public_health', level: 'high').
    *   Linked one-to-many with `Legislation`.
    *   Includes `impact_category`, `impact_level`, `impact_description`, `confidence_score`.

*   **`ImplementationRequirement` (`implementation_requirements` table):**
    *   Stores details about requirements for implementing the legislation if enacted.
    *   Linked one-to-many with `Legislation`.
    *   Includes `requirement_type`, `description`, `estimated_cost`, `implementation_deadline`.

*   **User Models (`app/models/user_models.py`):** Models for user accounts (`users`), preferences (`user_preferences`), search history (`search_history`), and alert settings/history (`alert_preferences`, `alert_history`).
*   **Synchronization Models (`app/models/sync_models.py`):** Models for tracking external API synchronization operations (`sync_metadata`, `sync_errors`).
*   **Enum Definitions (`app/models/enums.py`):** Contains Python `enum.Enum` classes that correspond to the database's custom ENUM types, used for type hinting and validation within the application code.

## 4. Database Connection & Setup

Database connection handling is primarily managed by modules outside the core data stores:

*   **Connection Management (`app/db_connection.py`):**
    *   Provides a `DatabaseManager` (often used as a singleton) to handle connection pooling and session creation via SQLAlchemy's `sessionmaker`.
    *   Constructs the database connection string from environment variables (`DATABASE_URL` or individual `DB_*` components).
    *   May offer utility functions for direct query execution or status checks (depending on implementation details not fully visible in stores/models).
*   **Connection Configuration:**
    *   The application typically reads database credentials from environment variables. Common variables include:
        *   `DATABASE_URL`: A single connection string.
        *   `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: Individual components if `DATABASE_URL` is not provided.
*   **Database Initialization (`db/db_setup.py`, `db/init_db.sh`, `setup_database.py`):**
    *   Scripts exist to initialize the database.
    *   These scripts typically connect to the PostgreSQL server, create the database and schema (by executing `db/policypulse_schema.sql`), potentially apply migrations (if using Alembic), and might seed initial data (like the admin user).
    *   They handle checking for existing objects (like ENUM types) to allow idempotent execution.

## 5. Key Relationships

*   `Legislation` is the central hub.
*   `Legislation` -> `LegislationText` (One-to-Many)
*   `Legislation` -> `LegislationAnalysis` (One-to-Many)
*   `Legislation` -> `LegislationSponsor` (One-to-Many)
*   `Legislation` -> `Amendment` (One-to-Many)
*   `Legislation` -> `ImpactRating` (One-to-Many)
*   `Legislation` -> `ImplementationRequirement` (One-to-Many)
*   `Legislation` -> `LegislationPriority` (One-to-One)
*   `Users` -> `UserPreferences`, `SearchHistory`, `AlertPreferences`, `AlertHistory` (One-to-Many/One)

Relationships are defined in the SQLAlchemy models (e.g., `app/models/legislation_models.py`) using `relationship()` and enforced at the database level via Foreign Keys. Cascade deletes are configured for most dependent entities.

## 6. Data Storage Details

*   **Database:** PostgreSQL.
*   **Key Data Types:**
    *   **ENUMs:** Custom enumerated types (e.g., `data_source_enum`, `bill_status_enum`, `impact_level_enum`) are defined in the schema (`db/policypulse_schema.sql`) and mapped in SQLAlchemy models (`app/models/enums.py`) for type safety and consistency.
    *   **JSONB:** Used extensively for storing semi-structured data like API responses (`raw_api_response`), analysis results (`key_points`, impact details), and user preferences. This allows flexibility in the stored data structure.
    *   **TEXT:** Used for long-form text like titles, descriptions, and summaries.
    *   **BYTEA:** Used implicitly via the `FlexibleContentType` in `LegislationText` and `Amendment` models to store binary data (like PDFs) when `is_binary` / `is_binary_text` is true.
    *   **TSVector:** The `legislation.search_vector` column stores pre-processed text from `title` and `description` for efficient full-text searching.
*   **Full-Text Search:**
    *   Implemented using PostgreSQL's built-in capabilities.
    *   A `BEFORE INSERT OR UPDATE` trigger (`tsvector_update`) automatically updates the `legislation.search_vector` column whenever the `title` or `description` changes.
    *   A GIN index (`idx_legislation_search`) is created on the `search_vector` column for fast searching.
*   **Indexing:** Various indexes are defined in `db/policypulse_schema.sql` and mirrored in model `__table_args__` to optimize common query patterns (e.g., filtering by status, dates, relevance scores).
*   **Constraints:** Unique constraints (e.g., `unique_bill_identifier` on `legislation`) ensure data integrity.

## 7. Data Access Layer (DAL)

*   **SQLAlchemy ORM:** The backend uses SQLAlchemy to map Python classes (models in `app/models/`) to database tables. This provides an object-oriented way to interact with the database.
*   **Data Stores:** Classes like `LegislationStore` (in `app/data/legislation_store.py`) encapsulate database logic for specific entities. They inherit from `BaseStore` (`app/data/base_store.py`).
*   **`BaseStore`:** Handles common tasks:
    *   Database connection management (session creation, pooling via SQLAlchemy).
    *   Connection checking and retry logic (`init_connection`, `check_connection`).
    *   Transaction management (`transaction()` context manager).
*   **`LegislationStore`:** Provides methods for:
    *   Fetching legislation lists (`list_legislation`).
    *   Getting detailed bill information (`get_legislation_details`), including related data via eager loading (`joinedload`).
    *   Performing simple keyword searches (`search_legislation_by_keywords`).
    *   Executing complex filtered and sorted searches (`search_legislation_advanced`).

## 8. Existing API Integrations (LegiScan)

The application primarily integrates with the LegiScan API to retrieve legislation data.

### LegiScan API Client (`app/legiscan/legiscan_api.py`)

The `LegiScanAPI` class (and related modules in `app/legiscan/`) provides methods for:
*   Retrieving legislative session information
*   Accessing master bill lists
*   Fetching detailed bill information
*   Retrieving bill text
*   Saving/updating bills in the database (`app/legiscan/db.py`)
*   Running synchronization operations (`app/legiscan/sync.py` - potentially, based on structure)
*   Calculating relevance scores for bills (`app/legiscan/relevance.py`)

### API Client Architecture (`app/legiscan/`)

The LegiScan module is organized into several components:
*   `api.py`: Low-level API request handling.
*   `db.py`: Database operations specific to saving/updating LegiScan data.
*   `sync.py` (or similar): Synchronization management.
*   `relevance.py`: Logic for scoring bills based on LegiScan data.
*   `models.py`: Data structures/Pydantic models for LegiScan API responses.
*   `utils.py`: Utility functions.
*   `exceptions.py`: Custom exception classes.

## 9. Data Flow

### Legislation Data Ingestion Process

1.  **API Synchronization**: The application periodically synchronizes with external legislative data sources (primarily LegiScan, likely via scheduled tasks or manual triggers). Sync status is tracked in `sync_metadata`.
2.  **Data Storage**: Retrieved legislation data is parsed and stored/updated in the `legislation` table and related tables (`legislation_text`, `legislation_sponsors`, etc.) using methods in `LegislationStore` and potentially source-specific DB modules (like `app/legiscan/db.py`).
3.  **Relevance Scoring**: New or updated legislation might be analyzed for relevance (e.g., `app/legiscan/relevance.py`) and scores stored in `legislation_priorities`.
4.  **Analysis Generation**: Relevant legislation text is queued or processed by the AI analysis pipeline (`app/ai_analysis/`), generating results stored in `legislation_analysis`.
5.  **Notification**: Based on user preferences (`alert_preferences`) and legislation priority/status changes, notifications might be generated and logged in `alert_history`.

### Data Update Process

*   **Change Detection**: Synchronization processes often use change hashes (`legislation.change_hash`) or comparison of key fields/dates to efficiently identify modified legislation from the source API.
*   **Versioning**: Changes to bill text (`legislation_text.version_num`) and analysis (`legislation_analysis.analysis_version`) are tracked with version numbers, preserving history.
*   **Audit Trail**: `created_at` and `updated_at` timestamps provide a basic audit trail for record modifications.

## 10. Integrating New Data Sources (e.g., APIs)

When adding a new source for legislative data:

1.  **Identify Key Fields:** Map the data from the new API to the columns in the `Legislation` table. Essential fields include:
    *   `external_id`: Unique ID from the new source.
    *   `data_source`: Assign a value from `DataSourceEnum` (add a new value if necessary, updating the ENUM definition in `db/policypulse_schema.sql` and `app/models/enums.py`).
    *   `govt_type`: Federal, state, etc. (`GovtTypeEnum`).
    *   `govt_source`: Abbreviation for the government body (e.g., 'CA', 'US', 'NYC').
    *   `bill_number`: The identifier used by the source (e.g., 'HB 101', 'S. 50').
    *   `title`, `description`.
    *   `bill_status` (map to `BillStatusEnum`).
    *   Relevant dates (`bill_introduced_date`, `bill_last_action_date`, `bill_status_date`).
    *   `url`, `state_link`.
2.  **Unique Constraint:** Ensure the combination of `data_source`, `govt_source`, and `bill_number` is unique to avoid duplicates (`unique_bill_identifier` constraint). Check for existing records before inserting.
3.  **Store Raw Response:** Save the complete, unmodified response from the API into the `legislation.raw_api_response` (JSONB) column for auditing and potential reprocessing.
4.  **Handle Bill Text:**
    *   If the API provides bill text (or a link to it), fetch the content.
    *   Determine if it's text or binary (e.g., PDF).
    *   Create a `LegislationText` record associated with the `Legislation` record.
    *   Use the `set_content()` method on the `LegislationText` model instance to correctly store the content (text or bytes) and set `is_binary`, `content_type`, and `file_size`.
    *   Implement versioning logic if the source provides different text versions over time (increment `version_num`). Calculate `text_hash` for change detection.
5.  **Trigger Analysis:** After saving new legislation and its text, the system should ideally trigger the AI analysis process (likely managed by services using `app/ai_analysis/`) to generate a `LegislationAnalysis` record.
6.  **Sponsors/Amendments:** If the API provides sponsor or amendment data, create corresponding `LegislationSponsor` or `Amendment` records linked to the `Legislation` record.
7.  **Update Logic:** Implement logic to check for updates from the API source. Compare incoming data with existing records (potentially using `change_hash` or comparing key fields) and update the `Legislation` record and related entities (e.g., add new `LegislationText` or `LegislationAnalysis` versions) as needed. Update `last_api_check` timestamp.

## 12. Other Considerations

*   **Auditing:** `created_at` and `updated_at` timestamps (managed by `BaseModel` and database triggers) track record modifications. `created_by` and `updated_by` fields exist but may not be consistently populated by automated processes.
*   **Change Detection:** The `legislation.change_hash` field can be used to store a hash of key bill attributes to quickly detect changes during data synchronization.
*   **Error Handling:** The `BaseStore` and specific stores include error handling for database operations, raising custom exceptions like `ConnectionError`, `ValidationError`, and `DatabaseOperationError`. Sync errors are logged in the `sync_errors` table.
*   **Database Migrations:** While not explicitly shown in the examined code, changes to the database schema (e.g., adding columns, tables, or modifying ENUMs) should be managed using a database migration tool (like Alembic) to ensure safe and consistent updates across different environments.

## 11. Development Guidelines

### Environment Variables

Key environment variables for configuration:

*   **Database:**
    *   `DATABASE_URL`: Complete database connection string (takes precedence if set).
    *   `DB_HOST`: Database host (default: localhost).
    *   `DB_PORT`: Database port (default: 5432).
    *   `DB_USER`: Database username.
    *   `DB_PASSWORD`: Database password.
    *   `DB_NAME`: Database name.
*   **APIs:**
    *   `LEGISCAN_API_KEY`: API key for LegiScan.
    *   *(Add variables for other integrated APIs as needed)*

### Working with Binary Content (`FlexibleContentType`)

*   The `FlexibleContentType` type column (`text_content` in `LegislationText`, `amendment_text` in `Amendment`) stores either TEXT or BYTEA based on the `is_binary`/`is_binary_text` flag.
*   Use the `set_content()` method (inherited from `BaseModel` or defined on the model) when setting content for these fields. It automatically handles:
    *   Detecting if input is `str` or `bytes`.
    *   Setting the `is_binary` flag.
    *   Storing the content appropriately.
    *   Updating `content_type` and `file_size` metadata.
*   Use the `get_content()` method to retrieve the content in its correct type (`str` or `bytes`).

### Relevance Scoring

*   When adding a new data source, consider if relevance scoring is needed.
*   If so, implement logic (potentially in the source's module, like `app/legiscan/relevance.py`) to calculate scores based on the source's data and update the `LegislationPriority` record.

### Database Transactions

*   The `BaseStore` provides a `transaction()` context manager using the underlying SQLAlchemy session's `begin()` method.
*   Data Store methods (`LegislationStore`, etc.) often operate within the scope of a single session obtained via `_get_session()`. Ensure operations that need to be atomic are wrapped appropriately, potentially at a higher service layer that calls the store methods.
*   Be mindful of session scope, especially in long-running background tasks or scheduled jobs.

### Error Handling and Logging

*   Utilize the custom exceptions defined in `app/data/errors.py` (`ConnectionError`, `ValidationError`, `DatabaseOperationError`) where appropriate.
*   Add informative logging (using Python's `logging` module) at different levels (INFO, WARNING, ERROR) to aid debugging. Follow existing patterns.