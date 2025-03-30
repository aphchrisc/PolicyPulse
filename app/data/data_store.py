"""
app/data/data_store.py

This module provides the main DataStore class that combines all specialized stores
to maintain backward compatibility with the original monolithic implementation.
"""

import logging
from typing import Dict, List, Optional, Any, Union, TypedDict, cast

from app.data.base_store import BaseStore
from app.data.user_store import UserStore
from app.data.search_store import SearchStore
from app.data.legislation_store import LegislationStore
from app.data.texas_store import TexasLegislationStore
from app.data.analytics_store import AnalyticsStore
from app.models import User, UserPreference
from app.api.models import BillSearchFilters # Import the model

logger = logging.getLogger(__name__)


# Import the type definition from legislation_store
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


class DataStore(BaseStore):
    """
    DataStore centralizes database operations for the legislative tracking system,
    including user management, search history, legislation queries, and analytics.
    It uses specialized store classes internally to handle different concerns.
    
    This class maintains backward compatibility with code that uses the original
    monolithic DataStore implementation.
    """

    def __init__(self, max_retries: int = 3) -> None:
        """
        Initialize the DataStore with specialized store components.

        Args:
            max_retries: Number of attempts to establish a connection.

        Raises:
            ValidationError: If max_retries is not a positive integer
            ConnectionError: If unable to establish a database connection after max_retries
        """
        super().__init__(max_retries)
        
        # Create store components
        self.user_store = UserStore(max_retries)
        self.search_store = SearchStore(max_retries)
        self.legislation_store = LegislationStore(max_retries)
        self.texas_store = TexasLegislationStore(max_retries)
        self.analytics_store = AnalyticsStore(max_retries)
        
        # Cache for frequently accessed data
        self._cache = {}

    # -----------------------------------------------------------------------------
    # USER & PREFERENCE METHODS - Delegate to UserStore
    # -----------------------------------------------------------------------------
    def get_or_create_user(self, email: str) -> User:
        """
        Retrieve a user by email or create one if it does not exist.

        Args:
            email: User's email address.

        Returns:
            User: The existing or newly created user.
        """
        return self.user_store.get_or_create_user(email)

    def save_user_preferences(self, email: str, new_prefs: Dict[str, Any]) -> bool:
        """
        Create or update user preferences.

        Args:
            email: User's email.
            new_prefs: Preference settings.

        Returns:
            bool: True if successful, False otherwise.
        """
        return self.user_store.save_user_preferences(email, new_prefs)

    def get_user_preferences(self, email: str) -> Dict[str, Any]:
        """
        Retrieve preferences for a user.

        Args:
            email: User's email.

        Returns:
            Dict[str, Any]: User preferences or default values.
        """
        return self.user_store.get_user_preferences(email)

    # -----------------------------------------------------------------------------
    # SEARCH HISTORY METHODS - Delegate to SearchStore
    # -----------------------------------------------------------------------------
    def add_search_history(self, email: str, query_string: str, results_data: dict) -> bool:
        """
        Log a user's search query and its results.

        Args:
            email: User's email.
            query_string: The search query.
            results_data: Metadata about the search results.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
        return self.search_store.add_search_history(email, query_string, results_data)

    def get_search_history(self, email: str) -> List[Dict[str, Any]]:
        """
        Retrieve the search history for a user.

        Args:
            email: User's email.

        Returns:
            List[Dict[str, Any]]: List of search history records.
        """
        return self.search_store.get_search_history(email)

    # -----------------------------------------------------------------------------
    # LEGISLATION METHODS - Delegate to LegislationStore
    # -----------------------------------------------------------------------------
    def list_legislation(self, limit: int = 50, offset: int = 0) -> PaginatedLegislation:
        """
        List legislation records with pagination. Returns both items and total count.

        Args:
            limit: Maximum items to return.
            offset: Number of items to skip.

        Returns:
            PaginatedLegislation: Dictionary with 'total_count', 'items', and 'page_info'.
        """
        return self.legislation_store.list_legislation(limit, offset)

    def get_legislation_details(self, legislation_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve detailed information for a specific legislation record.

        Args:
            legislation_id: The ID of the legislation.

        Returns:
            Optional[Dict[str, Any]]: Detailed record, or None if not found.
        """
        return self.legislation_store.get_legislation_details(legislation_id)

    def search_legislation_by_keywords(self, keywords: Union[str, List[str]], limit: int = 50, offset: int = 0) -> PaginatedLegislation:
        """
        Search for legislation whose title or description contains the given keywords.

        Args:
            keywords: String of comma-separated keywords or list of keywords
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            PaginatedLegislation: Dictionary with search results and pagination metadata
        """
        return self.legislation_store.search_legislation_by_keywords(keywords, limit, offset)
        
    def search_legislation_advanced(
        self,
        query: str,
        filters: Optional['BillSearchFilters'] = None, # Use the Pydantic model type hint
        sort_by: str = "relevance",
        sort_dir: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> PaginatedLegislation:
        """
        Perform an advanced search for legislation using various filters and sorting.

        Args:
            query: Search query string.
            filters: Dictionary of filter criteria (e.g., impact_level, status).
            sort_by: Field to sort results by.
            sort_dir: Sort direction ('asc' or 'desc').
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            PaginatedLegislation: Dictionary with search results and pagination metadata.
        """
        # Delegate the call to the LegislationStore
        return self.legislation_store.search_legislation_advanced(
            query=query,
            filters=filters,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset
        )
        
    # -----------------------------------------------------------------------------
    # TEXAS-SPECIFIC METHODS - Delegate to TexasLegislationStore
    # -----------------------------------------------------------------------------
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
        return self.texas_store.get_texas_health_legislation(limit, offset, filters)
        
    # -----------------------------------------------------------------------------
    # ANALYTICS METHODS - Delegate to AnalyticsStore
    # -----------------------------------------------------------------------------
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
        return self.analytics_store.get_impact_summary(impact_type, time_period)
    
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
        return self.analytics_store.get_recent_activity(days, limit, offset) 