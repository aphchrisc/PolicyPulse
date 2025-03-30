"""
app/data/texas_store.py

This module provides specialized store for Texas-specific legislation queries.
"""

import logging
import re
from typing import Dict, List, Optional, Any, cast
from datetime import datetime
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError

from app.data.base_store import BaseStore, ensure_connection, validate_inputs
from app.data.errors import ValidationError, DatabaseOperationError
from app.models import (
    Legislation,
    LegislationText,
    LegislationAnalysis,
    BillStatusEnum,
    ImpactCategoryEnum
)

logger = logging.getLogger(__name__)


class TexasLegislationStore(BaseStore):
    """
    TexasLegislationStore provides Texas-specific legislation queries and analytics.
    """
    
    def _validate_texas_legislation_filters(self, filters: Optional[Dict[str, Any]]) -> None:
        """
        Validate filters for Texas health legislation queries.
        
        Args:
            filters: Dictionary of filters to validate
            
        Raises:
            ValidationError: If filters contain invalid values
        """
        if not filters:
            return
            
        if not isinstance(filters, dict):
            raise ValidationError(f"Filters must be a dictionary, got {type(filters).__name__}")
            
        # Validate specific filter types
        if 'keywords' in filters and filters['keywords'] and not isinstance(filters['keywords'], str):
            raise ValidationError("Keywords filter must be a string")
            
        if 'status' in filters and filters['status']:
            try:
                BillStatusEnum(filters['status'])
            except ValueError:
                valid_statuses = [status.value for status in BillStatusEnum]
                raise ValidationError(f"Invalid status: {filters['status']}. Must be one of {valid_statuses}")
                
        if 'date_from' in filters and filters['date_from']:
            if not self._is_valid_date_format(filters['date_from']):
                raise ValidationError(f"Invalid date_from format: {filters['date_from']}. Use YYYY-MM-DD.")
                
        if 'date_to' in filters and filters['date_to']:
            if not self._is_valid_date_format(filters['date_to']):
                raise ValidationError(f"Invalid date_to format: {filters['date_to']}. Use YYYY-MM-DD.")
                
        if 'bill_number' in filters and filters['bill_number'] and not isinstance(filters['bill_number'], str):
            raise ValidationError("Bill number must be a string")
    
    def _is_valid_date_format(self, date_str: str) -> bool:
        """
        Validate that a string is in YYYY-MM-DD format and represents a valid date.
        
        Args:
            date_str: The date string to validate
            
        Returns:
            bool: True if date is valid, False otherwise
        """
        # Check format with regex
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return False
            
        # Try to parse as date
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    @ensure_connection
    @validate_inputs(lambda self, limit, offset, filters: (
        self._validate_pagination_params(limit, offset),
        self._validate_texas_legislation_filters(filters)
    ))
    def get_texas_health_legislation(
        self,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve legislation relevant to Texas public health departments or local governments.
        
        Args:
            limit: Maximum records to return
            offset: Pagination offset
            filters: Optional filtering criteria
            
        Returns:
            List of legislation records
        """
        try:
            # Get session
            session = self._get_session()
            
            # Start with base query
            query = (
                session.query(Legislation)
                .outerjoin(LegislationText, Legislation.id == LegislationText.legislation_id)
                .outerjoin(LegislationAnalysis, Legislation.id == LegislationAnalysis.legislation_id)
                .filter(Legislation.state == 'TX')
                .filter(Legislation.categories.contains(['public health']))
                .options(
                    joinedload(Legislation.text),
                    joinedload(Legislation.analysis)
                )
            )
            
            # Apply filters if provided
            if filters:
                if 'keywords' in filters and filters['keywords']:
                    keyword = f"%{filters['keywords']}%"
                    query = query.filter(
                        or_(
                            Legislation.title.ilike(keyword),
                            LegislationText.text_content.ilike(keyword)
                        )
                    )
                    
                if 'status' in filters and filters['status']:
                    query = query.filter(Legislation.status == filters['status'])
                    
                if 'date_from' in filters and filters['date_from']:
                    date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                    query = query.filter(Legislation.introduced_date >= date_from)
                    
                if 'date_to' in filters and filters['date_to']:
                    date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                    query = query.filter(Legislation.introduced_date <= date_to)
                    
                if 'bill_number' in filters and filters['bill_number']:
                    query = query.filter(Legislation.bill_number == filters['bill_number'])
            
            # Add order by
            query = query.order_by(desc(Legislation.introduced_date))
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            
            # Execute query and format results
            results = []
            for legislation in query.all():
                legislation_dict = {
                    'id': legislation.id,
                    'bill_number': legislation.bill_number,
                    'title': legislation.title,
                    'description': legislation.description,
                    'state': legislation.state,
                    'status': legislation.status,
                    'introduced_date': self._format_date(legislation.introduced_date),
                    'last_action_date': self._format_date(legislation.last_action_date),
                    'categories': legislation.categories,
                    'text': {
                        'id': legislation.text.id if legislation.text else None,
                        'content': legislation.text.text_content if legislation.text else None,
                        'url': legislation.text.source_url if legislation.text else None,
                        'updated_at': self._format_date(legislation.text.updated_at) if legislation.text else None
                    } if legislation.text else None,
                    'analysis': {
                        'id': legislation.analysis.id if legislation.analysis else None,
                        'summary': legislation.analysis.summary if legislation.analysis else None,
                        'impact': legislation.analysis.impact if legislation.analysis else None,
                        'updated_at': self._format_date(legislation.analysis.updated_at) if legislation.analysis else None
                    } if legislation.analysis else None
                }
                results.append(legislation_dict)
                
            return results
            
        except ValidationError:
            # Re-raise validation errors
            raise
        except (SQLAlchemyError, Exception) as e:
            logger.error("Error retrieving Texas health legislation: %s", e)
            # For production, wrap in our custom error
            raise DatabaseOperationError(f"Database error retrieving Texas legislation: {e}")
    
    def _format_date(self, date_obj) -> Optional[str]:
        """Format a date object to ISO string or return None."""
        if date_obj is None:
            return None
        return date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj) 