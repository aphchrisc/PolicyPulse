"""
scheduler/amendments.py

Functions for tracking and processing bill amendments.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models import Legislation
from app.scheduler.errors import DataSyncError
from app.scheduler.utils import parse_date, format_error_message, safe_getattr

logger = logging.getLogger(__name__)

# Define placeholder types for type hints if models aren't available
class AmendmentBase:
    """Base placeholder class for Amendment."""
    amendment_id: str = ""
    legislation_id: int = 0
    adopted: bool = False
    status: str = ""
    amendment_date: Optional[datetime] = None
    title: str = ""
    description: str = ""
    amendment_hash: str = ""
    amendment_url: str = ""

class AmendmentStatusEnumBase:
    """Placeholder enum for Amendment status."""
    adopted: str = "adopted"
    proposed: str = "proposed"

# Initialize with placeholders
Amendment = AmendmentBase
AmendmentStatusEnum = AmendmentStatusEnumBase
HAS_AMENDMENT_MODEL = False

# Try to import the real models
try:
    # Try to import from app.models
    from app.models import Amendment as RealAmendment
    from app.models import AmendmentStatusEnum as RealAmendmentStatusEnum
    
    # Use the real classes if available
    Amendment = RealAmendment
    AmendmentStatusEnum = RealAmendmentStatusEnum
    HAS_AMENDMENT_MODEL = True
    logger.debug("Successfully imported Amendment models")
except (ImportError, AttributeError) as e:
    # Handle case where Amendment models are not available
    logger.warning("Amendment models not available: %s", e)
    HAS_AMENDMENT_MODEL = False


def track_amendments(db_session: Session, bill: Legislation,
                    amendments: List[Dict[str, Any]]) -> int:
    """
    Track amendments back to their parent bills. This helps maintain relationships
    between bills and their amendments.

    Args:
        db_session: Database session
        bill: Parent legislation object
        amendments: List of amendment data from LegiScan

    Returns:
        Number of amendments processed

    Raises:
        DataSyncError: If unable to process amendments
    """
    try:
        processed_count = 0

        # Process each amendment
        for amend_data in amendments:
            amendment_id = amend_data.get("amendment_id")
            if not amendment_id:
                continue

            # Process the amendment based on available models
            if HAS_AMENDMENT_MODEL:
                try:
                    process_with_amendment_model(db_session, bill, amend_data, amendment_id)
                except Exception as e:
                    logger.warning("Error processing amendment with model: %s", e)
                    # Fall back to processing without model if there's an error
                    process_without_amendment_model(bill, amend_data, amendment_id)
            else:
                process_without_amendment_model(bill, amend_data, amendment_id)

            processed_count += 1

        # Commit changes
        db_session.commit()
        return processed_count

    except SQLAlchemyError as e:
        handle_amendment_error(db_session, 'Database error while tracking amendments: ', e)
        return 0  # Return 0 to indicate no amendments were processed
    except Exception as e:
        handle_amendment_error(db_session, 'Error tracking amendments: ', e)
        return 0  # Return 0 to indicate no amendments were processed


def process_with_amendment_model(db_session: Session, bill: Legislation,
                               amend_data: Dict[str, Any], amendment_id: str) -> None:
    """
    Process an amendment using the dedicated Amendment model.
    
    Args:
        db_session: Database session
        bill: Parent legislation object
        amend_data: Amendment data from LegiScan
        amendment_id: ID of the amendment
    """
    if not HAS_AMENDMENT_MODEL:
        logger.warning("Amendment model not available but process_with_amendment_model was called")
        return

    # Get the integer value of bill.id - convert to string first to avoid SQLAlchemy Column issues
    try:
        bill_id_str = str(bill.id)
        bill_id = int(bill_id_str)
    except (AttributeError, ValueError) as e:
        logger.warning("Could not get bill ID: %s", e)
        return

    try:
        # Check if this amendment already exists
        existing = (
            db_session.query(Amendment)
            .filter_by(amendment_id=amendment_id, legislation_id=bill_id)
            .first()
        )

        # Parse amendment date
        amend_date = parse_date(amend_data.get("date"))

        # Convert adopted flag to boolean
        is_adopted = bool(amend_data.get("adopted", 0))

        # Determine status enum value with fallback
        status_value = get_status_value(is_adopted)

        if existing:
            # Update existing record
            update_existing_amendment(existing, is_adopted, status_value, amend_date, amend_data)
        else:
            # Create new record
            create_new_amendment(db_session, bill_id, amendment_id, is_adopted, 
                            status_value, amend_date, amend_data)
    except Exception as e:
        logger.warning("Error in process_with_amendment_model: %s", e)
        # Let the exception propagate so we can try the fallback method


def get_status_value(is_adopted: bool) -> Any:
    """Get the appropriate status value with fallbacks."""
    try:
        if hasattr(AmendmentStatusEnum, 'adopted') and hasattr(AmendmentStatusEnum, 'proposed'):
            return AmendmentStatusEnum.adopted if is_adopted else AmendmentStatusEnum.proposed
        else:
            # Fallback for when enum doesn't have these attributes
            return 'adopted' if is_adopted else 'proposed'
    except Exception as e:
        logger.warning("Error determining amendment status: %s", e)
        return 'adopted' if is_adopted else 'proposed'


def update_existing_amendment(existing: Any, is_adopted: bool,
                            status_value: Any, amend_date: Optional[datetime],
                            amend_data: Dict[str, Any]) -> None:
    """
    Update an existing amendment record.
    
    Args:
        existing: Existing Amendment object
        is_adopted: Whether the amendment was adopted
        status_value: Status enum value
        amend_date: Parsed amendment date
        amend_data: Raw amendment data
    """
    # Update existing record using dict update approach
    update_data = {
        "adopted": is_adopted,
        "status": status_value,
        "amendment_date": amend_date,
        "title": amend_data.get("title", ""),
        "description": amend_data.get("description", ""),
        "amendment_hash": amend_data.get("amendment_hash", "")
    }

    # Use orm.attributes to update the object
    for key, value in update_data.items():
        try:
            if hasattr(existing, key):
                setattr(existing, key, value)
        except Exception as e:
            logger.warning("Error setting %s on amendment: %s", key, e)


def create_new_amendment(db_session: Session, legislation_id: int,
                       amendment_id: str, is_adopted: bool, status_value: Any,
                       amend_date: Optional[datetime], amend_data: Dict[str, Any]) -> None:
    """
    Create a new amendment record.
    
    Args:
        db_session: Database session
        legislation_id: ID of the parent legislation
        amendment_id: ID of the amendment
        is_adopted: Whether the amendment was adopted
        status_value: Status enum value
        amend_date: Parsed amendment date
        amend_data: Raw amendment data
    """
    if not HAS_AMENDMENT_MODEL:
        logger.warning("Amendment model not available but create_new_amendment was called")
        return

    # Create new record using kwargs to avoid linter errors about parameters
    amendment_data = {
        "amendment_id": amendment_id,
        "legislation_id": legislation_id,
        "adopted": is_adopted,
        "status": status_value,
        "amendment_date": amend_date,
        "title": amend_data.get("title", ""),
        "description": amend_data.get("description", ""),
        "amendment_hash": amend_data.get("amendment_hash", ""),
        "amendment_url": amend_data.get("state_link", ""),
    }
    
    # Filter out any keys that might not be accepted by the Amendment constructor
    try:
        # Get attributes that exist on the Amendment class
        valid_keys = []
        for key in amendment_data:
            if hasattr(Amendment, key):
                valid_keys.append(key)
        
        # Create a new dict with only valid keys
        valid_amendment_data = {k: amendment_data[k] for k in valid_keys}
        
        # Create and add the new amendment
        new_amendment = Amendment(**valid_amendment_data)
        db_session.add(new_amendment)
    except Exception as e:
        logger.warning("Error creating amendment: %s", e)


def process_without_amendment_model(bill: Legislation,
                                  amend_data: Dict[str, Any],
                                  amendment_id: Any) -> None:
    """
    Process an amendment without using a dedicated Amendment model.
    Store it in the bill's raw_api_response field.
    
    Args:
        bill: Parent legislation object
        amend_data: Amendment data from LegiScan
        amendment_id: ID of the amendment
    """
    raw_data = {}
    
    # Safely handle SQLAlchemy Column type for raw_api_response
    raw_api_response = safe_getattr(bill, 'raw_api_response')
    
    # If it's None or empty, initialize as empty dict
    if raw_api_response is None:
        raw_data = {}
    else:
        # Convert to dict if it's a string or already a dict
        if isinstance(raw_api_response, str):
            try:
                raw_data = json.loads(raw_api_response)
            except json.JSONDecodeError:
                raw_data = {}
        else:
            raw_data = raw_api_response
    
    # Make sure raw_data is a dictionary
    if not isinstance(raw_data, dict):
        raw_data = {}

    # Initialize amendments list if it doesn't exist
    if "amendments" not in raw_data:
        raw_data["amendments"] = []

    # Add amendment if not already tracked
    existing_ids = {a.get("amendment_id") for a in raw_data["amendments"] if a.get("amendment_id")}
    if amendment_id not in existing_ids:
        raw_data["amendments"].append(amend_data)
        
        # Use setattr to avoid type checking issues with Column assignment
        try:
            setattr(bill, "raw_api_response", raw_data)
        except Exception as e:
            logger.warning("Error setting raw_api_response: %s", e)


def _get_bill_id_safely(bill_obj: Legislation) -> Optional[int]:
    """
    Get the bill ID safely, handling potential SQLAlchemy Column issues.
    
    Args:
        bill_obj: Legislation object
        
    Returns:
        Bill ID as int, or None if any error occurs
    """
    bill_id = safe_getattr(bill_obj, 'id')
    if bill_id is None:
        return None
        
    try:
        # Convert to string and then to int to avoid SQLAlchemy Column issues
        return int(str(bill_id))
    except (ValueError, TypeError) as e:
        logger.warning("Error converting bill ID to int: %s", e)
        return None


def handle_amendment_error(db_session: Session, prefix: str, exception: Exception) -> None:
    """
    Handle errors during amendment tracking.
    
    Args:
        db_session: Database session
        prefix: Error message prefix
        exception: The exception that occurred
        
    Raises:
        DataSyncError: Always raised with formatted error message
    """
    try:
        db_session.rollback()
    except Exception as e:
        logger.warning("Error rolling back session: %s", e)
        
    error_msg = format_error_message(prefix, exception)
    raise DataSyncError(error_msg) from exception 
