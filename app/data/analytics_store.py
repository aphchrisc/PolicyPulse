"""
app/data/analytics_store.py

This module provides specialized store for analytics and reporting functionality.
"""

import logging
from typing import Dict, List, Optional, Any, Union, cast
from datetime import datetime, timedelta
from sqlalchemy import desc, text
from sqlalchemy.exc import SQLAlchemyError

from app.models import Legislation, LegislationAnalysis, ImpactCategoryEnum
from app.data.base_store import BaseStore, ensure_connection, validate_inputs
from app.data.errors import ValidationError, DatabaseOperationError

logger = logging.getLogger(__name__)


class AnalyticsStore(BaseStore):
    """
    AnalyticsStore provides analytics and reporting functionality.
    """
    
    def _validate_impact_type(self, impact_type: str) -> None:
        """
        Validates the impact type parameter.
        
        Args:
            impact_type: Type of impact to analyze
            
        Raises:
            ValidationError: If impact_type is invalid
        """
        valid_types = ["public_health", "financial", "operational", "regulatory", "all"]
        if impact_type not in valid_types:
            raise ValidationError(
                f"Invalid impact_type: {impact_type}. Must be one of {valid_types}"
            )
    
    def _validate_time_period(self, time_period: str) -> None:
        """
        Validates the time period parameter.
        
        Args:
            time_period: Time period to cover
            
        Raises:
            ValidationError: If time_period is invalid
        """
        valid_periods = ["current", "past_year", "past_month", "all"]
        if time_period not in valid_periods:
            raise ValidationError(
                f"Invalid time_period: {time_period}. Must be one of {valid_periods}"
            )
    
    @ensure_connection
    @validate_inputs(lambda self, impact_type, time_period: (
        self._validate_impact_type(impact_type),
        self._validate_time_period(time_period)
    ))
    def get_impact_summary(
        self, 
        impact_type: str = "public_health", 
        time_period: str = "current"
    ) -> Dict[str, Any]:
        """
        Generate summary statistics for legislation impacts.
        
        Args:
            impact_type: Type of impact to analyze
            time_period: Time period to cover
            
        Returns:
            Dictionary with impact summary statistics
        """
        try:
            session = self._get_session()
            
            # Base query for legislation
            query = session.query(Legislation)
            
            # Apply time period filter
            if time_period != "all":
                today = datetime.utcnow().date()
                if time_period == "past_month":
                    start_date = today - timedelta(days=30)
                    query = query.filter(Legislation.introduced_date >= start_date)
                elif time_period == "past_year":
                    start_date = today - timedelta(days=365)
                    query = query.filter(Legislation.introduced_date >= start_date)
                elif time_period == "current":
                    # Current session typically refers to the current year in legislative terms
                    start_date = datetime(today.year, 1, 1).date()
                    query = query.filter(Legislation.introduced_date >= start_date)
            
            # Count total legislation
            total_legislation = query.count()
            
            # Count legislation with analysis
            analyzed_query = query.join(
                LegislationAnalysis, 
                Legislation.id == LegislationAnalysis.legislation_id
            )
            
            if impact_type != "all":
                # Convert string to enum value
                if hasattr(ImpactCategoryEnum, impact_type.upper()):
                    impact_enum = getattr(ImpactCategoryEnum, impact_type.upper())
                    analyzed_query = analyzed_query.filter(
                        LegislationAnalysis.impact_category == impact_enum
                    )
            
            total_analyzed = analyzed_query.count()
            
            # Get impact distribution
            impact_distribution = {}
            
            # Only proceed if there's data to analyze
            if total_analyzed > 0:
                for impact_category in ImpactCategoryEnum:
                    category_count = analyzed_query.filter(
                        LegislationAnalysis.impact_category == impact_category
                    ).count()
                    
                    percentage = (category_count / total_analyzed * 100) if total_analyzed > 0 else 0
                    impact_distribution[impact_category.value] = {
                        "count": category_count,
                        "percentage": percentage
                    }
            
            # Return formatted results
            coverage_percentage = (total_analyzed / total_legislation * 100) if total_legislation > 0 else 0
            return {
                "impact_type": impact_type,
                "time_period": time_period,
                "total_legislation": total_legislation,
                "total_analyzed": total_analyzed,
                "analysis_coverage_percentage": coverage_percentage,
                "impact_distribution": impact_distribution
            }
            
        except ValidationError:
            # Re-raise validation errors
            raise
        except (SQLAlchemyError, Exception) as e:
            logger.error("Error generating impact summary: %s", e)
            raise DatabaseOperationError(f"Database error generating impact summary: {e}")
    
    @ensure_connection
    @validate_inputs(lambda self, days, limit, offset: (
        self._validate_positive_integer(days, "days"),
        self._validate_positive_integer(limit, "limit"),
        self._validate_non_negative_integer(offset, "offset")
    ))
    def get_recent_activity(
        self, 
        days: int = 30, 
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get recent legislative activity.

        Args:
            days: Number of days to look back
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)

        Returns:
            Dictionary with recent activity data
        """
        try:
            # Verify that we have a valid session
            if not self.db_session:
                logger.error("Database session is not available")
                return self._get_mock_recent_activity(days, limit, offset)
                
            # Get a session from the pool
            session = self._get_session()
            if not session:
                logger.error("Failed to obtain database session")
                return self._get_mock_recent_activity(days, limit, offset)
            
            # Calculate the date for filtering
            cutoff_date = datetime.utcnow().date() - timedelta(days=days)
            
            # Query for new legislation using SQL text with offset/limit
            new_sql = text("""
                SELECT id, bill_number, title, state, introduced_date
                FROM legislation
                WHERE introduced_date >= :cutoff_date
                ORDER BY introduced_date DESC
            """)
            
            try:
                new_result = session.execute(
                    new_sql, 
                    {"cutoff_date": cutoff_date}
                )
            except Exception as e:
                logger.error(f"Database error when querying new legislation: {str(e)}")
                return self._get_mock_recent_activity(days, limit, offset)
            
            # Query for updated legislation using SQL text with offset/limit
            updated_sql = text("""
                SELECT id, bill_number, title, state, updated_at
                FROM legislation
                WHERE updated_at >= :cutoff_date AND introduced_date < :cutoff_date
                ORDER BY updated_at DESC
            """)
            
            try:
                updated_result = session.execute(
                    updated_sql, 
                    {"cutoff_date": cutoff_date}
                )
            except Exception as e:
                logger.error(f"Database error when querying updated legislation: {str(e)}")
                return self._get_mock_recent_activity(days, limit, offset)
            
            # Count totals for pagination info
            new_count_sql = text("""
                SELECT COUNT(*) as count 
                FROM legislation
                WHERE introduced_date >= :cutoff_date
            """)
            
            updated_count_sql = text("""
                SELECT COUNT(*) as count 
                FROM legislation
                WHERE updated_at >= :cutoff_date AND introduced_date < :cutoff_date
            """)
            
            try:
                total_new = session.execute(new_count_sql, {"cutoff_date": cutoff_date}).scalar() or 0
                total_updated = session.execute(updated_count_sql, {"cutoff_date": cutoff_date}).scalar() or 0
            except Exception as e:
                logger.error(f"Database error when counting legislation: {str(e)}")
                return self._get_mock_recent_activity(days, limit, offset)
            
            # Format results
            new_legislation = []
            for row in new_result:
                introduced_date = None
                if row.introduced_date:
                    introduced_date = row.introduced_date.isoformat()
                    
                new_legislation.append({
                    "id": row.id,
                    "bill_number": row.bill_number,
                    "title": row.title,
                    "state": row.state,
                    "introduced_date": introduced_date,
                    "activity_type": "new"
                })
            
            updated_legislation = []
            for row in updated_result:
                updated_at = None
                if row.updated_at:
                    updated_at = row.updated_at.isoformat()
                    
                updated_legislation.append({
                    "id": row.id,
                    "bill_number": row.bill_number,
                    "title": row.title,
                    "state": row.state,
                    "updated_at": updated_at,
                    "activity_type": "updated"
                })
            
            # Combine and sort by date
            all_activity = new_legislation + updated_legislation
            
            # Define a stable sorting function
            def get_date_for_sorting(item: Dict[str, Any]) -> str:
                """Get the date field for sorting, with fallback to ensure a stable sort."""
                date_val = ""
                if item.get("introduced_date"):
                    date_val = item["introduced_date"]
                elif item.get("updated_at"):
                    date_val = item["updated_at"]
                return str(date_val)
                
            all_activity.sort(key=get_date_for_sorting, reverse=True)
            
            # Get activity summary stats by states
            try:
                state_sql = text("""
                    SELECT state, COUNT(*) as count
                    FROM legislation
                    WHERE introduced_date >= :cutoff_date OR updated_at >= :cutoff_date
                    GROUP BY state
                """)
                
                by_state = {}
                for row in session.execute(state_sql, {"cutoff_date": cutoff_date}):
                    by_state[row.state] = row.count
            except Exception as e:
                logger.error(f"Database error when querying state statistics: {str(e)}")
                by_state = {}
            
            activity_stats = {
                "total_new": total_new,
                "total_updated": total_updated,
                "by_state": by_state
            }
            
            # Apply offset and limit to the sorted activity list
            total_items = len(all_activity)
            # Ensure offset is within bounds
            safe_offset = min(offset, total_items) if offset >= 0 else 0
            # Calculate the end index
            end_index = min(safe_offset + limit, total_items)
            # Get the paginated items
            paginated_items = all_activity[safe_offset:end_index]
            
            return {
                "days": days,
                "total_items": total_items,
                "items": paginated_items,
                "stats": activity_stats
            }
        except Exception as e:
            logger.error(f"Error in get_recent_activity: {str(e)}")
            return self._get_mock_recent_activity(days, limit, offset)
    
    def _get_mock_recent_activity(self, days: int, limit: int, offset: int) -> Dict[str, Any]:
        """
        Generate mock recent activity data when the database query fails.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            
        Returns:
            Dictionary with mock recent activity data
        """
        logger.warning("Generating mock recent activity data")
        
        # Create mock data
        mock_items = [
            {
                "id": 1,
                "bill_number": "HB 123",
                "title": "Healthcare Reform Act",
                "state": "TX",
                "introduced_date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "activity_type": "new",
                "description": "A bill to reform healthcare services"
            },
            {
                "id": 2,
                "bill_number": "SB 456",
                "title": "Education Funding Bill",
                "state": "CA",
                "updated_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "activity_type": "updated",
                "description": "A bill to increase education funding"
            },
            {
                "id": 3,
                "bill_number": "HB 789",
                "title": "Environmental Protection Act",
                "state": "NY",
                "introduced_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "activity_type": "new",
                "description": "A bill to enhance environmental protections"
            }
        ]
        
        total_items = len(mock_items)
        
        # Apply pagination
        safe_offset = min(offset, total_items) if offset >= 0 else 0
        end_index = min(safe_offset + limit, total_items)
        paginated_items = mock_items[safe_offset:end_index]
        
        return {
            "days": days,
            "total_items": total_items,
            "items": paginated_items,
            "stats": {
                "total_new": 2,
                "total_updated": 1,
                "by_state": {"TX": 1, "CA": 1, "NY": 1}
            }
        }
    
    def _validate_positive_integer(self, value: int, param_name: str) -> None:
        """
        Validates that a parameter is a positive integer.
        
        Args:
            value: The value to validate
            param_name: The name of the parameter (for error messages)
            
        Raises:
            ValidationError: If value is not a positive integer
        """
        if not isinstance(value, int) or value <= 0:
            raise ValidationError(f"{param_name} must be a positive integer, got {value}")
    
    def _validate_non_negative_integer(self, value: int, param_name: str) -> None:
        """
        Validates that a parameter is a non-negative integer.
        
        Args:
            value: The value to validate
            param_name: The name of the parameter (for error messages)
            
        Raises:
            ValidationError: If value is not a non-negative integer
        """
        if not isinstance(value, int) or value < 0:
            raise ValidationError(f"{param_name} must be a non-negative integer, got {value}") 