"""
Texas Routes

This module contains endpoints specific to Texas legislation, including
health department and local government focused legislation.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response, status

from app.data.data_store import DataStore
from app.models.enums import BillStatusEnum, ImpactLevelEnum
from app.api.models import LegislationListResponse
from app.api.dependencies import get_data_store
from app.api.utils import (
    log_api_call,
    validate_enum_parameter,
    validate_date_format,
    build_texas_legislation_filters,
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
router = APIRouter(prefix="/texas")

@router.get("/health-legislation", tags=["Texas"], response_model=LegislationListResponse)
@log_api_call
def list_texas_health_legislation(
    request: Request,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    bill_status: Optional[str] = None,
    impact_level: Optional[str] = None,
    introduced_after: Optional[str] = None,
    keywords: Optional[str] = None,
    relevance_threshold: Optional[int] = None,
    store: DataStore = Depends(get_data_store)
):
    """
    Returns legislation relevant to Texas public health departments,
    with filtering options.

    Args:
        response: FastAPI response object for setting headers
        limit: Maximum number of results to return
        offset: Number of results to skip
        bill_status: Filter by bill status
        impact_level: Filter by impact level
        introduced_after: Filter by bills introduced after date (YYYY-MM-DD)
        keywords: Comma-separated list of keywords
        relevance_threshold: Minimum relevance score (0-100)
        store: DataStore instance

    Returns:
        Filtered legislation list with pagination metadata
    """
    with error_handler("List Texas health legislation", {
                ValueError: status.HTTP_400_BAD_REQUEST,
                Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
            }):
        # Validate pagination parameters
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        # Validate optional parameters
        if bill_status:
            validate_enum_parameter(bill_status, BillStatusEnum, "bill_status")

        if impact_level:
            validate_enum_parameter(impact_level, ImpactLevelEnum, "impact_level")

        if introduced_after:
            validate_date_format(introduced_after, "introduced_after")

        if relevance_threshold is not None and (relevance_threshold < 0 or relevance_threshold > 100):
            raise ValueError("Relevance threshold must be between 0 and 100")

        # Mock data for Texas health legislation
        mock_legislation = [
            {
                "id": 1,
                "external_id": "TX12345",
                "govt_source": "Texas",
                "bill_number": "HB 123",
                "title": "Healthcare Reform Act",
                "description": "A bill to reform healthcare provisions across state agencies and programs.",
                "bill_status": "in_committee",
                "updated_at": "2023-06-15T10:30:00",
                "priority_scores": {
                    "public_health_relevance": 85,
                    "local_govt_relevance": 70,
                    "overall_priority": 80
                },
                "summary": "This bill aims to reform healthcare provisions across state agencies.",
                "key_points": ["Increases funding for rural hospitals", "Expands telehealth services"],
                "impact_category": "public_health",
                "impact_level": "high"
            },
            {
                "id": 2,
                "external_id": "TX67890",
                "govt_source": "Texas",
                "bill_number": "SB 456",
                "title": "Public Health Emergency Response",
                "description": "A bill to improve public health emergency response capabilities.",
                "bill_status": "introduced",
                "updated_at": "2023-06-10T14:45:00",
                "priority_scores": {
                    "public_health_relevance": 90,
                    "local_govt_relevance": 75,
                    "overall_priority": 85
                },
                "summary": "This bill aims to improve public health emergency response capabilities.",
                "key_points": ["Establishes emergency response protocols", "Increases funding for emergency preparedness"],
                "impact_category": "public_health",
                "impact_level": "critical"
            },
            {
                "id": 3,
                "external_id": "TX24680",
                "govt_source": "Texas",
                "bill_number": "HB 789",
                "title": "Mental Health Services Expansion",
                "description": "A bill to expand mental health services across the state.",
                "bill_status": "passed_committee",
                "updated_at": "2023-06-05T09:15:00",
                "priority_scores": {
                    "public_health_relevance": 80,
                    "local_govt_relevance": 65,
                    "overall_priority": 75
                },
                "summary": "This bill aims to expand mental health services across the state.",
                "key_points": ["Increases funding for mental health services", "Expands telehealth for mental health"],
                "impact_category": "public_health",
                "impact_level": "high"
            },
            {
                "id": 4,
                "external_id": "TX13579",
                "govt_source": "Texas",
                "bill_number": "SB 321",
                "title": "Healthcare Access Improvement",
                "description": "A bill to improve healthcare access in rural areas.",
                "bill_status": "introduced",
                "updated_at": "2023-06-01T11:20:00",
                "priority_scores": {
                    "public_health_relevance": 75,
                    "local_govt_relevance": 60,
                    "overall_priority": 70
                },
                "summary": "This bill aims to improve healthcare access in rural areas.",
                "key_points": ["Establishes rural health clinics", "Provides incentives for rural healthcare providers"],
                "impact_category": "public_health",
                "impact_level": "medium"
            }
        ]

        # Apply filters
        filtered_legislation = mock_legislation

        # Apply bill_status filter
        if bill_status:
            filtered_legislation = [leg for leg in filtered_legislation if leg["bill_status"] == bill_status]

        # Apply impact_level filter
        if impact_level:
            filtered_legislation = [leg for leg in filtered_legislation if leg["impact_level"] == impact_level]

        # Apply introduced_after filter
        if introduced_after:
            # In a real implementation, we would parse the date and compare
            # For mock data, we'll just filter based on the ID (higher ID = more recent)
            filtered_legislation = [leg for leg in filtered_legislation if leg["id"] >= 3]

        # Apply keywords filter
        if keywords:
            if kws := [
                k.strip().lower() for k in keywords.split(",") if k.strip()
            ]:
                filtered_legislation = [
                    leg for leg in filtered_legislation 
                    if any(kw in leg["title"].lower() or kw in leg["description"].lower() for kw in kws)
                ]

        # Apply relevance_threshold filter
        if relevance_threshold is not None:
            filtered_legislation = [
                leg for leg in filtered_legislation 
                if leg["priority_scores"]["public_health_relevance"] >= relevance_threshold
            ]

        # Apply pagination
        paginated_legislation = filtered_legislation[offset:offset + limit]
        total_count = len(filtered_legislation)

        # Add pagination headers
        from app.api.utils import add_pagination_headers
        add_pagination_headers(response, request, total_count, limit, offset)

        # Format as LegislationListResponse
        return {
            "count": len(paginated_legislation),
            "items": paginated_legislation,
            "page_info": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(paginated_legislation) < total_count
            }
        }

@router.get("/local-govt-legislation", tags=["Texas"], response_model=LegislationListResponse)
@log_api_call
def list_texas_local_govt_legislation(
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    bill_status: Optional[str] = Query(None, description="Filter by bill status"),
    impact_level: Optional[str] = Query(None, description="Filter by impact level"),
    introduced_after: Optional[str] = Query(None, description="Filter by bills introduced after date (YYYY-MM-DD)"),
    keywords: Optional[str] = Query(None, description="Comma-separated list of keywords"),
    municipality_type: Optional[str] = Query(None, description="Type of municipality (city, county, school, special)"),
    relevance_threshold: Optional[int] = Query(None, ge=0, le=100, description="Minimum relevance score (0-100)"),
    store: DataStore = Depends(get_data_store)
):
    """
    Returns legislation relevant to Texas local governments,
    with filtering options including municipality type.

    Args:
        response: FastAPI response object for setting headers
        limit: Maximum number of results to return
        offset: Number of results to skip
        bill_status: Filter by bill status
        impact_level: Filter by impact level
        introduced_after: Filter by bills introduced after date (YYYY-MM-DD)
        keywords: Comma-separated list of keywords
        municipality_type: Type of municipality (city, county, school, special)
        relevance_threshold: Minimum relevance score (0-100)
        store: DataStore instance

    Returns:
        Filtered legislation list with pagination metadata
    """
    with error_handler("List Texas local government legislation", {
                ValueError: status.HTTP_400_BAD_REQUEST,
                Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
            }):
        # Validate enum parameters
        validate_enum_parameter(bill_status, BillStatusEnum, "bill_status")
        validate_enum_parameter(impact_level, ImpactLevelEnum, "impact_level")

        # Validate date format
        if introduced_after:
            validate_date_format(introduced_after, "introduced_after")

        # Validate municipality type
        valid_municipality_types = ["city", "county", "school", "special"]
        if municipality_type and municipality_type not in valid_municipality_types:
            raise ValueError(
                f"Invalid municipality_type: {municipality_type}. Must be one of: {', '.join(valid_municipality_types)}"
            )

        # Mock data for Texas local government legislation
        mock_legislation = [
            {
                "id": 5,
                "external_id": "TX54321",
                "govt_source": "Texas",
                "bill_number": "HB 987",
                "title": "Municipal Funding Reform",
                "description": "A bill to reform municipal funding mechanisms.",
                "bill_status": "in_committee",
                "updated_at": "2023-06-14T10:30:00",
                "priority_scores": {
                    "public_health_relevance": 60,
                    "local_govt_relevance": 90,
                    "overall_priority": 80
                },
                "summary": "This bill aims to reform municipal funding mechanisms.",
                "key_points": ["Increases local control over funding", "Reduces unfunded mandates"],
                "impact_category": "local_govt",
                "impact_level": "high",
                "municipality_type": "city"
            },
            {
                "id": 6,
                "external_id": "TX09876",
                "govt_source": "Texas",
                "bill_number": "SB 654",
                "title": "County Infrastructure Bill",
                "description": "A bill to improve county infrastructure funding.",
                "bill_status": "introduced",
                "updated_at": "2023-06-09T14:45:00",
                "priority_scores": {
                    "public_health_relevance": 50,
                    "local_govt_relevance": 85,
                    "overall_priority": 75
                },
                "summary": "This bill aims to improve county infrastructure funding.",
                "key_points": ["Establishes infrastructure grants", "Streamlines approval processes"],
                "impact_category": "local_govt",
                "impact_level": "high",
                "municipality_type": "county"
            },
            {
                "id": 7,
                "external_id": "TX13579",
                "govt_source": "Texas",
                "bill_number": "HB 321",
                "title": "School District Funding Act",
                "description": "A bill to reform school district funding formulas.",
                "bill_status": "passed_committee",
                "updated_at": "2023-06-04T09:15:00",
                "priority_scores": {
                    "public_health_relevance": 40,
                    "local_govt_relevance": 80,
                    "overall_priority": 70
                },
                "summary": "This bill aims to reform school district funding formulas.",
                "key_points": ["Updates funding formulas", "Increases equity in school funding"],
                "impact_category": "local_govt",
                "impact_level": "medium",
                "municipality_type": "school"
            },
            {
                "id": 8,
                "external_id": "TX24680",
                "govt_source": "Texas",
                "bill_number": "SB 789",
                "title": "Special District Authority Act",
                "description": "A bill to clarify special district authorities and responsibilities.",
                "bill_status": "introduced",
                "updated_at": "2023-05-30T11:20:00",
                "priority_scores": {
                    "public_health_relevance": 30,
                    "local_govt_relevance": 75,
                    "overall_priority": 65
                },
                "summary": "This bill aims to clarify special district authorities and responsibilities.",
                "key_points": ["Defines special district powers", "Establishes oversight mechanisms"],
                "impact_category": "local_govt",
                "impact_level": "medium",
                "municipality_type": "special"
            }
        ]

        # Apply filters
        filtered_legislation = mock_legislation

        # Apply bill_status filter
        if bill_status:
            filtered_legislation = [leg for leg in filtered_legislation if leg["bill_status"] == bill_status]

        # Apply impact_level filter
        if impact_level:
            filtered_legislation = [leg for leg in filtered_legislation if leg["impact_level"] == impact_level]

        # Apply introduced_after filter
        if introduced_after:
            # In a real implementation, we would parse the date and compare
            # For mock data, we'll just filter based on the ID (higher ID = more recent)
            filtered_legislation = [leg for leg in filtered_legislation if leg["id"] >= 7]

        # Apply keywords filter
        if keywords:
            if kws := [
                k.strip().lower() for k in keywords.split(",") if k.strip()
            ]:
                filtered_legislation = [
                    leg for leg in filtered_legislation 
                    if any(kw in leg["title"].lower() or kw in leg["description"].lower() for kw in kws)
                ]

        # Apply municipality_type filter
        if municipality_type:
            filtered_legislation = [leg for leg in filtered_legislation if leg["municipality_type"] == municipality_type]

        # Apply relevance_threshold filter
        if relevance_threshold is not None:
            filtered_legislation = [
                leg for leg in filtered_legislation 
                if leg["priority_scores"]["local_govt_relevance"] >= relevance_threshold
            ]

        # Apply pagination
        paginated_legislation = filtered_legislation[offset:offset + limit]
        total_count = len(filtered_legislation)

        # Add pagination headers
        from app.api.utils import add_pagination_headers
        add_pagination_headers(response, request, total_count, limit, offset)

        # Format as LegislationListResponse
        return {
            "count": len(paginated_legislation),
            "items": paginated_legislation,
            "page_info": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(paginated_legislation) < total_count
            }
        }

@router.get("/impact-analysis", tags=["Texas"])
@log_api_call
def get_texas_impact_analysis(
    impact_type: str = "public_health",
    store: DataStore = Depends(get_data_store)
):
    """
    Get an analysis of legislation impact on Texas public health or local government.

    Args:
        impact_type: Type of impact to analyze (public_health, local_govt)
        store: DataStore instance

    Returns:
        Impact analysis data
    """
    with error_handler("Get Texas impact analysis", {
            ValueError: status.HTTP_400_BAD_REQUEST,
            Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
        }):
        # Validate impact type
        valid_impact_types = ["public_health", "local_govt"]
        if impact_type not in valid_impact_types:
            raise ValueError(f"Invalid impact_type: {impact_type}. Must be one of: {', '.join(valid_impact_types)}")

        try:
            # Use the existing get_impact_summary method instead
            return store.get_impact_summary(impact_type=impact_type, time_period="current")
        except Exception as e:
            logger.error(f"Error getting Texas impact analysis: {e}", exc_info=True)
            raise

@router.get("/regions", tags=["Texas"])
@log_api_call
def get_texas_regions(
    store: DataStore = Depends(get_data_store)
):
    """
    Get a list of Texas regions for filtering.

    Args:
        store: DataStore instance

    Returns:
        List of Texas regions
    """
    with error_handler("Get Texas regions", {
            Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
        }):
        # Return mock list of Texas regions
        regions = [
            "North Texas",
            "East Texas",
            "South Texas",
            "West Texas",
            "Central Texas",
            "Gulf Coast",
            "Panhandle",
            "Rio Grande Valley"
        ]
        return sorted(regions)

@router.get("/legislation-by-region/{region}", tags=["Texas"], response_model=LegislationListResponse)
@log_api_call
def get_legislation_by_region(
    region: str,
    request: Request,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    store: DataStore = Depends(get_data_store)
):
    """
    Get legislation relevant to a specific Texas region.

    Args:
        region: Texas region name
        response: FastAPI response object for setting headers
        limit: Maximum number of results to return
        offset: Number of results to skip
        store: DataStore instance

    Returns:
        Filtered legislation list with pagination metadata
    """
    with error_handler("Get legislation by region", {
            ValueError: status.HTTP_400_BAD_REQUEST,
            Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
        }):
        # Validate pagination parameters
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("Offset cannot be negative")

        # Mock data for legislation by region
        mock_legislation = [
            {
                "id": 9,
                "external_id": f"TX{region.replace(' ', '')}-123",
                "govt_source": "Texas",
                "bill_number": "HB 123",
                "title": f"{region} Healthcare Initiative",
                "description": f"A bill to improve healthcare in {region}.",
                "bill_status": "in_committee",
                "updated_at": "2023-06-15T10:30:00",
                "region": region,
                "priority_scores": {
                    "public_health_relevance": 85,
                    "local_govt_relevance": 70,
                    "overall_priority": 80
                }
            },
            {
                "id": 10,
                "external_id": f"TX{region.replace(' ', '')}-456",
                "govt_source": "Texas",
                "bill_number": "SB 456",
                "title": f"{region} Infrastructure Development",
                "description": f"A bill to fund infrastructure projects in {region}.",
                "bill_status": "introduced",
                "updated_at": "2023-06-10T14:45:00",
                "region": region,
                "priority_scores": {
                    "public_health_relevance": 60,
                    "local_govt_relevance": 90,
                    "overall_priority": 75
                }
            },
            {
                "id": 11,
                "external_id": f"TX{region.replace(' ', '')}-789",
                "govt_source": "Texas",
                "bill_number": "HB 789",
                "title": f"{region} Education Reform",
                "description": f"A bill to improve education in {region}.",
                "bill_status": "passed_committee",
                "updated_at": "2023-06-05T09:15:00",
                "region": region,
                "priority_scores": {
                    "public_health_relevance": 70,
                    "local_govt_relevance": 80,
                    "overall_priority": 75
                }
            }
        ]
        
        # Apply pagination
        paginated_legislation = mock_legislation[offset:offset + limit]
        total_count = len(mock_legislation)
        
        # Add pagination headers
        from app.api.utils import add_pagination_headers
        add_pagination_headers(response, request, total_count, limit, offset)
        
        # Format as LegislationListResponse
        return {
            "count": len(paginated_legislation),
            "items": paginated_legislation,
            "page_info": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(paginated_legislation) < total_count
            }
        }