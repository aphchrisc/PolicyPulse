"""
Database operations for legislation data.

This module provides functions to save and update legislation data in the database.
"""

import base64
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.legiscan.models import (
    HAS_AMENDMENT_MODEL,
    HAS_PRIORITY_MODEL,
    convert_raw_api_response_to_dict,
    decode_bill_text,
    detect_content_type,
    parse_date,
    prepare_legislation_attributes,
    validate_bill_data,
)
from app.legiscan.utils import sanitize_text
from app.models import (
    DataSourceEnum,
    Legislation,
    LegislationSponsor,
    LegislationText,
    SyncError,
)

logger = logging.getLogger(__name__)


def save_bill_to_db(db_session: Session, bill_data: Dict[str, Any], detect_relevance: bool = True) -> Optional[Legislation]:
    """
    Creates or updates a bill record in the database based on LegiScan data.

    Args:
        db_session: SQLAlchemy database session
        bill_data: Bill information from LegiScan API
        detect_relevance: Whether to calculate relevance scores for public health

    Returns:
        Updated or created Legislation object, or None on failure
    """
    if not bill_data or not validate_bill_data(bill_data):
        logger.warning("Invalid bill data provided to save_bill_to_db")
        return None

    try:
        # Check if we are monitoring this state (US or TX)
        monitored_jurisdictions = ["US", "TX"]
        if bill_data.get("state") not in monitored_jurisdictions:
            logger.debug(f"Skipping bill from unmonitored state: {bill_data.get('state')}")
            return None

        # Start a transaction
        transaction = db_session.begin_nested()

        try:
            # Check if bill already exists
            external_id = str(bill_data["bill_id"])
            existing = db_session.query(Legislation).filter(
                and_(
                    Legislation.data_source == DataSourceEnum.legiscan,
                    Legislation.external_id == external_id
                )
            ).first()

            # Prepare attributes for database
            attrs = prepare_legislation_attributes(bill_data)

            if existing:
                # Update existing record
                for k, v in attrs.items():
                    setattr(existing, k, v)
                bill_obj = existing
            else:
                # Create new record
                bill_obj = Legislation(**attrs)
                db_session.add(bill_obj)

            # Flush to get bill_obj.id if it's a new record
            db_session.flush()

            # Save sponsors
            save_sponsors(db_session, bill_obj, bill_data.get("sponsors", []))

            # Save bill text if present
            save_legislation_texts(db_session, bill_obj, bill_data.get("texts", []))

            # Calculate relevance scores if requested
            if detect_relevance and HAS_PRIORITY_MODEL:
                from app.legiscan.relevance import RelevanceScorer
                scorer = RelevanceScorer()
                scorer.calculate_bill_relevance(bill_obj, db_session)

            # Process amendments if present
            if "amendments" in bill_data and bill_data["amendments"]:
                track_amendments(db_session, bill_obj, bill_data["amendments"])

            # Commit all changes
            transaction.commit()
            return bill_obj

        except Exception as e:
            transaction.rollback()
            raise e

    except SQLAlchemyError as e:
        logger.error(f"Database error in save_bill_to_db: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error in save_bill_to_db: {e}", exc_info=True)
        return None


def save_sponsors(db_session: Session, bill: Legislation, sponsors: List[Dict[str, Any]]) -> None:
    """
    Saves or updates bill sponsors.

    Args:
        db_session: SQLAlchemy database session
        bill: Legislation database object
        sponsors: List of sponsor dictionaries from LegiScan
    """
    # Clear old sponsors
    db_session.query(LegislationSponsor).filter(
        LegislationSponsor.legislation_id == bill.id
    ).delete()

    # Add new sponsors
    for sp in sponsors:
        sponsor_obj = LegislationSponsor(
            legislation_id=bill.id,
            sponsor_external_id=str(sp.get("people_id", "")),
            sponsor_name=sp.get("name", ""),
            sponsor_title=sp.get("role", ""),
            sponsor_state=sp.get("district", ""),
            sponsor_party=sp.get("party", ""),
            sponsor_type=str(sp.get("sponsor_type", "")),
        )
        db_session.add(sponsor_obj)
    db_session.flush()


def save_legislation_texts(
    db_session: Session, bill: Legislation, texts: List[Dict[str, Any]]
) -> None:
    """
    Saves or updates bill text versions.
    
    Args:
        db_session: SQLAlchemy database session
        bill: Legislation database object
        texts: List of text dictionaries from LegiScan
    """
    for text_info in texts:
        version_num = text_info.get("version", 1)
        
        # Check if this text version already exists
        existing = get_existing_text_version(db_session, bill.id, version_num)
        
        # Parse text date
        text_date_str = text_info.get("date", "")
        text_date = parse_date(text_date_str, datetime.now(timezone.utc))
        
        # Get bill state from raw_api_response (for logging only)
        bill_state = None
        if hasattr(bill, 'raw_api_response') and isinstance(bill.raw_api_response, dict):
            bill_state = bill.raw_api_response.get('state')
        
        # Get content if needed for important versions
        content, content_is_binary = get_text_content(
            text_info, bill.id, version_num, bill_state
        )
        
        # Prepare attributes for insert/update
        attrs = prepare_text_attributes(
            bill.id, version_num, text_info, text_date or datetime.now(timezone.utc), 
            content, content_is_binary
        )
        
        # Update or insert
        update_or_insert_text(db_session, existing, attrs)
    
    db_session.flush()


def get_existing_text_version(
    db_session: Session, legislation_id: Union[int, Any], version_num: int
) -> Optional[LegislationText]:
    """
    Get existing text version if it exists.
    
    Args:
        db_session: SQLAlchemy database session
        legislation_id: ID of the legislation
        version_num: Version number of the text
        
    Returns:
        LegislationText object or None if not found
    """
    return db_session.query(LegislationText).filter_by(
        legislation_id=legislation_id,
        version_num=version_num
    ).first()


def get_text_content(
    text_info: Dict[str, Any], 
    bill_id: Union[int, Any], 
    version_num: int, 
    bill_state: Optional[str] = None
) -> Tuple[Optional[Union[str, bytes]], bool]:
    """
    Get text content for bill versions, prioritizing state_link.
    
    Args:
        text_info: Text information dictionary from LegiScan
        bill_id: ID of the bill
        version_num: Version number of the text
        bill_state: State code of the bill (for logging)
        
    Returns:
        Tuple of (text_content, is_binary_flag)
    """
    doc_id = text_info.get("doc_id")
    state_link = text_info.get("state_link")
    mime_id = text_info.get("mime_id")
    content = None
    content_is_binary = False
    
    # Always try state_link first if available
    if state_link:
        try:
            logger.info(f"Fetching bill content from state_link: {state_link}")
            response = requests.get(state_link, timeout=30)
            response.raise_for_status()
            
            # Determine if content is binary based on mime_id
            if mime_id == 2:  # PDF
                content = response.content  # Keep as binary
                content_is_binary = True
                logger.info(
                    f"Successfully fetched PDF content from state_link for bill {bill_id}"
                )
            else:  # HTML or text
                content = response.text  # Store as text
                content_is_binary = False
                logger.info(
                    f"Successfully fetched HTML/text content from state_link for bill {bill_id}"
                )
            
            return content, content_is_binary
        except Exception as e:
            logger.error(f"Failed to fetch content from state_link for bill {bill_id}: {e}")
            # Fall back to other methods
    
    # Fallback to direct API content if state_link fails or is not available
    if doc_id and (version_num == 1 or text_info.get("type") in ("Enrolled", "Chaptered")):
        if doc_base64 := text_info.get("doc"):
            try:
                content, content_is_binary = decode_bill_text(doc_base64)
                
                # Ensure content is in the correct format based on binary flag
                if content_is_binary and not isinstance(content, bytes):
                    content = str(content).encode('utf-8', errors='replace')
                elif not content_is_binary and isinstance(content, bytes):
                    content = content.decode('utf-8', errors='replace')
            except Exception as e:
                logger.error(f"Failed to decode base64 content for bill {bill_id}: {e}")
    
    # Final validation to ensure content type matches binary flag
    if content is not None:
        if content_is_binary and not isinstance(content, bytes):
            content = str(content).encode('utf-8', errors='replace')
        elif not content_is_binary and isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
            
    return content, content_is_binary


def prepare_text_attributes(
    legislation_id: Union[int, Any],
    version_num: int,
    text_info: Dict[str, Any],
    text_date: datetime,
    content: Optional[Union[str, bytes]],
    content_is_binary: bool
) -> Dict[str, Any]:
    """
    Prepare attributes for text record insert/update.
    
    Args:
        legislation_id: ID of the legislation
        version_num: Version number of the text
        text_info: Text information dictionary from LegiScan
        text_date: Parsed date of the text
        content: Text content (string or bytes)
        content_is_binary: Whether the content is binary
        
    Returns:
        Dictionary of attributes ready for database insertion
    """
    attrs = {
        "legislation_id": legislation_id,
        "version_num": version_num,
        "text_type": text_info.get("type", ""),
        "text_date": text_date,
        "text_hash": text_info.get("text_hash"),
        "is_binary": content_is_binary,
    }
    
    # Add content if available
    if content is not None:
        try:
            # Double-check content type matches is_binary flag
            if content_is_binary and isinstance(content, str):
                logger.warning(
                    f"Content is marked as binary but is a string for legislation {legislation_id}. "
                    "Converting to bytes."
                )
                content = content.encode('utf-8', errors='replace')
            elif not content_is_binary and isinstance(content, bytes):
                logger.warning(
                    f"Content is marked as text but is bytes for legislation {legislation_id}. "
                    "Converting to string."
                )
                content = content.decode('utf-8', errors='replace')
            
            # Process content based on binary flag
            if content_is_binary:
                # Ensure binary content is stored as bytes
                if not isinstance(content, bytes):
                    binary_content = (
                        content.encode('utf-8', errors='replace') 
                        if isinstance(content, str) 
                        else str(content).encode('utf-8', errors='replace')
                    )
                else:
                    binary_content = content
                
                # Set binary-specific attributes
                attrs["content_type"] = detect_content_type(binary_content)
                attrs["file_size"] = len(binary_content)
                attrs["text_content"] = binary_content
                attrs["text_metadata"] = {
                    'is_binary': True,
                    'content_type': attrs["content_type"],
                    'size_bytes': attrs["file_size"]
                }
            else:
                # For text content, ensure it's a string
                text_content = (
                    content.decode('utf-8', errors='replace') 
                    if isinstance(content, bytes) 
                    else str(content)
                )
                
                # Sanitize text content
                text_content = sanitize_text(text_content)
                
                # Set text-specific attributes
                attrs["content_type"] = "text/plain"
                attrs["file_size"] = len(text_content.encode('utf-8'))
                attrs["text_content"] = text_content
                attrs["text_metadata"] = {
                    'is_binary': False,
                    'encoding': 'utf-8',
                    'size_bytes': attrs["file_size"]
                }
        except Exception as e:
            logger.error(f"Error preparing text attributes: {e}")
            # Provide fallbacks based on content type
            if content_is_binary or isinstance(content, bytes):
                attrs["is_binary"] = True
                attrs["content_type"] = "application/octet-stream"
                attrs["file_size"] = len(content) if isinstance(content, bytes) else 0
                attrs["text_content"] = content if isinstance(content, bytes) else b""
                attrs["text_metadata"] = {
                    'is_binary': True,
                    'content_type': "application/octet-stream",
                    'size_bytes': attrs["file_size"],
                    'error': str(e)
                }
            else:
                attrs["is_binary"] = False
                attrs["content_type"] = "text/plain"
                attrs["text_content"] = str(content) if content is not None else ""
                attrs["file_size"] = len(attrs["text_content"].encode('utf-8'))
                attrs["text_metadata"] = {
                    'is_binary': False,
                    'encoding': 'utf-8',
                    'size_bytes': attrs["file_size"],
                    'error': str(e)
                }
    
    return attrs


def update_or_insert_text(
    db_session: Session, existing: Optional[LegislationText], attrs: Dict[str, Any]
) -> None:
    """
    Update existing text record or insert new one.
    
    Args:
        db_session: SQLAlchemy database session
        existing: Existing LegislationText object or None
        attrs: Dictionary of attributes for the text
    """
    # Make a copy of attrs to avoid modifying the original
    safe_attrs = attrs.copy()
    
    # Handle binary content properly
    if 'text_content' in safe_attrs:
        # Respect the content type based on is_binary flag
        is_binary = safe_attrs.get('is_binary', False)
        
        # Handle the content separately to ensure proper type handling
        text_content = safe_attrs.pop('text_content')
        
        # Ensure content is in the correct format based on is_binary flag
        if is_binary:
            # For binary content, ensure it's bytes
            if not isinstance(text_content, bytes):
                text_content = (
                    text_content.encode('utf-8', errors='replace') 
                    if isinstance(text_content, str) 
                    else str(text_content).encode('utf-8', errors='replace')
                )
        else:
            # For text content, ensure it's a string
            if isinstance(text_content, bytes):
                text_content = text_content.decode('utf-8', errors='replace')
            elif not isinstance(text_content, str):
                text_content = str(text_content)
            
            # Sanitize text content
            text_content = sanitize_text(text_content)
        
        # Create or update the record with the text content handled separately
        if existing:
            # Update existing record
            for k, v in safe_attrs.items():
                setattr(existing, k, v)
            # Set the text content separately
            existing.set_content(text_content)
        else:
            # Create new record without text_content first
            new_text = LegislationText(**safe_attrs)
            # Then set the content properly
            new_text.set_content(text_content)
            db_session.add(new_text)
        
        # Skip the rest of the method since we've handled this case
        return
    
    # If we get here, there's no text_content to handle
    if existing:
        for k, v in safe_attrs.items():
            setattr(existing, k, v)
    else:
        new_text = LegislationText(**safe_attrs)
        db_session.add(new_text)


def track_amendments(
    db_session: Session, bill: Legislation, amendments: List[Dict[str, Any]]
) -> int:
    """
    Track amendments back to their parent bills.

    Args:
        db_session: SQLAlchemy database session
        bill: Parent legislation object
        amendments: List of amendment data from LegiScan

    Returns:
        Number of amendments processed
    """
    processed_count = 0

    # Start a nested transaction for amendment processing
    with db_session.begin_nested():
        # Process each amendment
        for amend_data in amendments:
            amendment_id = amend_data.get("amendment_id")
            if not amendment_id:
                continue

            # Process amendment based on model availability
            if HAS_AMENDMENT_MODEL:
                process_amendment_with_model(db_session, bill, amend_data)
                processed_count += 1
            else:
                store_amendment_in_raw_response(bill, amend_data)
                processed_count += 1

    return processed_count


def process_amendment_with_model(
    db_session: Session, bill: Legislation, amend_data: Dict[str, Any]
) -> None:
    """
    Process an amendment using the Amendment model.
    
    Args:
        db_session: SQLAlchemy database session
        bill: Parent legislation object
        amend_data: Amendment data from LegiScan
    """
    # Import models within the function to ensure they exist
    from app.models import Amendment, AmendmentStatusEnum
    
    amendment_id = amend_data.get("amendment_id")
    
    # Check if amendment already exists
    existing = db_session.query(Amendment).filter_by(
        amendment_id=str(amendment_id),
        legislation_id=bill.id
    ).first()
    
    # Parse amendment date
    amend_date_str = amend_data.get("date", "")
    amend_date = parse_date(amend_date_str)
    
    # Convert adopted flag to boolean and determine status
    is_adopted = bool(amend_data.get("adopted", 0))
    status_value = AmendmentStatusEnum.adopted if is_adopted else AmendmentStatusEnum.proposed
    
    # Prepare common attributes
    amendment_attrs = {
        'adopted': is_adopted,
        'status': status_value,
        'amendment_date': amend_date,
        'title': amend_data.get("title", ""),
        'description': amend_data.get("description", ""),
        'amendment_hash': amend_data.get("amendment_hash", ""),
    }
    
    if existing:
        # Update existing record using setattr to avoid type checking issues
        for key, value in amendment_attrs.items():
            setattr(existing, key, value)
    else:
        # Create new record
        new_amendment = Amendment(
            amendment_id=str(amendment_id),
            legislation_id=bill.id,
            amendment_url=amend_data.get("state_link"),
            **amendment_attrs
        )
        db_session.add(new_amendment)


def store_amendment_in_raw_response(bill: Legislation, amend_data: Dict[str, Any]) -> None:
    """
    Store amendment data in the bill's raw_api_response field when Amendment model is unavailable.
    
    Args:
        bill: Parent legislation object
        amend_data: Amendment data from LegiScan
    """
    try:
        # Get the current raw_api_response as a dictionary
        raw_data = convert_raw_api_response_to_dict(bill.raw_api_response)
        
        # Ensure amendments list exists
        if "amendments" not in raw_data:
            raw_data["amendments"] = []
        elif not isinstance(raw_data.get("amendments"), list):
            raw_data["amendments"] = []
        
        # Check if amendment already exists
        amendment_id = amend_data.get("amendment_id")
        amendments_list = raw_data["amendments"]
        existing_ids = [
            a.get("amendment_id")
            for a in amendments_list
            if isinstance(a, dict) and "amendment_id" in a
        ]
        
        # Add the new amendment if not already tracked
        if amendment_id not in existing_ids:
            amendments_list.append(amend_data)
            
            # Update the raw_api_response
            setattr(bill, "raw_api_response", raw_data)
            
    except Exception as e:
        logger.warning(f"Error storing amendment in raw_api_response: {e}")


def record_sync_error(
    db_session: Session, 
    sync_id: int, 
    error_type: str, 
    error_message: str, 
    stack_trace: Optional[str] = None
) -> None:
    """
    Record an error that occurred during sync operations.
    
    Args:
        db_session: SQLAlchemy database session
        sync_id: ID of the sync operation
        error_type: Type of error (e.g., "bill_processing", "api_error")
        error_message: Error message
        stack_trace: Optional stack trace for debugging
    """
    try:
        sync_error = SyncError(
            sync_id=sync_id,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace
        )
        db_session.add(sync_error)
        db_session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Failed to record sync error: {e}")
        db_session.rollback() 