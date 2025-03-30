"""
Sync operations for the LegiScan API.

This module provides functionality for syncing legislation data with LegiScan.
"""

import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models import (
    Legislation, 
    SyncMetadata, 
    SyncStatusEnum, 
    SyncError,
    DataSourceEnum
)
from app.legiscan.db import save_bill_to_db, record_sync_error

logger = logging.getLogger(__name__)


class SyncManager:
    """
    Manages the synchronization process between LegiScan API and the local database.
    """
    
    def __init__(self, db_session: Session, api_client):
        """
        Initialize the sync manager.
        
        Args:
            db_session: SQLAlchemy database session
            api_client: ApiClient instance for LegiScan API requests
        """
        self.db_session = db_session
        self.api_client = api_client
        self.monitored_jurisdictions = ["US", "TX"]
        
    def run_sync(self, sync_type: str = "daily") -> Dict[str, Any]:
        """
        Runs a complete sync operation for all monitored jurisdictions.

        Args:
            sync_type: Type of sync (e.g., "daily", "weekly", "manual")

        Returns:
            Dictionary with sync statistics and status
        """
        # Initialize sync metadata and summary
        sync_meta, summary = self._initialize_sync(sync_type)
        
        try:
            # Process all jurisdictions
            self._process_all_jurisdictions(sync_meta, summary)
            
            # Finalize sync with success status
            self._finalize_sync_success(sync_meta, summary)
            
        except Exception as e:
            # Handle critical errors
            self._handle_sync_critical_error(e, sync_meta, summary)
            
        finally:
            # Ensure we commit any pending changes
            self._commit_sync_changes(sync_meta)
            
        return summary
        
    def _initialize_sync(self, sync_type: str) -> Tuple[SyncMetadata, Dict[str, Any]]:
        """Initialize sync metadata and summary dictionary."""
        sync_start = datetime.now(timezone.utc)
        
        # Create a sync metadata record
        sync_meta = SyncMetadata(
            last_sync=sync_start,
            status=SyncStatusEnum.in_progress,
            sync_type=sync_type
        )
        self.db_session.add(sync_meta)
        self.db_session.commit()
        
        # Initialize summary dictionary
        summary = {
            "new_bills": 0,
            "bills_updated": 0,
            "errors": [],
            "start_time": sync_start,
            "end_time": None,
            "status": "in_progress",
            "amendments_tracked": 0
        }
        
        return sync_meta, summary
        
    def _process_all_jurisdictions(self, sync_meta: SyncMetadata, summary: Dict[str, Any]) -> None:
        """Process all monitored jurisdictions."""
        for state in self.monitored_jurisdictions:
            self._process_jurisdiction(state, sync_meta, summary)
            
    def _process_jurisdiction(self, state: str, sync_meta: SyncMetadata, summary: Dict[str, Any]) -> None:
        """Process a single jurisdiction's active sessions."""
        # Get active sessions for this state
        active_sessions = self._get_active_sessions(state)
        
        for session in active_sessions:
            self._process_session(session, sync_meta, summary)
            
    def _process_session(self, session: Dict[str, Any], sync_meta: SyncMetadata, summary: Dict[str, Any]) -> None:
        """Process a single legislative session."""
        session_id = session.get("session_id")
        if not session_id:
            return
            
        # Get the master bill list with change_hash
        data = self.api_client.make_request("getMasterListRaw", {"id": session_id})
        master_list = data.get("masterlist", {})
        
        if not master_list:
            summary["errors"].append(f"Failed to get master list for session {session_id}")
            return
            
        # Get list of bills that need updating
        changed_bill_ids = self._identify_changed_bills(master_list)
        
        # Process each changed bill
        for bill_id in changed_bill_ids:
            self._process_bill(bill_id, sync_meta, summary)
            
    def _process_bill(self, bill_id: int, sync_meta: SyncMetadata, summary: Dict[str, Any]) -> None:
        """Process a single bill that needs updating."""
        try:
            # Get full bill details
            data = self.api_client.make_request("getBill", {"id": bill_id})
            bill_data = data.get("bill")
            
            if not bill_data:
                return

            # Save to database
            if bill_obj := save_bill_to_db(self.db_session, bill_data, detect_relevance=True):
                # Update summary statistics
                self._update_bill_statistics(bill_obj, bill_data, summary)
            else:
                return

        except Exception as e:
            self._record_bill_processing_error(bill_id, e, sync_meta, summary)
            
    def _update_bill_statistics(self, bill_obj: Legislation, bill_data: Dict[str, Any], summary: Dict[str, Any]) -> None:
        """Update summary statistics based on bill processing results."""
        # Determine if this is a new bill or an update
        created = getattr(bill_obj, 'created_at', None)
        updated = getattr(bill_obj, 'updated_at', None)
        
        if created is not None and updated is not None and created == updated:
            summary["new_bills"] += 1
        else:
            summary["bills_updated"] += 1
            
        # Count amendments if present
        if "amendments" in bill_data and isinstance(bill_data["amendments"], list):
            summary["amendments_tracked"] += len(bill_data["amendments"])
            
    def _record_bill_processing_error(self, bill_id: int, e: Exception, sync_meta: SyncMetadata, summary: Dict[str, Any]) -> None:
        """Record an error that occurred during bill processing."""
        error_msg = f"Error processing bill {bill_id}: {str(e)}"
        logger.error(error_msg)
        summary["errors"].append(error_msg)
        
        # Record the error in the database
        record_sync_error(
            self.db_session, 
            sync_meta.id, 
            "bill_processing", 
            error_msg
        )
        
    def _finalize_sync_success(self, sync_meta: SyncMetadata, summary: Dict[str, Any]) -> None:
        """Update sync metadata with success status and summary information."""
        # Update bill counts
        sync_meta.bills_updated = summary["bills_updated"]
        sync_meta.new_bills = summary["new_bills"]
        
        # Set last successful sync time
        setattr(sync_meta, "last_successful_sync", datetime.now(timezone.utc))
        
        # Set appropriate status based on errors
        if summary["errors"]:
            setattr(sync_meta, 'status', SyncStatusEnum.partial)
            setattr(sync_meta, 'errors', {
                "count": len(summary["errors"]),
                "samples": summary["errors"][:5]
            })
        else:
            setattr(sync_meta, "status", SyncStatusEnum.completed)
            
        # Update summary
        summary["status"] = str(sync_meta.status)
        summary["end_time"] = datetime.now(timezone.utc)
        
    def _commit_sync_changes(self, sync_meta: SyncMetadata) -> None:
        """Commit any pending changes to the database."""
        try:
            self.db_session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Failed to commit sync metadata updates: {e}")
            self.db_session.rollback()

    def _get_active_sessions(self, state: str) -> List[Dict[str, Any]]:
        """
        Gets active legislative sessions for a state.

        Args:
            state: Two-letter state code

        Returns:
            List of active session dictionaries
        """
        data = self.api_client.make_request("getSessionList", {"state": state})
        sessions = data.get("sessions", [])
        current_year = datetime.now().year

        return [
            session
            for session in sessions
            if (
                session.get("year_end", 0) >= current_year
                or session.get("sine_die", 1) == 0
            )
        ]

    def _identify_changed_bills(self, master_list: Dict[str, Any]) -> List[int]:
        """
        Identifies bills that need updating based on change_hash comparison.

        Args:
            master_list: Master bill list from LegiScan API

        Returns:
            List of bill IDs that need updating
        """
        if not master_list:
            return []

        changed_bill_ids = []

        for key, bill_info in master_list.items():
            if key == "0":  # Skip metadata
                continue

            bill_id = bill_info.get("bill_id")
            change_hash = bill_info.get("change_hash")

            if not bill_id or not change_hash:
                continue

            # Check if we have this bill and if the change_hash is different
            existing = self.db_session.query(Legislation).filter(
                Legislation.external_id == str(bill_id),
                Legislation.data_source == DataSourceEnum.legiscan
            ).first()

            if not existing or existing.change_hash != change_hash:
                changed_bill_ids.append(bill_id)

        return changed_bill_ids
        
    def _handle_sync_critical_error(self, e: Exception, sync_meta: SyncMetadata, summary: Dict[str, Any]) -> None:
        """
        Handle critical errors during sync operations.
        
        Args:
            e: The exception that occurred
            sync_meta: The sync metadata record to update
            summary: The summary dictionary to update
        """
        error_msg = f"Fatal error in sync operation: {str(e)}"
        logger.error(error_msg, exc_info=True)

        setattr(sync_meta, "status", SyncStatusEnum.failed)
        setattr(sync_meta, 'errors', {"critical_error": error_msg})

        sync_error = SyncError(
            sync_id=sync_meta.id,
            error_type="fatal_error",
            error_message=error_msg,
            stack_trace=str(sys.exc_info())
        )
        self.db_session.add(sync_error)

        summary["status"] = "failed"
        summary["errors"].append(error_msg)
        summary["end_time"] = datetime.now(timezone.utc)
        
    def lookup_bills_by_keywords(self, keywords: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Searches for bills matching the given keywords using LegiScan's search API.

        Args:
            keywords: List of keywords to search for
            limit: Maximum number of results to return

        Returns:
            List of bill information dictionaries
        """
        if not keywords:
            return []

        results = []
        query = " AND ".join(keywords)

        # Search in monitored jurisdictions
        for state in self.monitored_jurisdictions:
            try:
                # Start with state-specific search
                data = self.api_client.make_request("getSearchRaw", {
                    "state": state,
                    "query": query,
                    "year": 2  # Current sessions
                })

                search_results = data.get("searchresult", {})

                # Skip the summary info
                for key, item in search_results.items():
                    if key != "summary" and isinstance(item, dict):
                        results.append({
                            "bill_id": item.get("bill_id"),
                            "change_hash": item.get("change_hash"),
                            "relevance": item.get("relevance", 0),
                            "state": state,
                            "bill_number": item.get("bill_number"),
                            "title": item.get("title", "")
                        })

                        if len(results) >= limit:
                            break

            except Exception as e:
                logger.error(f"Error searching bills with keywords {keywords} in {state}: {e}")

        return results 