"""
Health Check Routes

This module contains endpoints for checking the health and status of the API
and its dependencies.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Protocol, cast, List

from fastapi import APIRouter, Depends, Request, Response, status, HTTPException
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

# Define a protocol for the scheduler
class SchedulerProtocol(Protocol):
    def get_jobs(self) -> List[Any]: ...

from app.data.data_store import DataStore
from app.api.models import HealthResponse, ErrorResponse
from app.api.dependencies import get_data_store, get_legiscan_api
from app.api.utils import log_api_call
from app.api.error_handlers import error_handler
from app.api.utils import StreamingJSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/health")

@router.get("", tags=["Utility"])
@log_api_call
async def health_check_without_slash(request: Request, store: DataStore = Depends(get_data_store)):
    """
    Health check endpoint without trailing slash to ensure consistent access.
    Delegates to the main health_check function.
    """
    return await health_check(request, store)

@router.get("/", tags=["Utility"])
@log_api_call
async def health_check(request: Request, store: DataStore = Depends(get_data_store)):
    """
    Health check endpoint to verify the API and database are functioning properly.

    Args:
        request: FastAPI request object (optional)
        store: DataStore dependency for database access
    
    Returns:
        Health status information including database connectivity
    """
    # Simple response that will have consistent Content-Length
    db_status = "ok"
    api_status = "ok"
    
    try:
        # Check database connection
        if store and store.db_session:
            try:
                # Simple test query
                store.db_session.execute(text("SELECT 1"))
            except Exception as db_error:
                logger.error(f"Database connection error: {db_error}")
                db_status = "error"
                api_status = "degraded"
        else:
            db_status = "error"
            api_status = "degraded"
    except Exception as e:
        logger.error(f"Health check error: {e}")
        api_status = "degraded"
        db_status = "error"
    
    # Return a response with our custom response class that handles Content-Length correctly
    return StreamingJSONResponse(
        content={
            "status": api_status,
            "message": "PolicyPulse API is running",
            "version": "2.0.0",
            "database": db_status
        }
    )

@router.get("/detailed")
async def detailed_health_check(request: Request, db: DataStore = Depends(get_data_store)):
    """
    Detailed health check that verifies all system components.
    
    Args:
        request: FastAPI request object
        db: DataStore dependency for database access
        
    Returns:
        Detailed health status of all components
    """
    health_status = {
        "api": {"status": "healthy", "timestamp": datetime.now().isoformat()},
        "database": {"status": "unknown"},
        "legiscan_api": {"status": "unknown"},
        "openai_api": {"status": "unknown"},
    }
    
    # Check database connection
    try:
        if db.db_session is not None:
            db.db_session.execute(text("SELECT 1"))
            health_status["database"] = {"status": "healthy"}
        else:
            health_status["database"] = {"status": "unhealthy", "error": "Database session is None"}
    except Exception as e:
        health_status["database"] = {"status": "unhealthy", "error": str(e)}
    
    # Check LegiScan API
    try:
        legiscan_api = get_legiscan_api()
        try:
            legiscan_status = legiscan_api.check_status()
            health_status["legiscan_api"] = {"status": "healthy", "details": legiscan_status}
        except Exception as e:
            health_status["legiscan_api"] = {"status": "unhealthy", "error": str(e)}
    except Exception as e:
        health_status["legiscan_api"] = {"status": "unhealthy", "error": f"Failed to get LegiScan API: {str(e)}"}
    
    # Check OpenAI API
    try:
        try:
            from app.ai_analysis.openai_client import check_openai_api
            openai_status = check_openai_api()
            if openai_status.get("status") == "connected":
                health_status["openai_api"] = {"status": "healthy", "details": openai_status}
            else:
                health_status["openai_api"] = {"status": "unhealthy", "details": openai_status, "error": openai_status.get("error", "Unknown error")}
        except ImportError:
            health_status["openai_api"] = {"status": "unhealthy", "error": "OpenAI client module not found or check_openai_api function not available"}
    except Exception as e:
        health_status["openai_api"] = {"status": "unhealthy", "error": str(e)}
    
    return StreamingJSONResponse(content=health_status)

@router.get("/database")
async def database_health_check(db: DataStore = Depends(get_data_store)):
    """
    Check database connectivity.
    
    Args:
        db: DataStore dependency for database access
        
    Returns:
        Database health status
    """
    try:
        # Execute a simple query to check database connectivity
        if db.db_session is not None:
            db.db_session.execute(text("SELECT 1"))
            return StreamingJSONResponse(
                content={"status": "healthy", "timestamp": datetime.now().isoformat()}
            )
        else:
            logger.error("Database health check failed: Database session is None")
            return StreamingJSONResponse(
                content={"status": "unhealthy", "error": "Database session is None", "timestamp": datetime.now().isoformat()},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return StreamingJSONResponse(
            content={"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

@router.get("/legiscan")
async def legiscan_health_check(legiscan_api: Any = Depends(get_legiscan_api)):
    """
    Check LegiScan API connectivity.
    
    Args:
        legiscan_api: LegiScanAPI dependency
        
    Returns:
        LegiScan API health status
    """
    try:
        status_info = legiscan_api.check_status()
        return StreamingJSONResponse(
            content={
                "status": "healthy", 
                "details": status_info,
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"LegiScan API health check failed: {str(e)}")
        return StreamingJSONResponse(
            content={
                "status": "unhealthy", 
                "error": str(e), 
                "timestamp": datetime.now().isoformat()
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

@router.get("/openai")
async def openai_health_check():
    """
    Check OpenAI API connectivity.
    
    Returns:
        OpenAI API health status
    """
    try:
        try:
            from app.ai_analysis.openai_client import check_openai_api  # type: ignore
            status_info = check_openai_api()
            return StreamingJSONResponse(
                content={
                    "status": "healthy",
                    "details": status_info,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except ImportError as ie:
            logger.error(f"OpenAI API health check failed: {str(ie)}")
            return StreamingJSONResponse(
                content={
                    "status": "unhealthy",
                    "error": "OpenAI client module not found or check_openai_api function not available",
                    "timestamp": datetime.now().isoformat()
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    except Exception as e:
        logger.error(f"OpenAI API health check failed: {str(e)}")
        return StreamingJSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

@router.get("/scheduler")
async def scheduler_health_check():
    """
    Check scheduler status.
    
    Returns:
        Scheduler health status
    """
    try:
        try:
            from app.scheduler import scheduler
            
            # Check if get_jobs method exists
            if hasattr(scheduler, 'get_jobs'):
                # Cast scheduler to our protocol for type checking
                typed_scheduler = cast(SchedulerProtocol, scheduler)
                jobs = typed_scheduler.get_jobs()
                job_info = [{"id": job.id, "next_run_time": str(job.next_run_time)} for job in jobs]
                
                return StreamingJSONResponse(
                    content={
                        "status": "healthy",
                        "jobs": job_info,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            else:
                # Alternative approach if get_jobs doesn't exist
                return StreamingJSONResponse(
                    content={
                        "status": "healthy",
                        "message": "Scheduler is running but get_jobs method is not available",
                        "timestamp": datetime.now().isoformat()
                    }
                )
        except ImportError:
            logger.error("Scheduler health check failed: Scheduler module not found")
            return StreamingJSONResponse(
                content={
                    "status": "unhealthy",
                    "error": "Scheduler module not found",
                    "timestamp": datetime.now().isoformat()
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    except Exception as e:
        logger.error(f"Scheduler health check failed: {str(e)}")
        return StreamingJSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )