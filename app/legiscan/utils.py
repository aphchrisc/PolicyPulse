"""
Utility functions for the LegiScan API integration.
"""

import re
import logging
from typing import Union, Any

logger = logging.getLogger(__name__)


def sanitize_text(text: Union[str, bytes, Any]) -> str:
    """
    Sanitize the input text by removing NUL characters and other control characters
    that might cause database issues.
    
    Args:
        text: The text to sanitize (can be string, bytes, or other types)
        
    Returns:
        Sanitized text with problematic characters removed
    """
    if text is None:
        return ""

    # Handle different input types
    if isinstance(text, bytes):
        try:
            text = text.decode('utf-8', errors='replace')
        except Exception:
            # If we can't decode as UTF-8, convert to a safe string representation
            return f"[Binary content of {len(text)} bytes]"

    # Convert to string if not already
    if not isinstance(text, str):
        text = str(text)

    return re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text) 