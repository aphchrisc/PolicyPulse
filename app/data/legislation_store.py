"""
app/data/legislation_store.py

This module provides the LegislationStore class for managing legislation data.
"""

import logging
import re
from datetime import datetime, timedelta # Added timedelta
from typing import Dict, List, Optional, Any, TypedDict, Union, cast

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy import or_, and_, func, desc, asc, distinct # Added asc, distinct

from app.models import (
    Legislation,
    LegislationText,  # Used in relationships
    LegislationAnalysis,  # Used in relationships
    LegislationSponsor,  # Used in relationships
    DataSourceEnum,  # noqa: Used for type conversion in formatted output
    GovtTypeEnum,  # noqa: Used in value conversion
    BillStatusEnum,  # noqa: Used in value conversion
    ImpactCategoryEnum,  # noqa: Used in value conversion
    ImpactLevelEnum  # noqa: Used in value conversion
)
# Import the filter model
from app.api.models import BillSearchFilters

try:
    from app.models import LegislationPriority  # noqa: Used conditionally via HAS_PRIORITY_MODEL
    HAS_PRIORITY_MODEL = True
except ImportError:
    HAS_PRIORITY_MODEL = False

try:
    from app.models import ImpactRating, ImplementationRequirement  # noqa: Used conditionally via HAS_IMPACT_MODELS
    HAS_IMPACT_MODELS = True
except ImportError:
    HAS_IMPACT_MODELS = False

from app.data.base_store import BaseStore, ensure_connection, validate_inputs
from app.data.errors import ValidationError, DatabaseOperationError

logger = logging.getLogger(__name__)


class LegislationSummary(TypedDict):
    """Type definition for legislation summary data."""
    id: int
    external_id: str
    govt_source: str
    bill_number: str
    title: str
    bill_status: Optional[str]
    updated_at: Optional[str]


class PaginatedLegislation(TypedDict):
    """Type definition for paginated legislation results."""
    total_count: int
    items: List[LegislationSummary]
    page_info: Dict[str, Any]


class LegislationStore(BaseStore):
    """
    LegislationStore handles all legislation-related database operations.
    """

    def _is_valid_date_format(self, date_str: str) -> bool:
        """
        Validate that a string is in YYYY-MM-DD format and represents a valid date.

        Args:
            date_str: The date string to validate

        Returns:
            bool: True if date is valid, False otherwise
        """
        # Check format with regex
        if not date_str or not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return False

        # Try to parse as date
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def _validate_legislation_id(self, legislation_id: int) -> None:
        """
        Validate a legislation ID.

        Args:
            legislation_id: The ID to validate

        Raises:
            ValidationError: If legislation_id is not a positive integer
        """
        if not isinstance(legislation_id, int) or legislation_id <= 0:
            raise ValidationError(
                f"Invalid legislation ID: {legislation_id}. Must be a positive integer."
            )

    def _validate_date_range(self, date_range: Dict[str, Any]) -> None:
        """
        Validate date range filter.

        Args:
            date_range: Date range dictionary

        Raises:
            ValidationError: If date range format is invalid
        """
        if not isinstance(date_range, dict):
            raise ValidationError("Date range must be a dictionary")

        start_date = date_range.get('start_date')
        end_date = date_range.get('end_date')

        # Validate start_date format
        if start_date and not self._is_valid_date_format(start_date):
            raise ValidationError(
                f"Invalid start_date format: {start_date}. Expected YYYY-MM-DD"
            )

        # Validate end_date format
        if end_date and not self._is_valid_date_format(end_date):
            raise ValidationError(
                f"Invalid end_date format: {end_date}. Expected YYYY-MM-DD"
            )

        # Validate end_date is after start_date
        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                f"end_date ({end_date}) cannot be before start_date ({start_date})"
            )

    def _validate_keywords_filter(self, keywords: Any) -> None:
        """
        Validate keywords filter.

        Args:
            keywords: Keywords parameter to validate

        Raises:
            ValidationError: If keywords format is invalid
        """
        if not isinstance(keywords, (list, str)):
            raise ValidationError("Keywords filter must be a list or string")

    def _validate_search_params(self, query: str, filters: Dict[str, Any]) -> None:
        """
        Validate search parameters.

        Args:
            query: Search query string
            filters: Dictionary of filter criteria

        Raises:
            ValidationError: If parameters are invalid
        """
        # Validate main parameters
        if not isinstance(query, str):
            raise ValidationError(f"Query must be a string, got {type(query).__name__}")

        if not isinstance(filters, dict):
            raise ValidationError(
                f"Filters must be a dictionary, got {type(filters).__name__}"
            )

        # Validate specific filters
        if 'keywords' in filters:
            self._validate_keywords_filter(filters['keywords'])

        if 'date_range' in filters and filters['date_range']:
            self._validate_date_range(filters['date_range'])

    def _format_legislation_summary(self, legislation) -> LegislationSummary:
        """
        Format a legislation record into a summary dictionary.

        Args:
            legislation: Legislation model instance

        Returns:
            LegislationSummary: Dictionary with legislation summary data
        """
        # Create base summary with required fields
        summary = {
            "id": legislation.id,
            "external_id": legislation.external_id,
            "govt_source": legislation.govt_source,
            "bill_number": legislation.bill_number,
            "title": legislation.title,
            "bill_status": None,
            "updated_at": None
        }

        # Handle bill_status which might be an enum
        if hasattr(legislation, 'bill_status') and legislation.bill_status is not None:
            summary["bill_status"] = (
                legislation.bill_status.value
                if hasattr(legislation.bill_status, 'value')
                else str(legislation.bill_status)
            )

        # Handle updated_at datetime
        if hasattr(legislation, 'updated_at') and legislation.updated_at is not None:
            summary["updated_at"] = legislation.updated_at.isoformat()

        # Cast the dictionary to LegislationSummary type
        return cast(LegislationSummary, summary)

    def _calculate_pagination_info(self, total_count: int, limit: int, offset: int) -> Dict[str, Any]:
        """
        Calculate pagination metadata.

        Args:
            total_count: Total number of records
            limit: Maximum records per page
            offset: Number of records to skip

        Returns:
            Dict[str, Any]: Pagination metadata
        """
        # Use effective page size (handle case where limit <= 0)
        page_size = max(1, limit) if limit > 0 else total_count

        # Calculate current page and total pages
        current_page = (offset // page_size) + 1 if page_size > 0 else 1
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

        # Determine if there are next/previous pages
        has_next = offset + limit < total_count if limit > 0 else False
        has_prev = offset > 0

        return {
            "total": total_count, # Added for consistency with API response
            "limit": limit, # Added for consistency
            "offset": offset, # Added for consistency
            "current_page": current_page,
            "total_pages": total_pages,
            "page_size": page_size,
            "has_more": has_next, # Renamed for consistency
            "has_next_page": has_next,
            "has_prev_page": has_prev,
            "next_offset": offset + limit if has_next else None,
            "prev_offset": max(0, offset - limit) if has_prev else None
        }

    @ensure_connection
    @validate_inputs(lambda self, limit, offset: self._validate_pagination_params(limit, offset))
    def list_legislation(self, limit: int = 50, offset: int = 0) -> PaginatedLegislation:
        """
        List legislation records with pagination. Returns both items and total count.

        Args:
            limit: Maximum items to return.
            offset: Number of items to skip.

        Returns:
            PaginatedLegislation: Dictionary with 'total_count', 'items', and 'page_info'.

        Raises:
            ValidationError: If pagination parameters are invalid
            DatabaseOperationError: On database errors
        """
        try:
            # Ensure we have a valid session
            session = self._get_session()

            # Create base query and get total count
            base_query = session.query(Legislation)
            total_count = base_query.count()

            # Apply sorting and pagination
            query = base_query.order_by(Legislation.updated_at.desc())

            if limit > 0:
                query = query.limit(limit)
            if offset > 0:
                query = query.offset(offset)

            # Execute query and format results
            records = query.all()
            items = [self._format_legislation_summary(leg) for leg in records]

            # Calculate pagination metadata
            page_info = self._calculate_pagination_info(total_count, limit, offset)

            # Return paginated result
            return {
                "total_count": total_count,
                "items": items,
                "page_info": page_info
            }
        except SQLAlchemyError as e:
            error_msg = f"Database error listing legislation: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseOperationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error listing legislation: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseOperationError(error_msg) from e

    def _format_date(self, date_obj) -> Optional[str]:
        """Helper method to format a date object to ISO format string."""
        return date_obj.isoformat() if date_obj is not None else None

    def _build_base_legislation_details(self, leg: Legislation) -> Dict[str, Any]:
        """Helper method to build the base legislation details dictionary."""
        return {
            "id": leg.id,
            "external_id": leg.external_id,
            "govt_type": leg.govt_type.value if leg.govt_type is not None else None,
            "govt_source": leg.govt_source,
            "bill_number": leg.bill_number,
            "title": leg.title,
            "description": leg.description,
            "bill_status": leg.bill_status.value if leg.bill_status is not None else None,
            "bill_introduced_date": self._format_date(leg.bill_introduced_date),
            "bill_last_action_date": self._format_date(leg.bill_last_action_date),
            "bill_status_date": self._format_date(leg.bill_status_date),
            "last_api_check": self._format_date(leg.last_api_check),
            "created_at": self._format_date(leg.created_at),
            "updated_at": self._format_date(leg.updated_at),
            "url": leg.url,
            "state_link": leg.state_link,
        }

    def _format_sponsors(self, sponsors) -> List[Dict[str, Any]]:
        """Helper method to format sponsors data."""
        return [
            {
                "name": sponsor.sponsor_name,
                "party": sponsor.sponsor_party,
                "state": sponsor.sponsor_state,
                "type": sponsor.sponsor_type
            }
            for sponsor in sponsors
        ]

    def _format_latest_text(self, latest_text) -> Dict[str, Any]:
        """Helper method to format the latest text data."""
        # Check if text content is binary
        is_binary = False
        if hasattr(latest_text, 'text_metadata') and latest_text.text_metadata:
            is_binary = latest_text.text_metadata.get('is_binary', False)

        return {
            "id": latest_text.id,
            "text_type": latest_text.text_type,
            "text_date": self._format_date(latest_text.text_date),
            "text_content": None if is_binary else latest_text.text_content,
            "is_binary": is_binary,
            "version_num": latest_text.version_num,
            "text_hash": latest_text.text_hash
        }

    def _format_analysis(self, analysis) -> Dict[str, Any]:
        """Helper method to format analysis data."""
        # Helper to safely get enum value or None
        def get_enum_value(enum_obj):
            return enum_obj.value if enum_obj else None

        return {
            "id": analysis.id,
            "analysis_version": analysis.analysis_version,
            "summary": analysis.summary,
            "key_points": analysis.key_points,
            "created_at": self._format_date(analysis.created_at),
            "analysis_date": self._format_date(analysis.analysis_date),
            "public_health_impacts": analysis.public_health_impacts,
            "local_gov_impacts": analysis.local_gov_impacts,
            "economic_impacts": analysis.economic_impacts,
            "environmental_impacts": analysis.environmental_impacts, # Added
            "education_impacts": analysis.education_impacts, # Added
            "infrastructure_impacts": analysis.infrastructure_impacts, # Added
            "stakeholder_impacts": analysis.stakeholder_impacts, # Added
            "recommended_actions": analysis.recommended_actions, # Added
            "immediate_actions": analysis.immediate_actions, # Added
            "resource_needs": analysis.resource_needs, # Added
            "impact_category": get_enum_value(analysis.impact_category),
            "impact_level": get_enum_value(analysis.impact), # Renamed from 'impact'
            "confidence_score": analysis.confidence_score, # Added
            "model_version": analysis.model_version, # Added
            "insufficient_text": analysis.insufficient_text, # Added
            "status": "complete" if analysis.id else "pending" # Add status based on existence
        }

    def _add_priority_data_if_available(self, details: Dict[str, Any], leg: Legislation) -> None:
        """Helper method to add priority data if available."""
        if HAS_PRIORITY_MODEL and hasattr(leg, 'priority') and leg.priority:
            details["priority"] = {
                "public_health_relevance": leg.priority.public_health_relevance,
                "local_govt_relevance": leg.priority.local_govt_relevance,
                "overall_priority": leg.priority.overall_priority,
                "manually_reviewed": leg.priority.manually_reviewed,
                "reviewer_notes": leg.priority.reviewer_notes,
                "review_date": self._format_date(leg.priority.review_date)
            }
        else: # Ensure priority key exists even if empty
             details["priority"] = None

    def _add_impact_data_if_available(self, details: Dict[str, Any], leg: Legislation) -> None:
        """Helper method to add impact ratings data if available."""
        if HAS_IMPACT_MODELS and hasattr(leg, 'impact_ratings') and leg.impact_ratings:
            details["impact_ratings"] = [
                {
                    "id": rating.id,
                    "category": rating.impact_category.value if rating.impact_category else None,
                    "level": rating.impact_level.value if rating.impact_level else None,
                    "description": rating.impact_description,
                    "confidence": rating.confidence_score,
                    "is_ai_generated": rating.is_ai_generated,
                    "reviewed_by": rating.reviewed_by,
                    "review_date": self._format_date(rating.review_date)
                }
                for rating in leg.impact_ratings
            ]
        else: # Ensure key exists
             details["impact_ratings"] = []


    def _add_implementation_data_if_available(self, details: Dict[str, Any], leg: Legislation) -> None:
        """Helper method to add implementation requirements data if available."""
        if HAS_IMPACT_MODELS and hasattr(leg, 'implementation_requirements') and leg.implementation_requirements:
            details["implementation_requirements"] = [
                {
                    "id": req.id,
                    "requirement_type": req.requirement_type,
                    "description": req.description,
                    "estimated_cost": req.estimated_cost,
                    "funding_provided": req.funding_provided,
                    "implementation_deadline": self._format_date(req.implementation_deadline),
                    "entity_responsible": req.entity_responsible
                }
                for req in leg.implementation_requirements
            ]
        else: # Ensure key exists
             details["implementation_requirements"] = []


    @ensure_connection
    @validate_inputs(lambda self, legislation_id: self._validate_legislation_id(legislation_id))
    def get_legislation_details(self, legislation_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve detailed information for a specific legislation record, including
        related texts, analyses, sponsors, and optionally priority/impact data.

        Args:
            legislation_id: The ID of the legislation.

        Returns:
            Optional[Dict[str, Any]]: Detailed record, or None if not found.

        Raises:
            ValidationError: If legislation_id is invalid
            DatabaseOperationError: On database errors
        """
        try:
            session = self._get_session()
            # logger.info(f"Attempting to fetch legislation with ID: {legislation_id} using session: {session}") # Removed log

            # Build query with necessary joins upfront
            query = session.query(Legislation).filter_by(id=legislation_id)
            query = query.options(
                joinedload(Legislation.texts),
                joinedload(Legislation.sponsors)
            )

            # Conditionally load analysis relationship
            query = query.options(joinedload(Legislation.analyses))

            # Conditionally load priority relationship
            if HAS_PRIORITY_MODEL:
                query = query.options(joinedload(Legislation.priority))

            # Conditionally load impact ratings and implementation requirements
            if HAS_IMPACT_MODELS:
                query = query.options(
                    joinedload(Legislation.impact_ratings),
                    joinedload(Legislation.implementation_requirements)
                )

            leg = query.first()


            # --- Logging Removed ---


            if not leg:
                return None

            # Get latest text and analysis
            latest_text = leg.latest_text
            latest_analysis = leg.latest_analysis

            # Build the response dictionary using helper methods
            details = self._build_base_legislation_details(leg)

            # Add sponsors
            details["sponsors"] = self._format_sponsors(leg.sponsors)

            # Add latest text if available
            if latest_text:
                details["latest_text"] = self._format_latest_text(latest_text)
            else:
                details["latest_text"] = None

            # Add analysis if available
            if latest_analysis:
                details["analysis"] = self._format_analysis(latest_analysis)
            else:
                details["analysis"] = None

            # Add optional model data if available
            self._add_priority_data_if_available(details, leg)
            self._add_impact_data_if_available(details, leg)
            self._add_implementation_data_if_available(details, leg)

            # Add jurisdiction if missing (fallback)
            if 'jurisdiction' not in details or details['jurisdiction'] is None:
                 details['jurisdiction'] = details.get('govt_source', 'Unknown')


            return details

        except SQLAlchemyError as e:
            error_msg = f"Database error loading details for legislation {legislation_id}: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseOperationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error loading details for legislation {legislation_id}: {e}"
            logger.error(error_msg, exc_info=True)
            # Return None instead of raising for unexpected errors during detail fetch
            return None

    @ensure_connection
    def search_legislation_by_keywords(self, keywords: Union[str, List[str]], limit: int = 50, offset: int = 0) -> PaginatedLegislation:
        """
        Search for legislation whose title or description contains the given keywords.

        Args:
            keywords: String of comma-separated keywords or list of keywords
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            PaginatedLegislation: Dictionary with search results and pagination metadata

        Raises:
            ValidationError: If input parameters are invalid
            DatabaseOperationError: On database errors
        """
        # Validate inputs
        self._validate_pagination_params(limit, offset)

        # Parse keywords from string if needed
        if isinstance(keywords, str):
            kws = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        elif isinstance(keywords, list):
            kws = [str(kw).strip() for kw in keywords if str(kw).strip()]
        else:
            raise ValidationError(
                f"Keywords must be a string or list, got {type(keywords).__name__}"
            )

        if not kws:
            page_info = self._calculate_pagination_info(0, limit, offset)
            return {"total_count": 0, "items": [], "page_info": page_info}


        try:
            session = self._get_session()

            # Build a query that searches for any of the keywords in title or description
            query = session.query(Legislation)

            # Add keyword filters
            keyword_filters = []
            for keyword in kws:
                pattern = "%%%s%%" % keyword
                keyword_filters.append(
                    or_(
                        Legislation.title.ilike(pattern),
                        Legislation.description.ilike(pattern)
                    )
                )

            # Apply OR combination of all keyword filters
            query = query.filter(or_(*keyword_filters))

            # Get total count for pagination
            total_count = query.count()

            # Apply sorting and pagination
            query = query.order_by(Legislation.updated_at.desc())

            if limit > 0:
                query = query.limit(limit)
            if offset > 0:
                query = query.offset(offset)

            # Execute query
            records = query.all()

            # Format results
            items = [self._format_legislation_summary(leg) for leg in records]

            # Calculate pagination metadata
            page_info = self._calculate_pagination_info(total_count, limit, offset)

            # Return paginated results
            return {
                "total_count": total_count,
                "items": items,
                "page_info": page_info
            }

        except SQLAlchemyError as e:
            error_msg = f"Error searching legislation by keywords: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseOperationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error searching legislation by keywords: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseOperationError(error_msg) from e

    # --- REVISED METHOD START ---
    @ensure_connection
    def search_legislation_advanced(
        self,
        query: str,
        filters: Optional[BillSearchFilters] = None,
        sort_by: str = "relevance",
        sort_dir: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> PaginatedLegislation:
        """
        Perform an advanced search for legislation using various filters and sorting,
        correctly handling distinct results with joins using a window function.
        Uses a two-step query approach to avoid potential syntax errors with complex window functions.

        Args:
            query: Search query string (searches title and description).
            filters: Pydantic model containing filter criteria.
            sort_by: Field to sort results by.
            sort_dir: Sort direction ('asc' or 'desc').
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            PaginatedLegislation: Dictionary with search results and pagination metadata.

        Raises:
            ValidationError: If input parameters are invalid.
            DatabaseOperationError: On database errors.
        """
        # Validate pagination first
        self._validate_pagination_params(limit, offset)
        # TODO: Add validation for sort_by, sort_dir if needed

        try:
            session = self._get_session()

            # --- Determine Sort Column and Direction ---
            sort_column = None
            sort_func = desc if sort_dir == "desc" else asc
            needs_priority_join_for_sort = False

            if sort_by == "date":
                sort_column = Legislation.bill_last_action_date
            elif sort_by == "updated":
                sort_column = Legislation.updated_at
            elif sort_by == "status":
                 sort_column = Legislation.bill_status
            elif sort_by == "title":
                 sort_column = Legislation.title
            elif sort_by == "priority" and HAS_PRIORITY_MODEL:
                 sort_column = LegislationPriority.overall_priority
                 needs_priority_join_for_sort = True
            else: # Default relevance/updated
                sort_column = Legislation.updated_at

            # Apply nullslast() to the sort column for consistent ordering in the final sort
            ordered_sort_column = sort_func(sort_column.nullslast())
            # Simplified ordering for window function (without NULLS LAST/FIRST)
            window_order_by = sort_func(sort_column)


            # --- Build Base Query for Filtering ---
            # Start with the base Legislation table
            filtered_query = session.query(Legislation)

            # --- Apply Joins needed for Filtering or Sorting ---
            analysis_joined = False
            priority_joined = False

            # Join for analysis if needed by filters
            if filters and (filters.impact_level or filters.impact_category):
                filtered_query = filtered_query.outerjoin(
                    LegislationAnalysis, Legislation.id == LegislationAnalysis.legislation_id
                )
                analysis_joined = True

            # Join for priority if needed by filters or sorting
            if (filters and filters.reviewed_only and HAS_PRIORITY_MODEL) or needs_priority_join_for_sort:
                 filtered_query = filtered_query.outerjoin(
                     LegislationPriority, Legislation.id == LegislationPriority.legislation_id
                 )
                 priority_joined = True

            # --- Apply Filters ---
            filter_conditions = []
            # 1. Text Query Filter
            if query and query.strip():
                pattern = f"%{query.strip()}%"
                filter_conditions.append(or_(Legislation.title.ilike(pattern), Legislation.description.ilike(pattern)))
            # 2. Filters from BillSearchFilters
            if filters:
                if filters.impact_level: filter_conditions.append(LegislationAnalysis.impact.in_(filters.impact_level))
                if filters.impact_category: filter_conditions.append(LegislationAnalysis.impact_category.in_(filters.impact_category))
                if filters.bill_status: filter_conditions.append(Legislation.bill_status.in_(filters.bill_status))
                if filters.govt_type: filter_conditions.append(Legislation.govt_type.in_(filters.govt_type))
                if filters.date_range:
                    date_range_dict = filters.date_range.dict()
                    self._validate_date_range(date_range_dict)
                    start_date = date_range_dict.get('start_date')
                    end_date = date_range_dict.get('end_date')
                    if start_date: filter_conditions.append(Legislation.bill_last_action_date >= start_date)
                    if end_date:
                        try:
                            end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
                            inclusive_end_date = end_date_dt + timedelta(days=1)
                            filter_conditions.append(Legislation.bill_last_action_date < inclusive_end_date.strftime('%Y-%m-%d'))
                        except ValueError: logger.warning(f"Invalid end_date format: {end_date}")
                if filters.reviewed_only and HAS_PRIORITY_MODEL: filter_conditions.append(LegislationPriority.manually_reviewed == True)

            # Apply filters to the query
            if filter_conditions:
                filtered_query = filtered_query.filter(and_(*filter_conditions))

            # --- Query for Total Count ---
            # Count distinct legislation IDs *after* filtering
            # Apply distinct to get a query with unique legislation IDs
            count_query = filtered_query.distinct(Legislation.id)
            total_count = count_query.count()

            # --- Build Window Function Subquery to get Ranked IDs ---
            # Select legislation IDs and calculate row numbers based on the *filtered* set
            # Use the simplified window_order_by here
            window_subquery = filtered_query.with_entities(
                Legislation.id,
                func.row_number().over(
                    order_by=window_order_by # Use simplified order
                ).label('rn')
            ).subquery('ranked_legislation')

            # --- Query for Paginated and Sorted IDs ---
            # Select IDs from the window subquery, apply final ordering and pagination
            ranked_ids_query = session.query(window_subquery.c.id).\
                order_by(window_subquery.c.rn) # Order by the rank generated by the window function

            if limit > 0:
                ranked_ids_query = ranked_ids_query.limit(limit)
            if offset > 0:
                ranked_ids_query = ranked_ids_query.offset(offset)

            # Execute to get the list of IDs in the correct order
            ordered_ids = [row[0] for row in ranked_ids_query.all()]

            # --- Fetch Legislation Objects for the selected IDs ---
            if not ordered_ids:
                records = []
            else:
                # Fetch the actual Legislation objects using the ordered IDs
                records_query = session.query(Legislation).filter(Legislation.id.in_(ordered_ids))
                # Preserve the order from ranked_ids_query
                records_dict = {record.id: record for record in records_query.all()}
                records = [records_dict[id] for id in ordered_ids if id in records_dict]


            # --- Format Results ---
            items = [self._format_legislation_summary(leg) for leg in records]
            page_info = self._calculate_pagination_info(total_count, limit, offset)

            return {
                "total_count": total_count,
                "items": items,
                "page_info": page_info
            }

        except ValidationError as e:
             logger.warning(f"Validation error during advanced search: {e}")
             raise # Re-raise validation errors
        except SQLAlchemyError as e:
            # Log the SQLAlchemy error
            logger.error(f"Database error during advanced search: {e}", exc_info=True)
            raise DatabaseOperationError(f"Database error during advanced search: {e}") from e
        except Exception as e:
            error_msg = f"Unexpected error during advanced search: {e}"
            logger.error(error_msg, exc_info=True)
            raise DatabaseOperationError(error_msg) from e
    # --- REVISED METHOD END ---