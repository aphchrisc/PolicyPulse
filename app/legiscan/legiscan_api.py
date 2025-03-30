"""
LegiScan API client for retrieving and managing legislation data.

This module provides the LegiScanAPI class which serves as the main interface
for interacting with the LegiScan API and storing/updating data in the database.
"""

import logging
from typing import Optional, Dict, Any, List, Union

from sqlalchemy.orm import Session

from app.legiscan.api import create_api_client
from app.legiscan.db import save_bill_to_db
from app.legiscan.sync import SyncManager
from app.legiscan.relevance import RelevanceScorer, get_relevant_texas_legislation
from app.legiscan.exceptions import ApiError

logger = logging.getLogger(__name__)


class LegiScanAPI:
    """
    Client for interacting with the LegiScan API and storing/updating 
    legislation data in the local database.

    Focuses on US Congress and Texas legislation with special attention to
    bills relevant to public health and local government.
    """

    def __init__(self, db_session: Session, api_key: Optional[str] = None):
        """
        Initialize the LegiScan API client.

        Args:
            db_session: SQLAlchemy session for database operations
            api_key: Optional API key (uses LEGISCAN_API_KEY env var if not provided)

        Raises:
            ValueError: If no API key is available
        """
        # Initialize the API client
        self.api_client = create_api_client(api_key)
        self.db_session = db_session

        # Initialize relevance scorer
        self.relevance_scorer = RelevanceScorer()
        
        # Initialize sync manager
        self.sync_manager = SyncManager(db_session, self.api_client)
        
        # Texas & US focus
        self.monitored_jurisdictions = ["US", "TX"]

    # ------------------------------------------------------------------------
    # Common calls to LegiScan
    # ------------------------------------------------------------------------
    def get_session_list(self, state: str) -> List[Dict[str, Any]]:
        """
        Retrieves available legislative sessions for a state.

        Args:
            state: Two-letter state code

        Returns:
            List of session information dictionaries
        """
        try:
            data = self.api_client.make_request("getSessionList", {"state": state})
            return data.get("sessions", [])
        except ApiError as e:
            logger.error("get_session_list(%s) failed: %s", state, e)
            return []

    def get_master_list(self, session_id: int) -> Dict[str, Any]:
        """
        Retrieves the full master bill list for a session.

        Args:
            session_id: LegiScan session ID

        Returns:
            Dictionary of bill information
        """
        try:
            data = self.api_client.make_request("getMasterList", {"id": session_id})
            return data.get("masterlist", {})
        except ApiError as e:
            logger.error("get_master_list(%s) failed: %s", session_id, e)
            return {}

    def get_master_list_raw(self, session_id: int) -> Dict[str, Any]:
        """
        Retrieves the optimized master bill list for change detection.
        The raw version includes change_hash values for efficient updates.

        Args:
            session_id: LegiScan session ID

        Returns:
            Dictionary of bill information with change_hash values
        """
        try:
            data = self.api_client.make_request("getMasterListRaw", {"id": session_id})
            return data.get("masterlist", {})
        except ApiError as e:
            logger.error("get_master_list_raw(%s) failed: %s", session_id, e)
            return {}

    def get_bill(self, bill_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves detailed information for a specific bill.

        Args:
            bill_id: LegiScan bill ID

        Returns:
            Dictionary with bill details or None if not found
        """
        try:
            data = self.api_client.make_request("getBill", {"id": bill_id})
            return data.get("bill")
        except ApiError as e:
            logger.error("get_bill(%s) failed: %s", bill_id, e)
            return None

    def get_bill_text(self, doc_id: int) -> Optional[Union[str, bytes]]:
        """
        Retrieves the text content of a bill document.

        Args:
            doc_id: LegiScan document ID

        Returns:
            Decoded text content (str) for text documents,
            raw bytes for binary content (e.g., PDFs), or
            None if retrieval fails
        """
        # Import here to avoid circular imports
        from app.legiscan.models import decode_bill_text
        
        try:
            data = self.api_client.make_request("getBillText", {"id": doc_id})
            text_obj = data.get("text", {})
            
            if encoded := text_obj.get("doc"):
                # Decode the content
                content, _ = decode_bill_text(encoded)
                return content
                
            return None
        except ApiError as e:
            logger.error("get_bill_text(%s) failed: %s", doc_id, e)
            return None

    # ------------------------------------------------------------------------
    # DB Save/Update
    # ------------------------------------------------------------------------
    def save_bill_to_db(self, bill_data: Dict[str, Any], detect_relevance: bool = True) -> Optional[Any]:
        """
        Creates or updates a bill record in the database based on LegiScan data.

        Args:
            bill_data: Bill information from LegiScan API
            detect_relevance: Whether to calculate relevance scores for Texas public health

        Returns:
            Updated or created Legislation object, or None on failure
        """
        return save_bill_to_db(self.db_session, bill_data, detect_relevance)

    # ------------------------------------------------------------------------
    # Sync Operations
    # ------------------------------------------------------------------------
    def run_sync(self, sync_type: str = "daily") -> Dict[str, Any]:
        """
        Runs a complete sync operation for all monitored jurisdictions.

        Args:
            sync_type: Type of sync (e.g., "daily", "weekly", "manual")

        Returns:
            Dictionary with sync statistics and status
        """
        return self.sync_manager.run_sync(sync_type)

    def lookup_bills_by_keywords(self, keywords: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Searches for bills matching the given keywords using LegiScan's search API.

        Args:
            keywords: List of keywords to search for
            limit: Maximum number of results to return

        Returns:
            List of bill information dictionaries
        """
        return self.sync_manager.lookup_bills_by_keywords(keywords, limit)

    def get_bill_relevance_score(self, bill_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Calculates relevance scores for public health and local government.

        Args:
            bill_data: Bill information dictionary

        Returns:
            Dictionary with relevance scores for health, local government, and overall
        """
        return self.relevance_scorer.calculate_relevance(bill_data)

    def get_relevant_texas_legislation(
        self, relevance_type: str = "health", min_score: int = 50, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieves legislation particularly relevant to Texas public health or local government.

        Args:
            relevance_type: Type of relevance to filter by ("health", "local_govt", or "both")
            min_score: Minimum relevance score (0-100)
            limit: Maximum number of results to return

        Returns:
            List of relevant legislation dictionaries
        """
        return get_relevant_texas_legislation(self.db_session, relevance_type, min_score, limit)

    def check_status(self) -> Dict[str, Any]:
        """
        Check the status of the LegiScan API connection.
        
        Returns:
            Dict with status information
            
        Raises:
            ApiError: If unable to connect to LegiScan API
        """
        status = self.api_client.check_status()
        
        # Add additional information
        status["monitored_jurisdictions"] = self.monitored_jurisdictions
        
        return status 