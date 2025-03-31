# PolicyPulse Backend Documentation

## Overview

This document provides a comprehensive overview of the PolicyPulse backend system, located primarily within the `/app` directory. It details the architecture and workflow, explaining how the system fetches legislation data from external sources (LegiScan), performs AI-powered analysis (using OpenAI), stores the processed information, and serves it via a RESTful API built with FastAPI. This guide is intended for developers onboarding to the project and AI assistants needing to understand the system's structure and function.

## System Architecture & Tech Stack

The PolicyPulse backend utilizes a modular architecture, separating concerns into distinct layers:

1.  **Data Acquisition Layer (`app/legiscan`)**: Fetches legislative data from the LegiScan API.
2.  **Data Storage Layer (`app/models`, `app/data`, `app/db_connection.py`)**: Defines the database schema (SQLAlchemy models), provides data access abstractions, and manages database connections (PostgreSQL).
3.  **AI Analysis Layer (`app/ai_analysis`)**: Analyzes legislation text and PDFs using OpenAI's language models.
4.  **API Layer (`app/api`)**: Exposes data and analysis results through FastAPI endpoints.
5.  **Scheduler Layer (`app/scheduler`)**: Manages background jobs for data synchronization and analysis using APScheduler.

**Core Technologies:**

*   **Language**: Python 3.x
*   **Web Framework**: FastAPI
*   **Database**: PostgreSQL
*   **ORM**: SQLAlchemy
*   **AI Analysis**: OpenAI API (GPT-4o series)
*   **Task Scheduling**: APScheduler
*   **External Data Source**: LegiScan API

## Core Components & Workflow Details

### 1. Data Acquisition & Storage (`app/legiscan`, `app/scheduler`, `app/models`, `app/db_connection.py`)

This process synchronizes local data with the LegiScan source.

**Trigger & Orchestration:**

*   **Scheduled Trigger**: The `nightly_sync_job` (defined in `app/scheduler/jobs.py`) is run daily (default: 10 PM UTC) by the `PolicyPulseScheduler` (`app/scheduler/__init__.py`).
*   **Manual Trigger**: Can be run via `app/run_scheduler.py --sync`.
*   **Coordinator**: The job calls `LegislationSyncManager.run_nightly_sync` (`app/scheduler/sync_manager.py`), which orchestrates the entire sync process for monitored jurisdictions (`US`, `TX`).

**Fetching & Change Detection:**

1.  **API Client**: The `LegislationSyncManager` uses `LegiScanAPI` (`app/legiscan/legiscan_api.py`).
2.  **Session & Master List**: `LegiScanAPI` fetches active sessions (`get_session_list`) and then the raw master bill list (`get_master_list_raw`) for each session. The raw list contains `bill_id` and `change_hash`.
3.  **Change Identification**: `LegislationSyncManager._identify_changed_bills` compares the fetched `change_hash` against the hash stored in the local `Legislation` database table for each `external_id` (LegiScan's `bill_id`) to identify new or modified bills.

**Processing & Saving Individual Bills:**

1.  **Fetch Details**: For each new/changed `bill_id`, `LegiScanAPI.get_bill` fetches the complete bill data.
2.  **Save to DB**: The data is passed to `save_bill_to_db` (`app/legiscan/db.py`). This function is central to data persistence:
    *   **Validation & Filtering**: Ensures data is valid and belongs to a monitored state.
    *   **Transaction**: Wraps operations in a database transaction.
    *   **Core Bill Data**: Creates/updates the `Legislation` record (`app/models/legislation_models.py`), mapping API fields using helpers like `prepare_legislation_attributes` (`app/legiscan/models.py`).
    *   **Sponsors**: Manages `LegislationSponsor` records (`save_sponsors`).
    *   **Text Versions**: Manages `LegislationText` records (`save_legislation_texts`). This involves:
        *   Fetching content, prioritizing `state_link` URLs.
        *   Handling text vs. binary (PDF) content.
        *   Decoding base64 content if needed (`decode_bill_text`).
        *   Sanitizing text (`app/legiscan/utils.py:sanitize_text`).
        *   Storing content and metadata (type, size, hash).
    *   **Relevance Scoring**: Optionally calculates relevance using `RelevanceScorer` (`app/legiscan/relevance.py`).
    *   **Amendments**: Tracks amendments using `track_amendments` (`app/scheduler/amendments.py`) or stores raw data as fallback.
3.  **Analysis Queue**: The `LegislationSyncManager` collects the internal database IDs (`Legislation.id`) of successfully processed bills, preparing them for the analysis stage.

**Database Connection:**

*   Managed by `DatabaseManager` (`app/db_connection.py`) using `psycopg2` and `SimpleConnectionPool` for efficient connection handling.

```python
# Example: Database Connection Pool (Simplified from app/db_connection.py)
class DatabaseManager:
    """Singleton database manager that handles connection pooling."""

    _instance = None
    _pool = None

    @classmethod
    def get_connection_pool(cls, min_conn=1, max_conn=10):
        if cls._pool is None:
            connection_string = cls.get_connection_string()
            cls._pool = SimpleConnectionPool(min_conn, max_conn, connection_string)
        return cls._pool
```

### 2. AI Analysis (`app/ai_analysis`)

This layer processes legislation content to generate structured insights.

**Trigger & Orchestration:**

*   **Trigger**: The `LegislationSyncManager` calls `analyze_legislation` (`app/ai_analysis/legislation_analyzer.py`) for each bill ID collected during the sync.
*   **Coordinator**: `analyze_legislation` (sync wrapper) calls `analyze_legislation_async`.
*   **Workflow (`analyze_legislation_async`)**:
    1.  Checks internal cache (`AIAnalysis._analysis_cache`).
    2.  Fetches the `Legislation` object via `_get_legislation_object`.
    3.  Extracts content (latest text/PDF) via `_extract_content`.
    4.  Calls `_process_analysis_async` (`app/ai_analysis/async_analysis.py`) for core processing logic.
    5.  Stores results via `_store_analysis_results`.

**Content Processing (`_process_analysis_async`, `analysis_processing.py`):**

*   **Dispatcher**: Determines how to handle content based on type (PDF vs. text) and size.
*   **PDF Handling**: If content is PDF and vision is enabled (`OpenAIClient.vision_enabled`), calls `OpenAIClient.call_structured_analysis_with_pdf_async`.
*   **Text Handling**:
    *   **Preprocessing**: Cleans text, checks token count (`preprocess_text`).
    *   **Insufficient Text**: If token count < 300, returns a standard "insufficient text" analysis (`create_insufficient_text_analysis`).
    *   **Chunking**: If token count > context limit, uses `TextChunker` (`chunking.py`) to split text and calls `analyze_in_chunks_async`.
    *   **Direct Analysis**: If within limits, calls `call_structured_analysis_async`.

**AI Interaction (`openai_client.py`, `utils.py`):**

*   **Prompt Engineering**: `call_structured_analysis_async` uses helpers (`utils.py`) to create system instructions (`create_analysis_instructions`) and user prompts (`create_user_prompt`, `create_chunk_prompt`). It includes the target JSON schema (`get_analysis_json_schema`).
*   **API Call**: `OpenAIClient` handles the actual API request to OpenAI (e.g., GPT-4o), managing JSON mode, retries, and response parsing. `call_structured_analysis_with_pdf_async` specifically handles PDF inputs for vision models.
*   **Chunk Merging**: `analyze_in_chunks_async` calls the analysis function for each chunk concurrently and then uses `merge_analyses` (`utils.py`) to combine the results into a single structured analysis.

```python
# Example: AIAnalysis Initialization (Simplified from app/ai_analysis/core_analysis.py)
class AIAnalysis:
    """The AIAnalysis class orchestrates generating a structured legislative analysis
    from OpenAI's language models and storing it in the database with version control."""

    def __init__(self, db_session: Any, openai_api_key: Optional[str] = None,
                 model_name: str = "gpt-4o-2024-08-06",
                 max_context_tokens: int = 120_000, ...):
        # Initialize components
        self.config = AIAnalysisConfig(...) # Load configuration
        self.db_session = db_session
        self.token_counter = TokenCounter(model_name=self.config.model_name)
        self.text_chunker = TextChunker(token_counter=self.token_counter)
        self.openai_client = OpenAIClient(...) # Handles OpenAI API calls
        self.utils = { ... } # Helper functions for prompts, merging, etc.
```

**Storing Results (`db_operations.py`, `impact_analysis.py`):**

*   The final analysis JSON is saved using `store_legislation_analysis_async`.
*   This creates a new `LegislationAnalysis` record, versions it (`is_current`), and links it to the `Legislation` record.
*   Priority scores are updated asynchronously via `update_legislation_priority`.

### 3. API Serving (`app/api`)

Exposes backend data and functionality via a RESTful API.

**Setup (`app.py`):**

*   Initializes the FastAPI application.
*   Configures middleware: CORS (`CORSMiddleware`), Trusted Hosts (`TrustedHostMiddleware`), Request Logging, Caching (`CacheMiddleware`), Rate Limiting (`RateLimitMiddleware`), Streaming Fix.
*   Sets up global exception handlers (`error_handlers.py`).
*   Initializes shared resources (e.g., `DataStore`, `LegiScanAPI`) via the `lifespan` context manager.
*   Includes routers defined in `app/api/routes/`.

```python
# Example: FastAPI App Setup (Simplified from app/api/app.py)
app = FastAPI(
    title="PolicyPulse API",
    description="Legislation tracking and analysis for public health and local government",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan # Manages startup/shutdown events
)

# Add middleware (order matters)
app.add_middleware(CORSMiddleware, ...)
app.add_middleware(TrustedHostMiddleware, ...)
app.add_middleware(StreamingResponseFixMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CacheMiddleware, ...)
app.add_middleware(RateLimitMiddleware, ...)

# Include all routers
app.include_router(health_router, tags=["Health"])
app.include_router(legislation_router, prefix="/legislation", tags=["Legislation"])
app.include_router(analysis_router, prefix="/analysis", tags=["Analysis"])
# ... other routers ...
```

**Routing & Data Access (`routes/`, `dependencies.py`, `data/`):**

*   Endpoints are defined in modules like `legislation.py`, `analysis.py`, etc.
*   Route functions handle incoming requests.
*   Dependencies (`dependencies.py`) provide access to shared resources like database sessions (`get_db`).
*   Data is retrieved either via direct SQLAlchemy queries on models (`app/models`) or through the Data Access Layer (`app/data` stores like `LegislationStore`).
*   Responses are typically serialized using Pydantic models (`app/api/models.py`).

**Key Routes:**

*   `/health`: Health checks.
*   `/legislation`: Access legislation details, lists, search.
*   `/analysis`: Access AI analysis results for specific bills.
*   `/dashboard`: Aggregated data endpoints.
*   `/sync`: Manual sync triggers (admin).
*   `/admin`: Other administrative functions.
*   `/users`: User management (if applicable).
*   `/texas`: Texas-specific data views.

### 4. Scheduler (`app/scheduler`)

Manages background tasks.

**Setup (`__init__.py`):**

*   `PolicyPulseScheduler` class initializes `BackgroundScheduler` from `APScheduler`.
*   Defines and schedules jobs using `CronTrigger`.

**Jobs (`jobs.py`, `sync_manager.py`, `seeding.py`):**

*   **`nightly_sync_job`**: Runs `LegislationSyncManager.run_nightly_sync` (described in Data Acquisition).
*   **`daily_maintenance_job`**: Performs DB cleanup (e.g., deleting old `SyncError` logs, running `VACUUM ANALYZE`).
*   **`run_on_demand_analysis`**: Triggers analysis for a specific bill ID.
*   **Historical Seeding**: `LegislationSyncManager.seed_historical_data` calls functions in `seeding.py` to backfill data.

```python
# Example: Scheduler Job Definition (Simplified from app/scheduler/__init__.py)
class PolicyPulseScheduler:
    """Manages scheduled jobs for PolicyPulse"""

    def _initialize_and_start_scheduler(self) -> bool:
        # Add the nightly sync job (runs at 10 PM UTC)
        self.scheduler.add_job(
            self._nightly_sync_job,
            CronTrigger(hour=22, minute=0),
            id='nightly_sync',
            name='LegiScan Nightly Sync',
            replace_existing=True
        )

        # Add daily maintenance job (runs at 4 AM UTC)
        self.scheduler.add_job(
            self._daily_maintenance_job,
            CronTrigger(hour=4, minute=0),
            id='daily_maintenance',
            name='Daily Database Maintenance',
            replace_existing=True
        )
        self.scheduler.start() # Start the scheduler background process
```

## Key Data Models (`app/models/`)

*   **`Legislation`**: Core bill information (title, status, dates, source ID, etc.).
*   **`LegislationSponsor`**: Bill sponsors.
*   **`LegislationText`**: Bill text versions (text/binary), content, metadata.
*   **`LegislationAnalysis`**: Structured AI analysis JSON, versioned.
*   **`Amendment`**: (Optional) Amendment details.
*   **`LegislationPriority`**: (Optional) Calculated priority scores.
*   **`ImpactRating`**: (Optional) Specific impact assessments.
*   **`SyncMetadata`**: Tracks background sync job status and results.
*   **`SyncError`**: Logs errors during sync operations.

*(Refer to `app/models/` modules for detailed field definitions)*

## Non-Functional Aspects

*   **Error Handling**: Custom exceptions (`AIAnalysisError`, `DataSyncError`), FastAPI exception handlers, transaction rollbacks, logging of errors (including to `SyncError` table).
*   **Security**: Relies on standard practices like environment variables for secrets, FastAPI middleware (Trusted Hosts), and potentially authentication middleware (not fully detailed here). Rate limiting helps prevent abuse.
*   **Performance**: Database connection pooling, API response caching, asynchronous operations in API and AI analysis, text chunking for large documents.
*   **Configuration**: Primarily via environment variables (`.env` loaded by `dotenv`) and Pydantic models (`AIAnalysisConfig`).

## Getting Started / Development

1.  **Environment Setup**: Set up Python environment, install dependencies from `requirements.txt`.
2.  **Database Setup**: Configure PostgreSQL, set connection string in `.env`, run schema setup/migrations (see `docs/DATABASE_SETUP.md`, `db/`).
3.  **Environment Variables**: Create a `.env` file based on `.env.example` or `.env.template` and populate required variables (Database URL, LegiScan API Key, OpenAI API Key).
4.  **Run API Server**: Use `uvicorn app.api.app:app --reload` or similar (potentially via `start_server.py`).
5.  **Run Scheduler**: Execute `python app/run_scheduler.py` for continuous background tasks, or with flags (`--seed`, `--sync`, `--analyze`) for specific actions.
6.  **Testing**: Run tests (details likely in `docs/testing_plan.md` or via scripts).

## Conclusion

The PolicyPulse backend is a robust system designed for the complex task of acquiring, analyzing, and serving legislative data. Its modular design facilitates maintenance and extension. Understanding the flow between the Scheduler, LegiScan integration, AI Analysis pipeline, and the API layer is key to working with this codebase.
