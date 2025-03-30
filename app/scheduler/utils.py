"""
scheduler/utils.py

Utility functions for scheduler and sync operations.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def format_error_message(prefix: str, exception: Exception) -> str:
    """
    Format an error message with a prefix and exception details.
    
    Args:
        prefix: Error message prefix
        exception: The exception that occurred
        
    Returns:
        Formatted error message
    """
    result = f"{prefix}{str(exception)}"
    logger.error(result, exc_info=True)
    return result


def parse_date(date_str: Optional[str], default_format: str = "%Y-%m-%d") -> Optional[datetime]:
    """
    Parse a date string into a datetime object.
    
    Args:
        date_str: Date string to parse
        default_format: Format string for datetime.strptime
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None
        
    try:
        return datetime.strptime(date_str, default_format)
    except ValueError:
        logger.warning(f"Invalid date format: {date_str}")
        return None


def initialize_sync_summary() -> Dict[str, Any]:
    """
    Initialize a summary dictionary for sync operations.
    
    Returns:
        Dictionary with initialized summary fields
    """
    return {
        "new_bills": 0,
        "bills_updated": 0,
        "bills_analyzed": 0,
        "errors": [],
        "amendments_tracked": 0,
        "start_time": datetime.now(),
        "end_time": None
    }


def safe_getattr(obj: Any, attr_name: str, default: Any = None) -> Any:
    """
    Safely get an attribute from an object, returning a default if not found.
    Particularly useful for SQLAlchemy Column attribute access.
    
    Args:
        obj: Object to get attribute from
        attr_name: Name of attribute to get
        default: Default value if attribute not found or error
        
    Returns:
        Attribute value or default
    """
    try:
        return getattr(obj, attr_name, default)
    except Exception as e:
        logger.debug(f"Error accessing attribute {attr_name}: {e}")
        return default 