"""
API Dependencies

This module contains all the FastAPI dependencies used across the API endpoints.
Dependencies are functions that can be injected into route handlers to provide
common functionality like database access.
"""

import logging
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global service instances - initialized in app.py
data_store = None
ai_analyzer = None
legiscan_api = None
bill_store = None

def get_data_store():
    """
    Dependency that yields the global data_store.

    Returns:
        DataStore instance

    Raises:
        HTTPException: If DataStore is not initialized
    """
    if not data_store:
        logger.critical("Attempted to access DataStore before initialization")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please try again later."
        )
    return data_store

def get_ai_analyzer():
    """
    Dependency that yields an AIAnalysis instance.
    Creates a new instance on-demand if the global one is not available.

    Returns:
        AIAnalysis instance

    Raises:
        HTTPException: If DataStore is not initialized or AIAnalysis cannot be created
    """
    global ai_analyzer, data_store

    # If global instance exists, return it
    if ai_analyzer:
        return ai_analyzer

    # Otherwise, create a new instance on-demand
    if not data_store or not data_store.db_session:
        logger.critical("Cannot create AIAnalysis: DataStore not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please try again later."
        )

    try:
        # Create a new instance with the current session
        logger.info("Creating on-demand AIAnalysis instance")
        from app.ai_analysis import AIAnalysis
        return AIAnalysis(db_session=data_store.db_session)
    except Exception as e:
        logger.critical(f"Failed to create AIAnalysis instance: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analysis service unavailable. Please try again later.",
        ) from e

def get_legiscan_api():
    """
    Dependency that yields the global legiscan_api.

    Returns:
        LegiScanAPI instance

    Raises:
        HTTPException: If LegiScanAPI is not initialized
    """
    if not legiscan_api:
        logger.critical("Attempted to access LegiScanAPI before initialization")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Legislative data service unavailable. Please try again later."
        )
    return legiscan_api

def get_bill_store():
    """
    Dependency that provides access to bill-related operations.
    Simply returns the data_store since there is no separate BillStore class.
    
    Returns:
        DataStore instance for bill operations
        
    Raises:
        HTTPException: If DataStore is not initialized
    """
    if not data_store:
        logger.critical("Attempted to access bill store but DataStore is not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Legislation service unavailable. Please try again later."
        )
    return data_store

# Export all dependencies
__all__ = [
    'get_data_store',
    'get_ai_analyzer',
    'get_legiscan_api',
    'get_bill_store',
]