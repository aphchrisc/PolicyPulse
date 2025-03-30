"""
Text preprocessing utilities for AI analysis.

This module provides utilities for preprocessing text before analysis,
including HTML detection and stripping, content sanitization, and token counting.
"""

import re
import logging
from typing import Any, Tuple
from contextlib import suppress

logger = logging.getLogger(__name__)

def is_binary_pdf(content: Any) -> bool:
    """
    Check if the content is a PDF file.
    
    Args:
        content: Content to check, can be bytes or any other type
        
    Returns:
        True if the content is a PDF, False otherwise
    """
    if not isinstance(content, bytes):
        return False

    # Check for PDF signature at the beginning of the file
    try:
        return content[:5] == b'%PDF-'
    except (IndexError, TypeError, AttributeError) as e:
        logger.warning("Error checking PDF signature: %s", e)
        return False

def ensure_plain_string(possibly_column: Any) -> str:
    """
    Convert a Column[str], bytes, or any other object to a plain `str`.
    Also sanitizes the text by removing NUL characters and control characters.
    
    Args:
        possibly_column: The object to convert to a plain string
        
    Returns:
        A sanitized string
    """
    if possibly_column is None:
        return ""
    
    # Handle special column objects from SQLAlchemy
    with suppress(ImportError):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import Column
        if isinstance(possibly_column, Column):
            possibly_column = str(possibly_column)

    # Convert bytes to string
    if isinstance(possibly_column, bytes):
        try:
            possibly_column = possibly_column.decode("utf-8", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            return f"[Binary content of {len(possibly_column)} bytes]"

    # Ensure we have a string
    if not isinstance(possibly_column, str):
        possibly_column = str(possibly_column)

    # Remove control characters
    return re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', possibly_column)

def strip_html_tags(html_content: str) -> Tuple[str, str]:
    """
    Strip HTML tags using BeautifulSoup for robust processing.
    
    Args:
        html_content: HTML content to strip
        
    Returns:
        Tuple of (stripped_text, method_used)
    """
    if not html_content or not isinstance(html_content, str):
        return "", "empty_content"

    # Check if content appears to be HTML
    html_indicators = ["<html", "<body", "<div", "<span", "<p", "<table"]
    html_indicator_count = sum(
        indicator in html_content.lower() for indicator in html_indicators
    )

    if html_indicator_count < 3 and all(
        tag not in html_content.lower() for tag in ["<html", "<body"]
    ):
        return html_content, "not_html"

    try:
        # Always try BeautifulSoup first
        try:
            # pylint: disable=import-outside-toplevel
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()

            # Get text with spacing between elements
            stripped_text = soup.get_text(separator=' ', strip=True)

            if len(stripped_text) < len(html_content):
                logger.info("Successfully stripped HTML using BeautifulSoup: %d → %d chars", 
                            len(html_content), len(stripped_text))
                return stripped_text, "beautifulsoup"
            else:
                # Try more aggressive approach
                stripped_text = ' '.join(soup.stripped_strings)
                logger.info("Used aggressive BeautifulSoup stripping: %d → %d chars", 
                            len(html_content), len(stripped_text))
                return stripped_text, "beautifulsoup_aggressive"

        except ImportError:
            logger.warning("BeautifulSoup not available, falling back to regex-based stripping")
            return strip_html_with_regex(html_content)
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning("Error stripping HTML tags: %s", e)
        return html_content[:100000], "stripping_failed"

def strip_html_with_regex(html_content: str) -> Tuple[str, str]:
    """
    Strip HTML tags using regex-based approach as a fallback when BeautifulSoup is not available.
    
    Args:
        html_content: HTML content to strip
        
    Returns:
        Tuple of (stripped_text, method_used)
    """
    # Remove CSS and JavaScript
    text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html_content)
    text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    stripped_text = text.strip()

    # Verify that stripping actually did something
    if len(stripped_text) >= len(html_content):
        # If regex didn't work, try a more aggressive approach
        text = re.sub(r'<[^>]*>', '', html_content)  # More aggressive tag removal
        stripped_text = re.sub(r'\s+', ' ', text).strip()
        logger.info("Used aggressive regex stripping: %d → %d chars", 
                   len(html_content), len(stripped_text))
        return stripped_text, "aggressive_regex"

    logger.info("Used regex-based stripping: %d → %d chars", 
               len(html_content), len(stripped_text))
    return stripped_text, "regex"

def process_html_content(analyzer: Any, text: str) -> str:
    """
    Process text to detect and strip HTML content if present.
    
    Args:
        analyzer: AIAnalysis instance (for access to token counter)
        text: The text to process
        
    Returns:
        Processed text with HTML stripped if applicable
    """
    if not isinstance(text, str) or len(text) <= 5000:
        return text

    # More comprehensive HTML detection - check for actual HTML tags
    html_indicators = ["<html", "<body", "<div", "<span", "<p", "<table", "<script", "<style",
                      "<a ", "<img ", "<form", "<input", "<h1", "<h2", "<h3", "<ul", "<ol", "<li"]

    # Count how many HTML indicators are present
    html_indicator_count = sum(
        indicator in text.lower() for indicator in html_indicators
    )

    # Only consider it HTML if multiple indicators are found or specific structural tags
    has_html = html_indicator_count >= 3 or any(tag in text.lower() for tag in ["<html", "<body", "<head"])

    if has_html:
        logger.info("Detected HTML content in text (%d chars) with %d HTML indicators", 
                   len(text), html_indicator_count)

        # Count tokens before stripping
        before_tokens = analyzer.token_counter.count_tokens(text)
        logger.info("Token count before HTML stripping: %d", before_tokens)

        # Strip HTML tags - returns tuple of (stripped_text, method_used)
        stripped_result = strip_html_tags(text)
        stripped_text, method_used = stripped_result

        # Only use the stripped text if it actually reduced the size and isn't "not_html"
        if method_used != "not_html" and len(stripped_text) < len(text):
            # Update text with the stripped content
            text = stripped_text
            logger.info("After stripping HTML tags (%s): %d chars", 
                       method_used, len(text))
        else:
            logger.info("HTML stripping ineffective (%s), keeping original text", 
                       method_used)

        # Count tokens after stripping
        after_tokens = analyzer.token_counter.count_tokens(text)
        token_reduction = before_tokens - after_tokens
        logger.info("Token count after HTML stripping: %d (reduced by %d tokens)", 
                   after_tokens, token_reduction)

    return text

def preprocess_text(analyzer: Any, text: str) -> Tuple[str, int]:
    """
    Preprocess text for analysis by removing HTML and sanitizing content.
    
    Args:
        analyzer: AIAnalysis instance (for access to token counter)
        text: The text to preprocess
        
    Returns:
        Tuple of (preprocessed_text, token_count)
    """
    # Ensure it's a plain string
    safe_text = ensure_plain_string(text)
    
    # Process HTML if present
    safe_text = process_html_content(analyzer, safe_text)
    
    # Count tokens
    token_count = analyzer.token_counter.count_tokens(safe_text)
    
    return safe_text, token_count 
