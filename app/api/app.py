"""
Main FastAPI Application

This module initializes and configures the FastAPI application for the PolicyPulse API.
It sets up middleware, error handlers, and includes all route modules.
"""

import os
import logging
from typing import AsyncGenerator, cast, Callable
from contextlib import asynccontextmanager

# Third-party imports
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware  # noqa: cSpell
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv  # noqa: cSpell

# Local application imports - this ordering prevents circular import issues
from app.data.data_store import DataStore
from app.legiscan.legiscan_api import LegiScanAPI  # noqa: cSpell
from .error_handlers import validation_exception_handler, general_exception_handler
from .middleware import (
    RequestLoggingMiddleware,
    CacheMiddleware,
    RateLimitMiddleware,
    StreamingResponseFixMiddleware,  # Add the new middleware
    rate_limiter,
    cache_manager
)
from .routes import (
    health_router,
    users_router,
    legislation_router,
    analysis_router,
    dashboard_router,
    admin_router,
    sync_router,
    texas_router
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"  # noqa: cSpell
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Application Lifecycle Handler
# -----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifecycle event handler for setup and teardown of application resources.
    """
    # Import dependencies module to access its global variables
    from . import dependencies  # pylint: disable=C0415

    # Startup: Initialize resources
    try:
        dependencies.data_store = DataStore(max_retries=3)
        # Ensure db_session is available before initializing other services
        if not dependencies.data_store.db_session:
            raise ValueError("Database session is not initialized")

        # dependencies.ai_analyzer = AIAnalysis(db_session=dependencies.data_store.db_session)
        # Commented out to make AIAnalysis on-demand
        dependencies.legiscan_api = LegiScanAPI(
            db_session=dependencies.data_store.db_session,
            api_key=os.getenv("LEGISCAN_API_KEY")  # noqa: cSpell
        )
        logger.info("Services initialized on startup.")
    except ValueError as e:
        logger.critical("Failed to initialize services: %s", e, exc_info=True)
        raise
    except (ConnectionError, TimeoutError) as e:
        logger.critical("Database connection error: %s", e, exc_info=True)
        raise
    except (RuntimeError, IOError) as e:  # Removed duplicate OSError
        logger.critical("Unexpected error during initialization: %s", e, exc_info=True)
        raise

    # Yield control back to FastAPI - make sure this is awaitable
    yield

    # Shutdown: Clean up resources
    if dependencies.data_store:
        try:
            dependencies.data_store.close()
            logger.info("DataStore closed on shutdown.")
        except (IOError, RuntimeError) as e:
            logger.error("Error closing DataStore: %s", e, exc_info=True)
        except (OSError, TypeError, AttributeError) as e:  # More specific exceptions
            logger.error("Unexpected error closing DataStore: %s", e, exc_info=True)

    # Set global variables to None
    dependencies.data_store = None
    dependencies.ai_analyzer = None
    dependencies.legiscan_api = None

# -----------------------------------------------------------------------------
# FastAPI Application Setup
# -----------------------------------------------------------------------------

# Create the FastAPI application
app = FastAPI(
    title="PolicyPulse API",
    description="Legislation tracking and analysis for public health and local government",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",  # noqa: cSpell
    openapi_url="/openapi.json",
    lifespan=lifespan,
    # Disable automatic trailing slash redirection to ensure consistent URLs
    openapi_prefix="",
    # Enable trailing slash redirection to match frontend expectations
    redirect_slashes=True
)

# -----------------------------------------------------------------------------
# Exception Handlers
# -----------------------------------------------------------------------------

# Register exception handlers
# Cast the validation_exception_handler to the expected type
app.add_exception_handler(
    RequestValidationError,
    cast(Callable, validation_exception_handler)
)
app.add_exception_handler(Exception, general_exception_handler)

# -----------------------------------------------------------------------------
# Middleware Setup
# -----------------------------------------------------------------------------

# Add middleware
# Order matters: the first middleware added is the outermost
# (processes the request first and the response last)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Total-Count", "X-Page-Size", "X-Current-Page", 
        "X-Total-Pages", "Content-Length"
    ]
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost", "127.0.0.1", "policypulse.app", "*.policypulse.app"
    ]  # noqa: cSpell
)

# Add streaming response fix middleware (should be first to handle all responses)
app.add_middleware(StreamingResponseFixMiddleware)

# Add request logging middleware (should be after streaming fix)
app.add_middleware(RequestLoggingMiddleware)

# Add caching middleware
app.add_middleware(CacheMiddleware, cache_manager_instance=cache_manager)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, rate_limiter_instance=rate_limiter) # Corrected this one too for consistency

# -----------------------------------------------------------------------------
# Router Registration
# -----------------------------------------------------------------------------

# Include all routers
app.include_router(health_router, tags=["Health"])
app.include_router(users_router, tags=["Users"])
app.include_router(legislation_router, tags=["Legislation"])
app.include_router(analysis_router, tags=["Analysis"])
app.include_router(dashboard_router, tags=["Dashboard"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(sync_router, tags=["Sync"])
app.include_router(texas_router, tags=["Texas"])

# -----------------------------------------------------------------------------
# Root Endpoint
# -----------------------------------------------------------------------------

@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {"message": "Legislative Analysis API is running"}


@app.get("/test")
async def test_endpoint():
    """Test endpoint with minimal response to verify JSON handling."""
    return {"status": "ok", "message": "Test endpoint works correctly"}


# Helper functions for bill-related endpoints
def get_bill_analysis(session, bill_id):
    """Get the latest analysis for a bill."""
    # pylint: disable=C0415
    from app.models import LegislationAnalysis

    return (
        session.query(LegislationAnalysis)
        .filter(LegislationAnalysis.legislation_id == bill_id)
        .order_by(LegislationAnalysis.analysis_version.desc())
        .first()
    )


def format_analysis_response(bill, analysis):
    """Format the analysis response based on whether analysis exists."""
    if not analysis:
        return {
            "bill_id": bill.id,
            "bill_number": bill.bill_number,
            "message": "No analysis available for this bill"
        }
    
    return {
        "bill_id": bill.id,
        "bill_number": bill.bill_number,
        "analysis_id": analysis.id,
        "analysis_version": analysis.analysis_version,
        "analysis_date": analysis.analysis_date.isoformat() if analysis.analysis_date else None,
        "impact_category": str(analysis.impact_category.value) if analysis.impact_category else None,
        "impact": str(analysis.impact.value) if analysis.impact else None,
        "summary": analysis.summary,
        "public_health_impacts": analysis.public_health_impacts,
        "local_gov_impacts": analysis.local_gov_impacts,
        "confidence_score": analysis.confidence_score,
        "insufficient_text": analysis.insufficient_text
    }


@app.get("/test-bills")
async def test_bills_endpoint():
    """Test endpoint to list bills with minimal processing."""
    # Import models within function to avoid circular imports
    # pylint: disable=C0415
    from app.models import init_db, Legislation

    try:
        # Create a dedicated session that doesn't go through middleware
        session_factory = init_db()
        session = session_factory()

        # Simple query to get a limited set of bills
        bills_data = []
        try:
            bills = session.query(Legislation).limit(10).all()
            bills_data.extend(
                {
                    "id": bill.id,
                    "bill_number": bill.bill_number,
                    "govt_source": bill.govt_source,
                    "title": bill.title[:100] if bill.title else None,  # Truncate long titles
                }
                for bill in bills
            )
        except (ValueError, KeyError) as e:
            return {"error": f"Invalid data format: {str(e)}"}
        except (IOError, OSError) as e:
            return {"error": f"I/O error: {str(e)}"}
        except (AttributeError, TypeError, RuntimeError) as e:
            return {"error": f"Database error: {str(e)}"}
        finally:
            session.close()

        return {
            "count": len(bills_data),
            "bills": bills_data
        }
    except ImportError as e:
        return {"error": f"Module import error: {str(e)}"}
    except ConnectionError as e:
        return {"error": f"Database connection error: {str(e)}"}
    except RuntimeError as e:
        return {"error": f"Runtime error: {str(e)}"}
    except (OSError, IOError, TypeError) as e:
        return {"error": f"Server error: {str(e)}"}


@app.get("/test-bills/{bill_id}")
async def test_bill_detail_endpoint(bill_id: int):
    """Test endpoint to get a specific bill by ID with minimal processing."""
    # Import models within function to avoid circular imports
    # pylint: disable=C0415
    from app.models import init_db, Legislation

    try:
        # Create a dedicated session that doesn't go through middleware
        session_factory = init_db()
        session = session_factory()

        try:
            # Get the bill
            bill = session.query(Legislation).filter(Legislation.id == bill_id).first()

            if not bill:
                raise HTTPException(status_code=404, detail=f"Bill with ID {bill_id} not found")

            # Create a simplified response with essential information
            result = {
                "id": bill.id,
                "bill_number": bill.bill_number,
                "govt_source": bill.govt_source,
                "title": bill.title,
                "description": bill.description,
                "bill_status": str(bill.bill_status.value) if bill.bill_status else None,
                "bill_introduced_date": (
                    bill.bill_introduced_date.isoformat() if bill.bill_introduced_date else None
                ),
                "bill_last_action_date": (
                    bill.bill_last_action_date.isoformat() if bill.bill_last_action_date else None
                ),
                "url": bill.url
            }

            # Add sponsors if available, but without relying on potentially missing attributes
            sponsors = []
            if hasattr(bill, 'sponsors') and bill.sponsors:
                sponsors = [{
                    "name": getattr(sponsor, "sponsor_name", "Unknown"),
                    "state": getattr(sponsor, "sponsor_state", None),
                    "party": getattr(sponsor, "sponsor_party", None),
                    "type": getattr(sponsor, "sponsor_type", None)
                } for sponsor in bill.sponsors]

            result["sponsors"] = sponsors

            return result
        except HTTPException:
            # Let FastAPI handle HTTPExceptions
            raise
        except (ValueError, KeyError, AttributeError) as e:
            return {"error": f"Data format error: {str(e)}"}
        except (IOError, OSError) as e:
            return {"error": f"I/O error: {str(e)}"}
        except (TypeError, LookupError, RuntimeError) as e:
            return {"error": f"Database error: {str(e)}"}
        finally:
            session.close()
    except ImportError as e:
        return {"error": f"Module import error: {str(e)}"}
    except ConnectionError as e:
        return {"error": f"Database connection error: {str(e)}"}
    except RuntimeError as e:
        return {"error": f"Runtime error: {str(e)}"}
    except (OSError, IOError, TypeError) as e:
        return {"error": f"Server error: {str(e)}"}


@app.get("/test-analysis/{bill_id}")
async def test_bill_analysis_endpoint(bill_id: int):
    """Test endpoint to get a bill's analysis with minimal processing."""
    # Import models within function to avoid circular imports
    # pylint: disable=C0415
    from app.models import init_db, Legislation

    try:
        # Create a dedicated session
        session_factory = init_db()
        session = session_factory()

        try:
            # Fetch bill and verify it exists
            bill = session.query(Legislation).filter(Legislation.id == bill_id).first()
            if not bill:
                raise HTTPException(status_code=404, detail=f"Bill with ID {bill_id} not found")

            # Get the latest analysis for this bill
            analysis = get_bill_analysis(session, bill_id)
            
            # Return appropriate response based on whether analysis exists
            return format_analysis_response(bill, analysis)
        except HTTPException:
            # Let FastAPI handle HTTPExceptions
            raise
        except (ValueError, KeyError, AttributeError) as e:
            return {"error": f"Data format error: {str(e)}"}
        except (IOError, OSError) as e:
            return {"error": f"I/O error: {str(e)}"}
        except (TypeError, LookupError, RuntimeError) as e:
            return {"error": f"Database error: {str(e)}"}
        finally:
            session.close()
    except ImportError as e:
        return {"error": f"Module import error: {str(e)}"}
    except ConnectionError as e:
        return {"error": f"Database connection error: {str(e)}"}
    except RuntimeError as e:
        return {"error": f"Runtime error: {str(e)}"}
    except (OSError, IOError, TypeError) as e:
        return {"error": f"Server error: {str(e)}"}
