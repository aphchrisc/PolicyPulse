"""
scheduler/sync_manager.py

Core synchronization manager for legislation data.
"""

import contextlib
import logging
import traceback
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from app.models import (
    SyncMetadata, SyncError as DBSyncError, SyncStatusEnum,
    Legislation
)
from app.legiscan_api import LegiScanAPI
from app.ai_analysis import AIAnalysis
from app.scheduler.errors import DataSyncError, AnalysisError
from app.scheduler.utils import safe_getattr, initialize_sync_summary
# Importing a protected helper function - consider moving this logic to a public API
from app.scheduler.amendments import _get_bill_id_safely, track_amendments

logger = logging.getLogger(__name__)


class LegislationSyncManager:
    """
    Orchestrates the actual data sync from LegiScan and manages
    AI analysis for all new and updated bills.
    """

    def __init__(self, db_session_factory: sessionmaker):
        """
        Initialize the sync manager with the provided database session factory.

        Args:
            db_session_factory: SQLAlchemy sessionmaker for creating database sessions
        """
        self.db_session_factory = db_session_factory

        # Keywords for determining relevance to Texas public health
        self.health_keywords = [
            "health", "healthcare", "public health", "medicaid", "medicare",
            "hospital", "physician", "vaccine", "immunization", "disease",
            "epidemic", "pandemic", "mental health", "substance abuse",
            "addiction", "opioid", "healthcare workforce"
        ]

        # Keywords for determining relevance to Texas local government
        self.local_govt_keywords = [
            "municipal", "county", "local government", "city council",
            "zoning", "property tax", "infrastructure", "public works",
            "community development", "ordinance", "school district",
            "special district", "county commissioner"
        ]

        self.target_jurisdictions = ["US", "TX"]
        
    def run_nightly_sync(self) -> Dict[str, Any]:
        """
        Performs nightly sync with LegiScan and triggers immediate AI analysis
        for all new and changed bills.

        Returns:
            Dictionary with summary of sync operations
        """
        db_session = self.db_session_factory()
        summary = initialize_sync_summary()
        sync_meta = None

        try:
            api = LegiScanAPI(db_session)
            sync_meta = self._create_sync_metadata_record(db_session)
            bills_to_analyze = self._process_jurisdictions(db_session, api, summary, sync_meta)
            self._analyze_bills(db_session, bills_to_analyze, summary, sync_meta)
            self._update_sync_metadata(db_session, sync_meta, summary)
            
            logger.info(
                "Nightly sync completed. New bills: %(new)s, Updated: %(updated)s, Analyzed: %(analyzed)s, Amendments: %(amendments)s, Errors: %(errors)s",
                {
                    "new": summary['new_bills'], 
                    "updated": summary['bills_updated'],
                    "analyzed": summary['bills_analyzed'],
                    "amendments": summary['amendments_tracked'],
                    "errors": len(summary['errors'])
                })

        except DataSyncError as e:
            self._handle_sync_error(db_session, sync_meta, e, "data_sync_error", summary)
        except AnalysisError as e:
            self._handle_sync_error(db_session, sync_meta, e, "analysis_error", summary)
        except SQLAlchemyError as e:
            self._handle_sync_error(db_session, sync_meta, e, "database_error", summary)
        except Exception as e:
            self._handle_sync_error(db_session, sync_meta, e, "fatal_error", summary)
        finally:
            summary["end_time"] = datetime.now(timezone.utc)
            with contextlib.suppress(Exception):
                db_session.close()
        return summary
        
    def _initialize_sync_summary(self) -> Dict[str, Any]:
        """Initialize the summary dictionary for sync operations."""
        return initialize_sync_summary()
        
    def _create_sync_metadata_record(self, db_session: Session) -> SyncMetadata:
        """Create and persist a sync metadata record to track this operation."""
        sync_meta = SyncMetadata(
            last_sync=datetime.now(timezone.utc),
            status=SyncStatusEnum.in_progress,
            sync_type="nightly"
        )
        db_session.add(sync_meta)
        db_session.commit()
        return sync_meta
        
    def _process_jurisdictions(
        self,
        db_session: Session,
        api: LegiScanAPI,
        summary: Dict[str, Any],
        sync_meta: SyncMetadata
    ) -> List[int]:
        """
        Process each target jurisdiction to find and save new/updated bills.
        
        Args:
            db_session: Database session
            api: LegiScan API client
            summary: Summary dictionary to update
            sync_meta: Sync metadata record
            
        Returns:
            List of bill IDs to analyze
        """
        bills_to_analyze = []
        
        for state in self.target_jurisdictions:
            try:
                bills_to_analyze.extend(
                    self._process_jurisdiction(db_session, api, state, summary, sync_meta)
                )
            except DataSyncError as e:
                error_msg = f"Error processing jurisdiction {state}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                summary["errors"].append(error_msg)

                # Record error but continue with other jurisdictions
                sync_error = DBSyncError(
                    sync_id=sync_meta.id,
                    error_type="jurisdiction_processing",
                    error_message=error_msg,
                    stack_trace=traceback.format_exc()
                )
                db_session.add(sync_error)
                db_session.commit()
                
        return bills_to_analyze
        
    def _process_jurisdiction(
        self,
        db_session: Session,
        api: LegiScanAPI,
        state: str,
        summary: Dict[str, Any],
        sync_meta: SyncMetadata
    ) -> List[int]:
        """
        Process a single jurisdiction to find and save new/updated bills.
        
        Args:
            db_session: Database session
            api: LegiScan API client
            state: State code
            summary: Summary dictionary to update
            sync_meta: Sync metadata record
            
        Returns:
            List of bill IDs to analyze
        """
        bills_to_analyze = []
        sessions = self._get_active_sessions(api, state)

        for session in sessions:
            session_id = session.get("session_id")
            if not session_id:
                continue

            # Get master list for change detection
            master_list = api.get_master_list_raw(session_id)
            if not master_list:
                error_msg = f"Failed to retrieve master list for session {session_id} in {state}"
                logger.warning(error_msg)
                summary["errors"].append(error_msg)
                continue

            # Process changed or new bills
            bill_ids = self._identify_changed_bills(db_session, master_list)

            # Process each bill
            for bill_id in bill_ids:
                try:
                    if bill_result := self._process_bill(
                        db_session, api, bill_id, summary, sync_meta
                    ):
                        bills_to_analyze.append(bill_result)
                except SQLAlchemyError as e:
                    error_msg = f"Failed to save bill {bill_id}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    summary["errors"].append(error_msg)

                    # Log error to database
                    sync_error = DBSyncError(
                        sync_id=sync_meta.id,
                        error_type="bill_processing",
                        error_message=error_msg,
                        stack_trace=traceback.format_exc()
                    )
                    db_session.add(sync_error)
                    db_session.commit()

        return bills_to_analyze
        
    def _process_bill(
        self,
        db_session: Session,
        api: LegiScanAPI,
        bill_id: int,
        summary: Dict[str, Any],
        sync_meta: SyncMetadata
    ) -> Optional[int]:
        """
        Process a single bill, saving it to the database.
        
        Args:
            db_session: Database session
            api: LegiScan API client
            bill_id: Bill ID
            summary: Summary dictionary to update
            sync_meta: Sync metadata record
            
        Returns:
            Bill ID to analyze if successful, None otherwise
        """
        # Get full bill details
        bill_data = api.get_bill(bill_id)
        if not bill_data:
            return None

        if bill_obj := api.save_bill_to_db(bill_data, detect_relevance=True):
            # Compare datetime values, not SQLAlchemy column objects
            try:
                if bill_obj.created_at.isoformat() == bill_obj.updated_at.isoformat():
                    summary["new_bills"] += 1
                else:
                    summary["bills_updated"] += 1
            except (AttributeError, ValueError) as e:
                # If comparing timestamps fails, just count it as updated
                logger.warning("Error comparing timestamps for bill %s: %s", bill_id, e)
                summary["bills_updated"] += 1

            # Track amendments back to parent bills
            if "amendments" in bill_data and bill_data["amendments"]:
                self._process_amendments(db_session, bill_obj, bill_data["amendments"], summary)

            bill_id_value = _get_bill_id_safely(bill_obj)
            if bill_id_value is not None:
                return bill_id_value
                
        return None
        
    def _process_amendments(
        self,
        db_session: Session, 
        bill_obj: Legislation, 
        amendments: List[Dict[str, Any]], 
        summary: Dict[str, Any]
    ) -> None:
        """
        Process amendments by importing track_amendments function safely.
        
        Args:
            db_session: Database session
            bill_obj: Legislation object
            amendments: List of amendment data
            summary: Summary dictionary to update
        """
        try:
            # Track the amendments
            amendments_count = track_amendments(db_session, bill_obj, amendments)
            summary["amendments_tracked"] += amendments_count
            logger.debug("Tracked %s amendments", amendments_count)
        except ImportError as e:
            logger.warning("Could not import track_amendments function: %s", e)
            self._store_amendments_in_raw_data(bill_obj, amendments)
        except Exception as e:
            logger.warning("Error tracking amendments: %s", e)
            # Try to store in raw data as a fallback
            self._store_amendments_in_raw_data(bill_obj, amendments)

    def _store_amendments_in_raw_data(self, bill: Legislation, amendments: List[Dict[str, Any]]) -> None:
        """
        Store amendments in bill's raw_api_response as a fallback.
        
        Args:
            bill: Legislation object
            amendments: List of amendment data
        """
        try:
            # Get the current raw_api_response safely
            raw_data = safe_getattr(bill, 'raw_api_response', {})
            
            # Make sure it's a dictionary
            if not isinstance(raw_data, dict):
                # Try to convert from string if needed
                if isinstance(raw_data, str):
                    # json is already imported at the top of the file
                    try:
                        raw_data = json.loads(raw_data)
                    except json.JSONDecodeError:
                        raw_data = {}
                else:
                    raw_data = {}
                    
            # Store the amendments
            if "amendments" not in raw_data:
                raw_data["amendments"] = []
                
            # Add any amendments that aren't already tracked
            existing_ids = {a.get("amendment_id") for a in raw_data["amendments"] if a.get("amendment_id")}
            for amend in amendments:
                if amend.get("amendment_id") and amend.get("amendment_id") not in existing_ids:
                    raw_data["amendments"].append(amend)
                    
            # Save the updated raw_api_response
            setattr(bill, "raw_api_response", raw_data)
            logger.debug("Stored amendments in raw_api_response as fallback")
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning("Failed to store amendments in raw_api_response: %s", e)
            
    def _analyze_bills(
        self,
        db_session: Session,
        bills_to_analyze: List[int],
        summary: Dict[str, Any],
        sync_meta: SyncMetadata
    ) -> None:
        """
        Analyze bills using AI analysis.
        
        Args:
            db_session: Database session
            bills_to_analyze: List of bill IDs to analyze
            summary: Summary dictionary to update
            sync_meta: Sync metadata record
        """
        if not bills_to_analyze:
            return
            
        analyzer = AIAnalysis(db_session=db_session)

        for leg_id in bills_to_analyze:
            try:
                analyzer.analyze_legislation(legislation_id=leg_id)
                summary["bills_analyzed"] += 1
            except (ValueError, KeyError, RuntimeError) as e:
                error_msg = f"Error analyzing legislation {leg_id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                summary["errors"].append(error_msg)

                # Log analysis error
                sync_error = DBSyncError(
                    sync_id=sync_meta.id,
                    error_type="analysis_error",
                    error_message=error_msg,
                    stack_trace=traceback.format_exc()
                )
                db_session.add(sync_error)
                db_session.commit()
                
    def _update_sync_metadata(
        self,
        db_session: Session,
        sync_meta: Optional[SyncMetadata],
        summary: Dict[str, Any]
    ) -> None:
        """
        Update the sync metadata record with results.
        
        Args:
            db_session: Database session
            sync_meta: Sync metadata record
            summary: Summary dictionary
        """
        if not sync_meta:
            return
            
        sync_meta.status = SyncStatusEnum.partial if summary["errors"] else SyncStatusEnum.completed
        sync_meta.last_successful_sync = datetime.now(timezone.utc)
        sync_meta.bills_updated = summary["bills_updated"]
        sync_meta.new_bills = summary["new_bills"]

        if summary["errors"]:
            # Only include the first 5 errors to avoid exceeding field size limits
            try:
                # Create a dictionary for the errors
                error_dict = {
                    "count": len(summary["errors"]),
                    "samples": summary["errors"][:5]
                }
                # Assign the dictionary directly (not as JSON string)
                sync_meta.errors = error_dict  # type: ignore
            except (TypeError, ValueError) as e:
                logger.warning("Error setting errors on sync_meta: %s", e)
                # Use a simple dict as fallback
                sync_meta.errors = {"error": "Failed to set errors"}  # type: ignore

        db_session.commit()
        
    def _handle_sync_error(
        self,
        db_session: Session,
        sync_meta: Optional[SyncMetadata],
        exception: Exception,
        error_type: str,
        summary: Dict[str, Any]
    ) -> None:
        """
        Handle sync errors consistently.
        
        Args:
            db_session: Database session
            sync_meta: Sync metadata record
            exception: Exception that occurred
            error_type: Type of error
            summary: Summary dictionary to update
        """
        error_msg = f"{error_type.replace('_', ' ').title()} in nightly sync: {exception}"
        logger.error(error_msg, exc_info=True)
        summary["errors"].append(f"{error_type.replace('_', ' ').title()}: {str(exception)}")
        
        if sync_meta:
            self._record_critical_error(db_session, sync_meta, exception, error_type)

    def _record_critical_error(self, db_session: Session,
                              sync_meta: SyncMetadata, exception: Exception,
                              error_type: str) -> None:
        """
        Record a critical error in the sync metadata and error log.

        Args:
            db_session: Database session
            sync_meta: SyncMetadata record
            exception: The exception that occurred
            error_type: Type of error
        """
        try:
            sync_meta.status = SyncStatusEnum.failed
            # Set errors as a dictionary, not a string
            sync_meta.errors = {"critical_error": str(exception)}  # type: ignore

            sync_error = DBSyncError(sync_id=sync_meta.id,
                                    error_type=error_type,
                                    error_message=str(exception),
                                    stack_trace=traceback.format_exc())
            db_session.add(sync_error)
            db_session.commit()
        except SQLAlchemyError as e:
            logger.error("Failed to record critical error: %s", e)
            with contextlib.suppress(Exception):
                db_session.rollback()

    def _get_active_sessions(self, api: LegiScanAPI,
                            state: str) -> List[Dict[str, Any]]:
        """
        Gets active legislative sessions for a state.

        Args:
            api: LegiScanAPI instance
            state: Two-letter state code

        Returns:
            List of active session dictionaries

        Raises:
            DataSyncError: If unable to retrieve sessions
        """
        try:
            return self._filter_active_sessions(api, state)
        except (ValueError, KeyError) as e:
            error_msg = f"Error retrieving active sessions for {state}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise DataSyncError(error_msg) from e

    def _filter_active_sessions(self, api: LegiScanAPI, state: str) -> List[Dict[str, Any]]:
        """
        Filter sessions to only include active ones based on current year.
        
        Args:
            api: LegiScanAPI instance
            state: Two-letter state code
            
        Returns:
            List of active session dictionaries
        """
        sessions = api.get_session_list(state)
        if not sessions:
            logger.warning("No sessions found for state %s", state)
            return []

        current_year = datetime.now().year

        return [
            session
            for session in sessions
            if (
                session.get("year_end", 0) >= current_year
                or session.get("sine_die", 1) == 0
            )
        ]

    def _identify_changed_bills(self, db_session: Session,
                              master_list: Dict[str, Any]) -> List[int]:
        """
        Identifies bills that have been added or changed since last sync.

        Args:
            db_session: SQLAlchemy database session
            master_list: Master bill list from LegiScan API

        Returns:
            List of bill IDs that need updating

        Raises:
            DataSyncError: If unable to process the master list
        """
        if not master_list:
            return []

        try:
            changed_bill_ids = []

            for key, bill_info in master_list.items():
                if key == "0":  # Skip metadata
                    continue

                bill_id = bill_info.get("bill_id")
                change_hash = bill_info.get("change_hash")

                if not bill_id or not change_hash:
                    continue

                # Check if we have this bill and if the change_hash is different
                existing = db_session.query(Legislation).filter(
                    Legislation.external_id == str(bill_id),
                    Legislation.data_source == "legiscan"
                ).first()

                if not existing or existing.change_hash != change_hash:
                    changed_bill_ids.append(bill_id)

            return changed_bill_ids
        except SQLAlchemyError as e:
            error_msg = f"Database error while identifying changed bills: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise DataSyncError(error_msg) from e
        except (ValueError, KeyError, TypeError) as e:
            error_msg = f"Error identifying changed bills: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise DataSyncError(error_msg) from e
            
    def seed_historical_data(self, start_date: str = "2025-01-01") -> Dict[str, Any]:
        """
        Seed the database with historical legislation since the specified start date.
        Default is January 1, 2025.

        Args:
            start_date: ISO format date string (YYYY-MM-DD)

        Returns:
            Dictionary with seeding statistics
        """
        db_session = self.db_session_factory()
        
        try:
            return self._call_seed_historical_data(db_session, start_date)
        except Exception as e:
            logger.error("Error during historical seeding: %s", e, exc_info=True)
            return {
                "error": str(e),
                "success": False,
                "start_date": start_date
            }
        finally:
            db_session.close()
            
    def _call_seed_historical_data(self, db_session: Session, start_date: str) -> Dict[str, Any]:
        """Call the seed_historical_data function safely."""
        try:
            from app.scheduler.seeding import seed_historical_data as seed_data
            
            # Call the function with max_bills parameter
            return seed_data(
                db_session=db_session,
                start_date=start_date,
                target_jurisdictions=self.target_jurisdictions,
                max_bills=getattr(self, "max_bills", 100)  # Use configured max_bills or default to 100
            )
        except ImportError as e:
            logger.error("Could not import seed_historical_data function: %s", e)
            return self._perform_fallback_seeding(start_date)
            
    def _perform_fallback_seeding(self, start_date: str) -> Dict[str, Any]:
        """
        Fallback implementation if the seeding module isn't available.
        
        This is a minimal implementation that returns a failure message.
        In a real implementation, you might implement basic seeding logic here.
        """
        logger.warning("Using fallback seeding implementation - this is minimal functionality")
        return {
            "error": "Seeding module not available - using minimal fallback",
            "success": False,
            "start_date": start_date,
            "bills_added": 0,
            "bills_analyzed": 0
        } 