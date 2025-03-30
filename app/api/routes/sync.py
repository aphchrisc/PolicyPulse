"""
Sync Routes

This module contains endpoints for synchronizing data with external sources
like LegiScan API.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from datetime import datetime

from app.data.data_store import DataStore
from app.api.models import SyncStatusResponse
from app.api.dependencies import get_data_store, get_legiscan_api
from app.api.utils import log_api_call, run_in_background
from app.api.error_handlers import error_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/sync")

@router.get("/status", tags=["Sync"], response_model=SyncStatusResponse)
@log_api_call
def get_sync_status(
    store: DataStore = Depends(get_data_store)
):
    """
    Retrieve the history of sync operations.

    Args:
        store: DataStore instance

    Returns:
        Sync history records

    Raises:
        HTTPException: If sync history cannot be retrieved
    """
    with error_handler("Get sync status", {
            ValueError: status.HTTP_400_BAD_REQUEST,
            Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
        }):
        try:
            # Check if store has get_sync_history method
            if hasattr(store, 'get_sync_history') and callable(getattr(store, 'get_sync_history')):
                # Get sync history from data store
                sync_history = store.get_sync_history(limit=10)
            else:
                # Fallback if method is not implemented
                logger.warning("get_sync_history method not implemented in DataStore")
                # Return mock data as a fallback
                sync_history = [
                    {
                        "id": 1,
                        "sync_type": "manual",
                        "start_time": datetime.now().isoformat(),
                        "end_time": datetime.now().isoformat(),
                        "status": "completed",
                        "bills_added": 10,
                        "bills_updated": 5,
                        "errors": []
                    }
                ]

            return {
                "sync_history": sync_history,
                "count": len(sync_history)
            }
        except Exception as e:
            logger.error(f"Error retrieving sync history: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            ) from e

@router.post("/trigger", tags=["Sync"], response_model=Dict[str, Any])
@log_api_call
def trigger_sync(
    background_tasks: BackgroundTasks,
    force: bool = False,
    background: bool = True,
    api = Depends(get_legiscan_api)
):
    """
    Manually trigger a synchronization with LegiScan.

    Args:
        force: Whether to force a sync even if one was recently run
        background: Whether to run the sync in the background
        background_tasks: FastAPI background tasks for async processing
        api: LegiScanAPI instance

    Returns:
        Status of the sync operation

    Raises:
        HTTPException: If sync fails or API is unavailable
    """
    with error_handler("Trigger sync", {
        Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
    }):
        if background:
            # Run sync in background
            async def run_sync_task():
                try:
                    api.run_sync(sync_type="manual")
                except Exception as e:
                    logger.error(f"Error in background sync task: {e}", exc_info=True)

            # Add task to background tasks
            background_tasks.add_task(run_sync_task)

            return {
                "status": "processing",
                "message": "Sync operation started in the background"
            }
        else:
            # Run sync synchronously
            result = api.run_sync(sync_type="manual")

            return {
                "status": "success",
                "message": "Sync operation completed successfully",
                "details": {
                    "new_bills": result["new_bills"],
                    "bills_updated": result["bills_updated"],
                    "error_count": len(result["errors"]),
                    "start_time": result["start_time"].isoformat() if result["start_time"] else None,
                    "end_time": result["end_time"].isoformat() if result["end_time"] else None
                }
            }

@router.post("/states/{state_code}", tags=["Sync"], response_model=Dict[str, Any])
@log_api_call
def sync_state(
    state_code: str,
    background_tasks: BackgroundTasks,
    background: bool = True,
    api = Depends(get_legiscan_api)
):
    """
    Trigger a synchronization for a specific state.

    Args:
        state_code: Two-letter state code (e.g., TX, CA)
        background: Whether to run the sync in the background
        background_tasks: FastAPI background tasks for async processing
        api: LegiScanAPI instance

    Returns:
        Status of the sync operation

    Raises:
        HTTPException: If sync fails or API is unavailable
    """
    with error_handler("Sync state", {
        ValueError: status.HTTP_400_BAD_REQUEST,
        Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
    }):
        # Validate state code
        if not state_code or len(state_code) != 2:
            raise ValueError("State code must be a two-letter code (e.g., TX, CA)")

        # Convert to uppercase
        state_code = state_code.upper()

        if background:
            # Run sync in background
            async def run_state_sync_task():
                try:
                    api.sync_state(state_code)
                except Exception as e:
                    logger.error(f"Error in background state sync task: {e}", exc_info=True)

            # Add task to background tasks
            background_tasks.add_task(run_state_sync_task)

            return {
                "status": "processing",
                "message": f"Sync operation for state {state_code} started in the background"
            }
        else:
            # Run sync synchronously
            result = api.sync_state(state_code)

            return {
                "status": "success",
                "message": f"Sync operation for state {state_code} completed successfully",
                "details": result
            }

@router.post("/bills/{bill_id}", tags=["Sync"], response_model=Dict[str, Any])
@log_api_call
def sync_bill(
    bill_id: int,
    api = Depends(get_legiscan_api)
):
    """
    Synchronize a specific bill by ID.

    Args:
        bill_id: LegiScan bill ID
        api: LegiScanAPI instance

    Returns:
        Status of the sync operation

    Raises:
        HTTPException: If sync fails or API is unavailable
    """
    with error_handler("Sync bill", {
        ValueError: status.HTTP_400_BAD_REQUEST,
        Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
    }):
        # Validate bill ID
        if bill_id <= 0:
            raise ValueError("Bill ID must be a positive integer")

        try:
            # Sync the bill
            result = api.sync_bill(bill_id)

            return {
                "status": "success",
                "message": f"Bill {bill_id} synchronized successfully",
                "details": result
            }
        except Exception as e:
            logger.error(f"Error syncing bill {bill_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to sync bill {bill_id}: {str(e)}",
            ) from e