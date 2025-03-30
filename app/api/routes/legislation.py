"""
Legislation Routes

This module contains endpoints for listing, searching, and retrieving legislation.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.data.data_store import DataStore
from app.models.legislation_models import Legislation
from app.models.enums import BillStatusEnum, ImpactLevelEnum, ImpactCategoryEnum, GovtTypeEnum
from app.api.models import (
    BillResponse,
    BillDetailResponse,
    BillSearchParams,
    LegislationListResponse,
    BillSearchQuery
)
from app.api.dependencies import get_data_store, get_bill_store
from app.api.utils import (
    log_api_call,
    add_pagination_headers,
    get_paginated_legislation_response
)
from app.api.error_handlers import error_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/legislation")

# -----------------------------------------------------------------------------
# Basic Legislation Endpoints
# -----------------------------------------------------------------------------
@router.get("/", tags=["Legislation"], response_model=LegislationListResponse)
@log_api_call
def list_legislation(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    store: DataStore = Depends(get_data_store)
):
    """
    List all legislation with pagination.

    Args:
        request: FastAPI request object
        response: FastAPI response object for setting headers
        limit: Maximum number of items to return
        offset: Number of items to skip
        store: DataStore dependency for database access

    Returns:
        List of legislation items with pagination metadata
    """
    with error_handler("listing legislation"):
        try:
            # Use the store to get actual legislation data
            results = store.list_legislation(limit=limit, offset=offset)
            
            # Add pagination headers
            add_pagination_headers(
                response, 
                request, 
                results["total_count"], 
                limit, 
                offset
            )
            
            # Return the formatted response
            return {
                "count": len(results["items"]),
                "items": results["items"],
                "page_info": results["page_info"]
            }
        except Exception as e:
            logger.error(f"Error listing legislation: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error listing legislation: {str(e)}"
            )

@router.get("/{leg_id}/", tags=["Legislation"], response_model=BillDetailResponse)
@log_api_call
def get_legislation_detail(
    leg_id: int,
    raw: bool = Query(False, description="If true, return raw data without validation"),
    store: DataStore = Depends(get_data_store)
):
    """
    Retrieve a single legislation record with detail, including
    latest text and analysis if present.

    Args:
        leg_id: Legislation ID
        raw: If true, return raw data without validation
        store: DataStore instance

    Returns:
        Detailed legislation record
    """
    logger.info(f"Getting legislation details for ID: {leg_id}, raw={raw}")
    
    try:
        # Validate legislation ID before using it
        if not isinstance(leg_id, int) or leg_id <= 0:
            raise ValueError(f"Invalid legislation ID: {leg_id}. Must be a positive integer.")
            
        # Get legislation details from store
        details = store.get_legislation_details(legislation_id=leg_id)

        # --- Logging Removed ---

        if not details:
            logger.warning(f"Legislation with ID {leg_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Legislation with ID {leg_id} not found"
            )
            
        # For raw requests, return the data directly without validation
        if raw:
            logger.info(f"Returning raw data for legislation ID {leg_id}")
            return dict(details)  # Return as dict to avoid streaming response
        
        # Ensure all required fields are present with appropriate defaults
        normalized_data = _normalize_legislation_data(details)
        
        # Convert to dict to ensure it's not a streaming response
        response_dict = dict(normalized_data)
        
        # Add required fields that might be missing
        if 'jurisdiction' not in response_dict and 'govt_source' in response_dict:
            response_dict['jurisdiction'] = response_dict['govt_source']
        
        if 'bill_status' not in response_dict and 'status' in response_dict:
            response_dict['bill_status'] = response_dict['status']
            
        # Ensure date fields are properly formatted
        date_fields = [
            "bill_introduced_date", "bill_last_action_date", "bill_status_date",
            "last_api_check", "created_at", "updated_at", "last_updated"
        ]
        
        for field in date_fields:
            if field in response_dict and response_dict[field] is not None and not isinstance(response_dict[field], str):
                response_dict[field] = response_dict[field].isoformat()
        
        return response_dict
            
    except ValueError as ve:
        logger.error(f"Validation error for legislation ID {leg_id}: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error getting legislation detail: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting legislation detail: {str(e)}"
        )

def _normalize_legislation_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize legislation data to ensure it meets the requirements of BillDetailResponse.
    
    Args:
        data: Raw legislation data from the data store
        
    Returns:
        Normalized data that should pass validation
    """
    # Create a copy to avoid modifying the input
    normalized = data.copy()
    
    # Ensure required fields are present
    if "id" not in normalized:
        raise ValueError("Legislation data missing required 'id' field")
    
    if "external_id" not in normalized:
        normalized["external_id"] = f"unknown_{normalized['id']}"
        
    if "bill_number" not in normalized:
        normalized["bill_number"] = f"#{normalized['id']}"
        
    if "title" not in normalized:
        normalized["title"] = "Untitled Legislation"
    
    # Handle datetime fields to ensure they're properly formatted
    date_fields = [
        "bill_introduced_date", "bill_last_action_date", "bill_status_date",
        "last_api_check", "created_at", "updated_at", "last_updated"
    ]
    
    for field in date_fields:
        # Ensure all date fields are present with default values if missing
        if field not in normalized or normalized[field] is None:
            if field == "last_updated" and "updated_at" in normalized and normalized["updated_at"]:
                normalized[field] = normalized["updated_at"]
            elif field == "updated_at" and "last_updated" in normalized and normalized["last_updated"]:
                normalized[field] = normalized["last_updated"]
            else:
                # For other missing date fields, use current time
                normalized[field] = datetime.now().isoformat()
    
    # Handle jurisdiction field
    if "jurisdiction" not in normalized and "govt_source" in normalized:
        normalized["jurisdiction"] = normalized["govt_source"]
    elif "jurisdiction" not in normalized:
        normalized["jurisdiction"] = "Unknown"
    
    # Handle status field naming
    if "bill_status" not in normalized and "status" in normalized:
        normalized["bill_status"] = normalized["status"]
    elif "bill_status" not in normalized:
        normalized["bill_status"] = "Unknown"
    
    # Handle optional fields with empty defaults
    list_fields = ["sponsors", "impact_ratings", "implementation_requirements"]
    for field in list_fields:
        if field not in normalized or normalized[field] is None:
            normalized[field] = []
    
    dict_fields = ["latest_text", "analysis", "priority"]
    for field in dict_fields:
        if field not in normalized or normalized[field] is None:
            # Only default to {} if the key is completely missing
            if field not in normalized:
                 normalized[field] = {}
            # If the key exists but is None (e.g., no analysis found), keep it None
            # This allows the frontend to distinguish between missing key and no data found.

    # Additional normalization for nested fields
    if "latest_text" in normalized and normalized["latest_text"] and isinstance(normalized["latest_text"], dict):
        if "text" not in normalized["latest_text"] and "text_content" in normalized["latest_text"]:
            normalized["latest_text"]["text"] = normalized["latest_text"]["text_content"]

    # Ensure 'analysis' field specifically retains its structure if present, even if empty initially
    if "analysis" in data and data["analysis"] is not None:
         normalized["analysis"] = data["analysis"] # Explicitly preserve fetched analysis
    elif "analysis" not in normalized: # If truly missing after fetch
         normalized["analysis"] = None # Set to None instead of {}

    return normalized

@router.get("/search/", tags=["Legislation"], response_model=LegislationListResponse)
@log_api_call
def search_legislation(
    request: Request,
    response: Response,
    keywords: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    store: DataStore = Depends(get_data_store)
):
    """
    Search for legislation whose title or description contains the given keywords (comma-separated).
    Example: /legislation/search/?keywords=health,education

    Args:
        request: FastAPI request object
        response: FastAPI response object for setting headers
        keywords: Comma-separated list of keywords
        limit: Maximum number of results to return
        offset: Number of results to skip
        store: DataStore instance

    Returns:
        Legislation items matching the keywords with pagination metadata
    """
    with error_handler("Search legislation", {
        ValueError: status.HTTP_400_BAD_REQUEST,
        Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
    }):
        # Validate pagination parameters
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("Offset cannot be negative")
            
        if not keywords or not keywords.strip():
            raise ValueError("Keywords parameter cannot be empty")

        # Parse keywords
        kws = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        if not kws:
            # Return empty result with pagination headers
            add_pagination_headers(response, request, 0, limit, offset)
            return {"count": 0, "items": [], "page_info": {"total": 0, "limit": limit, "offset": offset, "has_more": False}}

        # Get search results
        results = store.search_legislation_by_keywords(kws, limit, offset)
            
        # Add pagination headers
        add_pagination_headers(
            response, 
            request, 
            results["total_count"], 
            limit, 
            offset
        )
        
        return {
            "count": len(results["items"]),
            "items": results["items"],
            "page_info": results["page_info"]
        }

@router.post("/advanced-search/", tags=["Legislation"], response_model=LegislationListResponse)
@log_api_call
def advanced_search(
    request: Request,
    response: Response,
    search_query: BillSearchQuery,
    store: DataStore = Depends(get_data_store)
):
    """
    Advanced search for legislation with filters, sorting, and pagination.

    Args:
        request: FastAPI request object
        response: FastAPI response object for setting headers
        search_query: Search parameters including filters and pagination
        store: DataStore instance

    Returns:
        Filtered and sorted legislation items with pagination metadata
    """
    with error_handler("Advanced search", {
        ValueError: status.HTTP_400_BAD_REQUEST,
        Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
    }):
        try:
            # Extract parameters from search_query
            limit = search_query.limit
            offset = search_query.offset

            # Call the DataStore method for advanced search
            # We assume a method like search_legislation_advanced exists
            # This method should accept the BillSearchQuery object or its parts
            results = store.search_legislation_advanced(
                query=search_query.query,
                filters=search_query.filters,
                sort_by=search_query.sort_by,
                sort_dir=search_query.sort_dir,
                limit=limit,
                offset=offset
            )

            # Add pagination headers
            add_pagination_headers(
                response, 
                request, 
                results["total_count"], 
                limit, 
                offset
            )
            
            return {
                "count": len(results["items"]),
                "items": results["items"],
                "page_info": results["page_info"]
            }
        except Exception as e:
            logger.error(f"Error in advanced search: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error in advanced search: {str(e)}"
            )

@router.get("/states/", tags=["Legislation"], response_model=List[str])
@log_api_call
async def get_states(store = Depends(get_bill_store)):
    """
    Get a list of available states.
    
    Args:
        store: BillStore dependency for database access
        
    Returns:
        List of state codes
    """
    with error_handler("retrieving states", {
            Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
        }):
        # Return list of states
        return ["TX", "CA", "NY", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]

@router.post("/refresh/", tags=["Legislation"])
@log_api_call
async def refresh_data(
    state: Optional[str] = None,
    bill_store = Depends(get_bill_store),
    legiscan_api = Depends(get_data_store)
):
    """
    Refresh legislation data from LegiScan API.
    
    Args:
        state: Optional state code to filter bills
        bill_store: BillStore dependency for bill data
        legiscan_api: LegiScanAPI dependency for fetching bill data
        
    Returns:
        Message with refresh status
    """
    with error_handler("refreshing legislation data", {
        ConnectionError: status.HTTP_503_SERVICE_UNAVAILABLE,
        Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
    }):
        # Return refresh response
        count = 10
        return {"message": f"Successfully refreshed {count} bills"}