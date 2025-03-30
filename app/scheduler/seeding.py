"""
scheduler/seeding.py

Functions for seeding the database with historical legislation data.
"""

import logging
import contextlib
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Legislation, LegislationAnalysis
from app.legiscan_api import LegiScanAPI
from app.ai_analysis import AIAnalysis
from app.scheduler.utils import safe_getattr
from app.scheduler.amendments import track_amendments

logger = logging.getLogger(__name__)


def parse_start_date(start_date: str) -> datetime:
    """Parse the start date string into a datetime object."""
    try:
        return datetime.fromisoformat(start_date)
    except ValueError:
        logger.error("Invalid start date format: %s. Using 2025-01-01.", start_date)
        return datetime.fromisoformat("2025-01-01")


def initialize_seeding_summary(start_date: str) -> Dict[str, Any]:
    """Initialize the summary dictionary for seeding operations."""
    return {
        "start_date": start_date,
        "bills_added": 0,
        "bills_analyzed": 0,
        "verification_success": False,
        "verification_errors": [],
        "errors": [],
        "sessions_processed": [],
        "start_time": datetime.now(),
        "end_time": None
    }


def log_seeding_error(error_type: str, exception: Exception, summary: Dict[str, Any]) -> None:
    """Log a seeding error and add it to the summary."""
    error_msg = f"{error_type} in historical seeding: {exception}"
    logger.error(error_msg, exc_info=True)
    summary["errors"].append(f"{error_type}: {str(exception)}")


def seed_historical_data(db_session: Session, start_date: str = "2025-01-01",
                         target_jurisdictions: Optional[List[str]] = None,
                         max_bills: int = 100) -> Dict[str, Any]:
    """
    Seed the database with historical legislation since the specified start date.
    Default is January 1, 2025.

    Args:
        db_session: Database session
        start_date: ISO format date string (YYYY-MM-DD)
        target_jurisdictions: List of jurisdictions to seed (default: ["US", "TX"])
        max_bills: Maximum number of bills to add (default: 100)

    Returns:
        Dictionary with seeding statistics
    """
    api = LegiScanAPI(db_session)
    
    # Set default target jurisdictions if None
    if target_jurisdictions is None:
        target_jurisdictions = ["US", "TX"]
    
    # Parse start date and initialize summary
    start_datetime = parse_start_date(start_date)
    summary = initialize_seeding_summary(start_date)
    summary["max_bills"] = max_bills
    
    try:
        # Verification step - test analysis on one bill from each jurisdiction
        logger.info("Starting verification step - testing analysis on sample bills")
        verification_success = verify_analysis_pipeline(db_session, api, target_jurisdictions, 
                                                     start_datetime, summary)
        
        if not verification_success:
            logger.error("Verification step failed. Seeding aborted.")
            return summary
            
        logger.info("Verification successful. Proceeding with full data seeding.")
        
        # Process jurisdictions and analyze bills
        process_jurisdictions_for_seeding(db_session, api, target_jurisdictions, 
                                        start_datetime, summary)
        analyze_new_bills(db_session, summary)
        
        logger.info(
            "Seeding completed. Added %s bills, analyzed %s bills, processed %s sessions",
            summary['bills_added'], summary['bills_analyzed'], len(summary['sessions_processed']))
        
    except Exception as e:  # Consider more specific exceptions if possible
        log_seeding_error("Error during seeding", e, summary)
    finally:
        summary["end_time"] = datetime.now()
            
    return summary


def process_jurisdictions_for_seeding(
    db_session: Session,
    api: LegiScanAPI,
    target_jurisdictions: List[str],
    start_datetime: datetime,
    summary: Dict[str, Any]
) -> None:
    """Process each target jurisdiction for historical seeding."""
    for state in target_jurisdictions:
        try:
            process_jurisdiction_for_seeding(db_session, api, state, start_datetime, summary)
        except Exception as e:  # Consider more specific exceptions if possible
            error_msg = f"{state}: {str(e)}"
            logger.error("Error processing state %s: %s", state, str(e), exc_info=True)
            summary["errors"].append(error_msg)
            

def process_jurisdiction_for_seeding(
    db_session: Session,
    api: LegiScanAPI,
    state: str,
    start_datetime: datetime,
    summary: Dict[str, Any]
) -> None:
    """Process a single jurisdiction for historical seeding."""
    # Get all sessions for the state
    all_sessions = api.get_session_list(state)
    if not all_sessions:
        warning_msg = f"No sessions found for state {state}"
        logger.warning(warning_msg)
        summary["errors"].append(warning_msg)
        return

    # Filter sessions that overlap with our target date range
    relevant_sessions = [
        session for session in all_sessions
        if (session.get("year_start", 0) >= start_datetime.year or
            session.get("year_end", 0) >= start_datetime.year)
    ]

    # Process each relevant session
    for session in relevant_sessions:
        if session_id := session.get("session_id"):
            process_session_for_seeding(
                db_session, api, state, session, session_id, start_datetime, summary
            )
        

def process_session_for_seeding(
    db_session: Session,
    api: LegiScanAPI,
    state: str,
    session: Dict[str, Any],
    session_id: int,
    start_datetime: datetime,
    summary: Dict[str, Any]
) -> None:
    """Process a single legislative session for historical seeding."""
    logger.info("Seeding historical data from %s session: %s", state, session.get('session_name'))
    
    # Initialize session summary
    session_summary = {
        "state": state,
        "session_id": session_id,
        "session_name": session.get("session_name"),
        "bills_found": 0,
        "bills_added": 0,
        "bills_analyzed": 0,
        "errors": []
    }
    
    try:
        # Get master list for this session
        master_list = api.get_master_list(session_id)
        if not master_list:
            error_msg = f"Failed to retrieve master list for session {session_id}"
            logger.error(error_msg)
            session_summary["errors"].append(error_msg)
            summary["sessions_processed"].append(session_summary)
            return
            
        # Process bills in this session
        process_bills_for_session(
            db_session, api, master_list, start_datetime, summary, session_summary
        )
        
    except Exception as e:  # Consider more specific exceptions if possible
        error_msg = f"Error processing session {session_id}: {str(e)}"
        logger.error("Error processing session %s: %s", session_id, str(e), exc_info=True)
        session_summary["errors"].append(error_msg)
        summary["errors"].append(error_msg)
    finally:
        # Always add session to processed list
        summary["sessions_processed"].append(session_summary)
        

def process_bills_for_session(
    db_session: Session,
    api: LegiScanAPI,
    master_list: Dict[str, Any],
    start_datetime: datetime,
    summary: Dict[str, Any],
    session_summary: Dict[str, Any]
) -> None:
    """Process bills from a legislative session's master list."""
    # Check if we've reached the maximum bills limit
    if summary.get("max_bills") and summary["bills_added"] >= summary["max_bills"]:
        logger.info(f"Reached maximum bill limit of {summary['max_bills']}. Stopping.")
        return
        
    for key, bill_info in master_list.items():
        # Stop if we've reached the maximum bills limit
        if summary.get("max_bills") and summary["bills_added"] >= summary["max_bills"]:
            logger.info(f"Reached maximum bill limit of {summary['max_bills']}. Stopping.")
            return
            
        if key == "0":  # Skip metadata
            continue
            
        bill_id = bill_info.get("bill_id")
        if not bill_id:
            continue
            
        # Check if bill already exists in our database
        existing = db_session.query(Legislation).filter(
            Legislation.external_id == str(bill_id),
            Legislation.data_source == "legiscan"
        ).first()
        
        session_summary["bills_found"] += 1
        
        if not existing:
            process_new_bill(
                db_session, api, bill_id, start_datetime, summary, session_summary
            )
            

def process_new_bill(
    db_session: Session,
    api: LegiScanAPI,
    bill_id: int,
    start_datetime: datetime,
    summary: Dict[str, Any],
    session_summary: Dict[str, Any]
) -> None:
    """Process a new bill that doesn't exist in the database yet."""
    try:
        # Get full bill data
        bill_data = api.get_bill(bill_id)
        if not bill_data:
            return
            
        # Skip bills before our start date
        if not is_bill_in_date_range(bill_data, start_datetime):
            return
            
        # Save bill to database
        if bill_obj := api.save_bill_to_db(bill_data, detect_relevance=True):
            summary["bills_added"] += 1
            session_summary["bills_added"] += 1
            
            # Process amendments if any
            if "amendments" in bill_data and bill_data["amendments"]:
                try:
                    # Track amendments (now using the imported function)
                    amendments_count = track_amendments(db_session, bill_obj, bill_data["amendments"])
                    logger.debug("Tracked %s amendments for bill %s", amendments_count, bill_id)
                except (ImportError, AttributeError) as e:
                    logger.warning("Could not import track_amendments for bill %s: %s", bill_id, e)
                except Exception as e:  # Consider more specific exceptions if possible
                    logger.warning("Error processing amendments for bill %s: %s", bill_id, e)
                
    except Exception as e:  # Consider more specific exceptions if possible
        error_msg = f"Error processing bill {bill_id}: {str(e)}"
        logger.error("Error processing bill %s: %s", bill_id, str(e), exc_info=True)
        session_summary["errors"].append(error_msg)
        summary["errors"].append(error_msg)
        

def is_bill_in_date_range(bill_data: Dict[str, Any], start_datetime: datetime) -> bool:
    """Check if a bill is within the target date range."""
    bill_date_str = bill_data.get("status_date", "")
    if not bill_date_str:
        return True  # If no date, include it to be safe
        
    with contextlib.suppress(ValueError):
        bill_date = datetime.strptime(bill_date_str, "%Y-%m-%d")
        if bill_date < start_datetime:
            return False  # Skip bills before our start date
            
    return True
    

def verify_analysis_pipeline(db_session: Session, api: LegiScanAPI, 
                           jurisdictions: List[str], start_datetime: datetime,
                           summary: Dict[str, Any]) -> bool:
    """
    Verify that the analysis pipeline works correctly by testing on one bill from each jurisdiction.
    
    Args:
        db_session: Database session
        api: LegiScanAPI instance
        jurisdictions: List of jurisdictions to verify
        start_datetime: Start date cutoff
        summary: Summary dictionary to update
        
    Returns:
        Boolean indicating whether verification was successful
    """
    # Initialize AI Analysis
    try:
        from app.ai_analysis import AIAnalysis
        analyzer = AIAnalysis(db_session=db_session)
        
        # Verify OpenAI API key
        if not os.environ.get("OPENAI_API_KEY"):
            error_msg = "OpenAI API key not found in environment variables"
            logger.error(error_msg)
            summary["verification_errors"].append(error_msg)
            return False
            
        logger.info(f"OpenAI API key found, using model: {analyzer.config.model_name}")
    except Exception as e:
        error_msg = f"Failed to initialize AIAnalysis: {str(e)}"
        logger.error(error_msg, exc_info=True)
        summary["verification_errors"].append(error_msg)
        return False
        
    # Test one bill from each jurisdiction
    verification_success = True
    analyzed_bills = []
    
    for jurisdiction in jurisdictions:
        try:
            logger.info(f"Testing analysis on a bill from {jurisdiction}")
            
            # Get sessions for this jurisdiction
            sessions = api.get_session_list(jurisdiction)
            if not sessions:
                error_msg = f"No sessions found for {jurisdiction}"
                logger.warning(error_msg)
                summary["verification_errors"].append(error_msg)
                verification_success = False
                continue
                
            # Get a recent session
            session = sessions[0]  # Most recent session
            session_id = session.get("session_id")
            if not session_id or not isinstance(session_id, int):
                error_msg = f"Invalid session ID for {jurisdiction}"
                logger.warning(error_msg)
                summary["verification_errors"].append(error_msg)
                verification_success = False
                continue
            
            # Get master list for this session
            master_list = api.get_master_list(session_id)
            if not master_list:
                error_msg = f"Failed to retrieve master list for {jurisdiction}"
                logger.warning(error_msg)
                summary["verification_errors"].append(error_msg)
                verification_success = False
                continue
                
            # Find a bill to test
            test_bill_id = None
            for key, bill_info in master_list.items():
                if key == "0":  # Skip metadata
                    continue
                    
                test_bill_id = bill_info.get("bill_id")
                if test_bill_id:
                    break
                    
            if not test_bill_id:
                error_msg = f"No bills found for {jurisdiction}"
                logger.warning(error_msg)
                summary["verification_errors"].append(error_msg)
                verification_success = False
                continue
                
            # Get the bill data
            bill_data = api.get_bill(test_bill_id)
            if not bill_data:
                error_msg = f"Failed to retrieve bill data for {test_bill_id}"
                logger.warning(error_msg)
                summary["verification_errors"].append(error_msg)
                verification_success = False
                continue
                
            # Save the bill to the database
            start_time = datetime.now()
            logger.info(f"Saving test bill {test_bill_id} to database")
            try:
                bill_obj = api.save_bill_to_db(bill_data, detect_relevance=True)
                if not bill_obj:
                    error_msg = f"Failed to save bill {test_bill_id} to database"
                    logger.error(error_msg)
                    summary["verification_errors"].append(error_msg)
                    verification_success = False
                    continue
            except Exception as e:
                error_msg = f"Error saving bill {test_bill_id} to database: {str(e)}"
                logger.error(error_msg, exc_info=True)
                summary["verification_errors"].append(error_msg)
                verification_success = False
                continue
            
            # Analyze the bill
            try:
                logger.info(f"Analyzing test bill {test_bill_id}")
                analysis = analyzer.analyze_legislation(bill_obj.id)
                
                # Check if analysis exists and has a valid ID
                if not analysis or not hasattr(analysis, 'id') or analysis.id is None:
                    error_msg = f"Analysis returned empty result for bill {test_bill_id}"
                    logger.error(error_msg)
                    summary["verification_errors"].append(error_msg)
                    verification_success = False
                    continue
                    
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                logger.info(f"Successfully analyzed bill {test_bill_id} in {duration:.2f} seconds")
                analyzed_bills.append({
                    "jurisdiction": jurisdiction,
                    "bill_id": test_bill_id,
                    "db_id": bill_obj.id,
                    "bill_number": bill_obj.bill_number,
                    "title": bill_obj.title[:100] + "..." if len(bill_obj.title) > 100 else bill_obj.title,
                    "analysis_id": analysis.id,
                    "duration_seconds": duration
                })
                
            except Exception as e:
                error_msg = f"Error analyzing bill {test_bill_id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                summary["verification_errors"].append(error_msg)
                
                # Special handling for OpenAI API errors
                from app.ai_analysis.errors import APIError, RateLimitError
                if isinstance(e, APIError) or "openai" in str(e).lower():
                    error_msg = f"OpenAI API error for bill {test_bill_id}: {str(e)}"
                    logger.error(error_msg)
                    summary["verification_errors"].append(error_msg)
                    verification_success = False
                    break  # Stop verifying if we hit API issues
                
                verification_success = False
        
        except Exception as e:
            error_msg = f"Error in verification process for {jurisdiction}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            summary["verification_errors"].append(error_msg)
            verification_success = False
    
    # Update summary with verification results
    summary["verification_success"] = verification_success
    summary["verification_bills"] = analyzed_bills
    
    # Log results
    if verification_success:
        logger.info("Verification successful - analysis pipeline is working")
    else:
        logger.error("Verification failed - analysis pipeline has issues")
        for error in summary["verification_errors"]:
            logger.error(f"Verification error: {error}")
    
    return verification_success


def analyze_new_bills(db_session: Session, summary: Dict[str, Any]) -> None:
    """Analyze all newly added bills without existing analysis."""
    if summary["bills_added"] == 0:
        return
        
    # Find bills without analysis
    no_analysis = db_session.query(Legislation.id).outerjoin(
        LegislationAnalysis,
        Legislation.id == LegislationAnalysis.legislation_id
    ).filter(
        LegislationAnalysis.legislation_id.is_(None)
    ).all()
    
    bills_to_analyze = [bill.id for bill in no_analysis]
    
    try:
        from app.ai_analysis import AIAnalysis
        analyzer = AIAnalysis(db_session=db_session)
    except Exception as e:
        error_msg = f"Failed to initialize AIAnalysis: {str(e)}"
        logger.error(error_msg, exc_info=True)
        summary["errors"].append(error_msg)
        return
    
    # Process each bill
    for leg_id in bills_to_analyze:
        try:
            analysis_start_time = datetime.now()
            logger.info(f"Analyzing legislation {leg_id}")
            
            # Analyze the bill
            analysis = analyzer.analyze_legislation(legislation_id=leg_id)
            
            analysis_duration = (datetime.now() - analysis_start_time).total_seconds()
            logger.info(f"Successfully analyzed legislation {leg_id} in {analysis_duration:.2f} seconds")
            
            summary["bills_analyzed"] += 1
            update_session_analysis_count(db_session, leg_id, summary)
            
        except Exception as e:
            # Handle OpenAI API errors specifically
            from app.ai_analysis.errors import APIError, RateLimitError
            if isinstance(e, APIError) or "openai" in str(e).lower():
                error_msg = f"OpenAI API error analyzing legislation {leg_id}: {str(e)}"
                logger.error(error_msg)
                summary["errors"].append(error_msg)
                
                # If we're rate limited, wait a bit before trying again
                if isinstance(e, RateLimitError) or "rate limit" in str(e).lower():
                    logger.warning("Rate limit hit, pausing for 60 seconds")
                    import time
                    time.sleep(60)
                    
                if "quota" in str(e).lower() or "billing" in str(e).lower():
                    error_msg = "OpenAI API quota exceeded or billing issue. Stopping analysis."
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)
                    break  # Stop analyzing if we're out of quota
            else:
                # General error handling
                error_msg = f"Error analyzing legislation {leg_id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                summary["errors"].append(error_msg)
                
                # Database errors might require stopping
                if "database" in str(e).lower() or "sql" in str(e).lower():
                    error_msg = f"Database error analyzing legislation {leg_id}. Stopping analysis."
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)
                    break


def update_session_analysis_count(
    db_session: Session,
    leg_id: int,
    summary: Dict[str, Any]
) -> None:
    """Update the session summary with analysis count for a bill."""
    try:
        # Get the bill from the database
        bill = db_session.query(Legislation).filter(Legislation.id == leg_id).first()
        if bill is None:
            return
            
        # Skip this step if we can't match the bill to a session
        if not hasattr(bill, 'raw_api_response'):
            return
            
        # Get state and session info - handle as safely as possible
        bill_state = None
        bill_session = None
        
        # The raw_api_response might be JSON data stored in a SQLAlchemy column
        # Access the raw data safely using safe_getattr
        raw_data = safe_getattr(bill, 'raw_api_response')
        
        # If it's a string, try to parse it as JSON
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except json.JSONDecodeError:
                return
        
        # Now try to access the state and session info
        if isinstance(raw_data, dict):
            bill_state = raw_data.get("state")
            session_info = raw_data.get("session")
            
            if isinstance(session_info, dict):
                bill_session = session_info.get("session_id")
        
        # If we couldn't get the state or session, we can't match it
        if not bill_state or not bill_session:
            return
            
        # Update the appropriate session summary
        for session_summary in summary["sessions_processed"]:
            if (session_summary["state"] == bill_state and
                session_summary["session_id"] == bill_session):
                session_summary["bills_analyzed"] += 1
                break
                
    except Exception as e:  # Consider more specific exceptions if possible
        logger.debug("Error updating session analysis count for bill %s: %s", leg_id, e) 