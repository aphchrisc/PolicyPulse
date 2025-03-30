"""
Bill relevance scoring and filtering module.

This module provides utilities for calculating relevance scores for legislation
based on keywords and filtering legislation by relevance scores.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Query
from sqlalchemy import or_, and_

from app.models import Legislation, GovtTypeEnum
from app.legiscan.models import HAS_PRIORITY_MODEL

logger = logging.getLogger(__name__)


class RelevanceScorer:
    """
    Calculates relevance scores for bills based on keyword matching.
    
    Scores indicate relevance to public health and local government topics.
    """
    
    def __init__(self):
        """Initialize with default keyword sets for different topics."""
        # Public health relevance keywords for prioritization
        self.health_keywords = [
            "health", "healthcare", "public health", "medicaid", "medicare", "hospital", 
            "physician", "vaccine", "immunization", "disease", "epidemic", "public health emergency",
            "mental health", "substance abuse", "addiction", "opioid", "healthcare workforce" 
        ]

        # Local government relevance keywords for prioritization
        self.local_govt_keywords = [
            "municipal", "county", "local government", "city council", "zoning", 
            "property tax", "infrastructure", "public works", "community development", 
            "ordinance", "school district", "special district", "county commissioner"
        ]
    
    def calculate_relevance(self, bill_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Calculate relevance scores for a bill.
        
        Args:
            bill_data: Dictionary containing bill information
            
        Returns:
            Dictionary with health_relevance, local_govt_relevance, and overall_relevance scores
        """
        if not bill_data:
            return {"health_relevance": 0, "local_govt_relevance": 0, "overall_relevance": 0}

        combined_text = f"{bill_data.get('title', '')} {bill_data.get('description', '')}"
        
        # Calculate health relevance score
        health_score = sum(
            10 
            for keyword in self.health_keywords 
            if keyword.lower() in combined_text.lower()
        )
        
        # Calculate local government relevance score
        local_govt_score = sum(
            10
            for keyword in self.local_govt_keywords
            if keyword.lower() in combined_text.lower()
        )
        
        # Cap scores at 100
        health_score = min(100, health_score)
        local_govt_score = min(100, local_govt_score)

        # Calculate overall priority as average of the two
        overall_score = (health_score + local_govt_score) // 2

        return {
            "health_relevance": health_score,
            "local_govt_relevance": local_govt_score,
            "overall_relevance": overall_score
        }
    
    def calculate_bill_relevance(self, bill_obj, db_session) -> bool:
        """
        Calculate and save relevance scores for a bill object.
        
        Args:
            bill_obj: Legislation database object
            db_session: SQLAlchemy database session
            
        Returns:
            True if relevance was calculated and saved, False otherwise
        """
        # First check if LegislationPriority is available
        if not self._check_priority_model_available("Cannot calculate bill relevance"):
            return False

        combined_text = f"{bill_obj.title} {bill_obj.description}"

        # Calculate health relevance score
        health_score = 0
        for keyword in self.health_keywords:
            if keyword.lower() in combined_text.lower():
                health_score += 10

        local_govt_score = sum(
            10
            for keyword in self.local_govt_keywords
            if keyword.lower() in combined_text.lower()
        )
        
        # Cap scores at 100
        health_score = min(100, health_score)
        local_govt_score = min(100, local_govt_score)

        # Calculate overall priority as average of the two
        overall_score = (health_score + local_govt_score) // 2

        # Now that we've checked HAS_PRIORITY_MODEL, we can safely import the model
        from app.models import LegislationPriority

        # Set priority scores
        if hasattr(bill_obj, 'priority') and bill_obj.priority:
            bill_obj.priority.public_health_relevance = health_score
            bill_obj.priority.local_govt_relevance = local_govt_score
            bill_obj.priority.overall_priority = overall_score
            bill_obj.priority.auto_categorized = True
        else:
            # Create new priority record
            priority = LegislationPriority(
                legislation_id=bill_obj.id,
                public_health_relevance=health_score,
                local_govt_relevance=local_govt_score,
                overall_priority=overall_score,
                auto_categorized=True,
                auto_categories={"health": health_score > 30, "local_govt": local_govt_score > 30}
            )
            db_session.add(priority)
            
        return True

    def _check_priority_model_available(self, context_message: Optional[str] = None) -> bool:
        """
        Check if the LegislationPriority model is available.
        
        Args:
            context_message: Optional context-specific message for the warning log
            
        Returns:
            bool: True if the model is available, False otherwise
        """
        if not HAS_PRIORITY_MODEL:
            warning_message = context_message or "LegislationPriority model not available"
            logger.warning(f"Cannot proceed: {warning_message}")
            return False
        return True


def apply_relevance_filter(query: Query, relevance_type: str, min_score: int) -> Query:
    """
    Apply relevance filters to a query based on the relevance type.
    
    Args:
        query: SQLAlchemy query object
        relevance_type: Type of relevance to filter by ("health", "local_govt", or "both")
        min_score: Minimum relevance score (0-100)
        
    Returns:
        SQLAlchemy query with filters applied
    """
    if not HAS_PRIORITY_MODEL:
        logger.warning("LegislationPriority model not available, cannot apply relevance filter")
        return query
        
    from app.models import LegislationPriority
    
    if relevance_type == "health":
        return query.filter(
            LegislationPriority.public_health_relevance >= min_score
        ).order_by(LegislationPriority.public_health_relevance.desc())
        
    elif relevance_type == "local_govt":
        return query.filter(
            LegislationPriority.local_govt_relevance >= min_score
        ).order_by(LegislationPriority.local_govt_relevance.desc())
        
    else:
        # Default case for "both" or any other value
        return query.filter(
            or_(
                LegislationPriority.public_health_relevance >= min_score,
                LegislationPriority.local_govt_relevance >= min_score
            )
        ).order_by(LegislationPriority.overall_priority.desc())


def get_relevant_texas_legislation(db_session, relevance_type: str = "health", min_score: int = 50, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves legislation particularly relevant to Texas public health or local government.

    Args:
        db_session: SQLAlchemy session
        relevance_type: Type of relevance to filter by ("health", "local_govt", or "both")
        min_score: Minimum relevance score (0-100)
        limit: Maximum number of results to return

    Returns:
        List of relevant legislation dictionaries
    """
    if not HAS_PRIORITY_MODEL:
        logger.warning("LegislationPriority model not available, cannot get relevant Texas legislation")
        return []

    # Import LegislationPriority since we already checked it's available
    from app.models import LegislationPriority

    # Build the query based on relevance type
    query = db_session.query(Legislation).join(
        LegislationPriority, Legislation.id == LegislationPriority.legislation_id
    )

    # Filter by Texas
    query = query.filter(
        or_(
            and_(
                Legislation.govt_type == GovtTypeEnum.state,
                Legislation.govt_source.ilike("%Texas%")
            ),
            Legislation.govt_type == GovtTypeEnum.federal
        )
    )

    # Apply relevance filter
    query = apply_relevance_filter(query, relevance_type, min_score)

    # Get results
    legislation_list = query.limit(limit).all()

    return [
        {
            "id": leg.id,
            "bill_number": leg.bill_number,
            "title": leg.title,
            "description": _safe_truncate_description(leg.description),
            "status": _safe_get_enum_value(leg.bill_status),
            "introduced_date": _safe_format_date(leg.bill_introduced_date),
            "govt_type": _safe_get_enum_value(leg.govt_type),
            "url": leg.url,
            "health_relevance": _safe_get_priority_value(leg, 'public_health_relevance'),
            "local_govt_relevance": _safe_get_priority_value(leg, 'local_govt_relevance'),
            "overall_priority": _safe_get_priority_value(leg, 'overall_priority'),
        }
        for leg in legislation_list
    ]


def _safe_truncate_description(description) -> str:
    """Safely truncate a description string, handling SQLAlchemy Column objects."""
    if description is None:
        return ""

    try:
        # Convert to string if needed
        desc_str = description if isinstance(description, str) else str(description)

        # Safely check length and truncate if needed
        try:
            # Try to get the length directly
            desc_len = len(desc_str)
            if desc_len > 200:
                return f"{desc_str[:200]}..."
        except (TypeError, AttributeError):
            pass
        return desc_str
    except Exception:
        # Fallback for any other errors
        return ""


def _safe_get_enum_value(enum_obj) -> Optional[str]:
    """Safely get the value from an enum object, handling SQLAlchemy Column objects."""
    if enum_obj is None:
        return None
    
    try:
        # Try to access the value attribute
        return enum_obj.value if hasattr(enum_obj, 'value') else str(enum_obj)
    except Exception:
        return None


def _safe_format_date(date_obj) -> Optional[str]:
    """Safely format a date object to ISO format, handling SQLAlchemy Column objects."""
    if date_obj is None:
        return None
    
    try:
        # Try to call isoformat()
        if hasattr(date_obj, 'isoformat'):
            return date_obj.isoformat()
        return str(date_obj)
    except Exception:
        return None


def _safe_get_priority_value(leg_obj, attr_name: str) -> int:
    """Safely get a priority value from a legislation object, handling SQLAlchemy Column objects."""
    try:
        # Check if priority attribute exists
        if not hasattr(leg_obj, 'priority') or leg_obj.priority is None:
            return 0
            
        # Try to get the attribute from priority
        priority_obj = leg_obj.priority
        if hasattr(priority_obj, attr_name):
            value = getattr(priority_obj, attr_name)
            return int(value) if value is not None else 0
        return 0
    except Exception:
        return 0 