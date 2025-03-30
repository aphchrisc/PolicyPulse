"""
Data conversion utilities for mapping between LegiScan API responses and database models.

This module handles the translation between API data structures and SQLAlchemy models.
"""

import base64
import logging
import contextlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, Union, List

from app.models import (
    Legislation,
    LegislationText,
    LegislationSponsor,
    DataSourceEnum, 
    GovtTypeEnum,
    BillStatusEnum
)
from app.legiscan.utils import sanitize_text

# Check if optional models are available
try:
    from app.models import LegislationPriority
    HAS_PRIORITY_MODEL = True
except ImportError:
    HAS_PRIORITY_MODEL = False

try:
    from app.models import Amendment, AmendmentStatusEnum
    HAS_AMENDMENT_MODEL = True
except ImportError:
    HAS_AMENDMENT_MODEL = False

logger = logging.getLogger(__name__)


def map_bill_status(status_val) -> str:
    """
    Maps LegiScan numeric status to BillStatusEnum.

    Args:
        status_val: LegiScan status value

    Returns:
        Corresponding BillStatusEnum value
    """
    if not status_val:
        return BillStatusEnum.new.value

    mapping = {
        "1": BillStatusEnum.introduced.value,
        "2": BillStatusEnum.updated.value,
        "3": BillStatusEnum.updated.value,
        "4": BillStatusEnum.passed.value,
        "5": BillStatusEnum.vetoed.value,
        "6": BillStatusEnum.defeated.value,
        "7": BillStatusEnum.enacted.value
    }
    status_str = str(status_val)
    return mapping.get(status_str, BillStatusEnum.updated.value)


def parse_date(date_str: str, default=None) -> Optional[datetime]:
    """
    Parse a date string in ISO format to a datetime object.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        default: Default value to return if parsing fails
        
    Returns:
        Parsed datetime or default value if parsing fails
    """
    if not date_str:
        return default
        
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"Invalid date format: {date_str}")
        return default


def decode_bill_text(encoded_text: Optional[str]) -> Tuple[Optional[Union[str, bytes]], bool]:
    """
    Decode base64-encoded bill text from the LegiScan API.
    
    Args:
        encoded_text: Base64-encoded text content
        
    Returns:
        Tuple of (decoded content, is_binary_flag)
    """
    if not encoded_text:
        return None, False
        
    try:
        decoded_content = base64.b64decode(encoded_text)
        
        # Common binary file signatures
        binary_signatures = [
            b'%PDF-',  # PDF
            b'\xD0\xCF\x11\xE0',  # MS Office
            b'PK\x03\x04'  # ZIP (often used for DOCX, XLSX)
        ]
        
        # Check if content matches any binary signature
        if any(decoded_content.startswith(sig) for sig in binary_signatures):
            return decoded_content, True
            
        # Try to decode as UTF-8 text
        try:
            text_content = decoded_content.decode("utf-8", errors="ignore")
            return text_content, False
        except UnicodeDecodeError:
            # If we can't decode as text, treat as binary
            return decoded_content, True
            
    except Exception as e:
        logger.error(f"Failed to decode base64 content: {e}")
        return None, False


def detect_content_type(data: bytes) -> str:
    """
    Detect content type from binary data.
    
    Args:
        data: Binary data to analyze
        
    Returns:
        MIME type string
    """
    if data.startswith(b'%PDF-'):
        return 'application/pdf'
    elif data.startswith(b'\xD0\xCF\x11\xE0'):
        return 'application/msword'
    elif data.startswith(b'PK\x03\x04'):
        return 'application/zip'
    return 'application/octet-stream'


def convert_raw_api_response_to_dict(api_response: Any) -> Dict[str, Any]:
    """
    Convert various types of API response data to a consistent dictionary format.
    
    Args:
        api_response: API response in various possible formats
        
    Returns:
        Normalized dictionary representation
    """
    # Return empty dict if raw_api_response is None
    if api_response is None:
        return {}

    # Try each conversion strategy in order of preference
    for strategy in [
        _convert_from_dict,
        _convert_from_json_string,
        _convert_from_copyable_object,
        _convert_from_dict_attribute,
        _convert_from_asdict_method,
        _convert_from_string_representation
    ]:
        if result := strategy(api_response):
            return result

    # If all strategies fail, log warning and return empty dict
    logger.warning(f"Could not convert raw_api_response of type {type(api_response)} to dictionary")
    return {}


def _normalize_dict_keys(data: Dict) -> Dict[str, Any]:
    """Convert all dictionary keys to strings."""
    return {str(k): v for k, v in data.items()}


def _convert_from_dict(data: Any) -> Optional[Dict[str, Any]]:
    """Convert data that is already a dictionary."""
    return _normalize_dict_keys(data) if isinstance(data, dict) else None


def _convert_from_json_string(data: Any) -> Optional[Dict[str, Any]]:
    """Convert data from a JSON string."""
    import json

    if not isinstance(data, str):
        return None

    with contextlib.suppress(json.JSONDecodeError):
        parsed = json.loads(data)
        if isinstance(parsed, dict):
            return _normalize_dict_keys(parsed)
    return None


def _convert_from_copyable_object(data: Any) -> Optional[Dict[str, Any]]:
    """Convert data from an object with a copy method."""
    if not hasattr(data, 'copy'):
        return None
        
    try:
        copied_data = data.copy()
        if isinstance(copied_data, dict):
            return _normalize_dict_keys(copied_data)
    except Exception:
        logger.debug("Failed to copy object data", exc_info=True)
    return None


def _convert_from_dict_attribute(data: Any) -> Optional[Dict[str, Any]]:
    """Convert data from an object with a __dict__ attribute."""
    if not hasattr(data, '__dict__'):
        return None
        
    try:
        obj_dict = data.__dict__
        if isinstance(obj_dict, dict):
            # Filter out private attributes (starting with _)
            filtered_dict = {k: v for k, v in obj_dict.items() if not k.startswith('_')}
            return _normalize_dict_keys(filtered_dict)
    except Exception:
        logger.debug("Failed to access __dict__ attribute", exc_info=True)
    return None


def _convert_from_asdict_method(data: Any) -> Optional[Dict[str, Any]]:
    """Convert data from an object with an _asdict method."""
    if not hasattr(data, '_asdict'):
        return None
        
    try:
        dict_data = data._asdict()
        if isinstance(dict_data, dict):
            return _normalize_dict_keys(dict_data)
    except Exception:
        logger.debug("Failed to call _asdict method", exc_info=True)
    return None


def _convert_from_string_representation(data: Any) -> Optional[Dict[str, Any]]:
    """Convert data from a string representation that might be JSON."""
    import json

    with contextlib.suppress(Exception):
        # Get string representation
        raw_str = str(data)

        # Check if it looks like JSON
        if raw_str.startswith('{') and raw_str.endswith('}'):
            with contextlib.suppress(json.JSONDecodeError):
                parsed = json.loads(raw_str)
                if isinstance(parsed, dict):
                    return _normalize_dict_keys(parsed)
    return None


def validate_bill_data(bill_data: Dict[str, Any]) -> bool:
    """
    Validates that essential fields are present in the bill data.

    Args:
        bill_data: Bill data from LegiScan API

    Returns:
        True if all required fields are present, False otherwise
    """
    required_fields = ["bill_id", "state", "bill_number", "title"]
    return all(field in bill_data for field in required_fields)


def prepare_legislation_attributes(bill_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepares database attributes for a Legislation object from API data.
    
    Args:
        bill_data: Bill data from LegiScan API
        
    Returns:
        Dictionary of attributes ready for database insertion
    """
    # Convert LegiScan's "state" to GovtTypeEnum
    govt_type = GovtTypeEnum.federal if bill_data["state"] == "US" else GovtTypeEnum.state
    external_id = str(bill_data["bill_id"])
    
    # Map the status numeric ID to BillStatusEnum
    new_status = map_bill_status(bill_data.get("status"))
    
    # Build the upsert attributes with proper enum instance
    attrs = {
        "external_id": external_id,
        "data_source": DataSourceEnum.legiscan,
        "govt_type": govt_type,
        "govt_source": sanitize_text(bill_data.get("session", {}).get("session_name", "Unknown Session")),
        "bill_number": sanitize_text(bill_data.get("bill_number", "")),
        "bill_type": bill_data.get("bill_type"),
        "title": sanitize_text(bill_data.get("title", "")),
        "description": sanitize_text(bill_data.get("description", "")),
        "bill_status": new_status,
        "url": bill_data.get("url"),
        "state_link": bill_data.get("state_link"),
        "change_hash": bill_data.get("change_hash"),
        "raw_api_response": None,  # Don't store raw LegiScan response
        "last_api_check": datetime.now(timezone.utc),
    }

    # Parse dates
    if introduced_str := bill_data.get("introduced_date", ""):
        attrs["bill_introduced_date"] = parse_date(introduced_str)

    if status_str := bill_data.get("status_date", ""):
        attrs["bill_status_date"] = parse_date(status_str)

    if last_action_str := bill_data.get("last_action_date", ""):
        attrs["bill_last_action_date"] = parse_date(last_action_str)

    return attrs 