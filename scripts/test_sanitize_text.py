#!/usr/bin/env python
"""
test_sanitize_text.py

Script to test the improved sanitize_text function and ensure it properly handles NUL characters.
"""

import os
import sys
import logging

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now we can import from app
from app.legiscan_api import sanitize_text

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sanitize_text():
    """Test the sanitize_text function with various inputs"""
    
    # Test case 1: Normal text
    normal_text = "This is normal text without any special characters."
    sanitized = sanitize_text(normal_text)
    logger.info(f"Test 1 (Normal text): {'PASS' if sanitized == normal_text else 'FAIL'}")
    
    # Test case 2: Text with NUL characters
    nul_text = "This text has\x00NUL\x00characters."
    expected = "This text hasNULcharacters."
    sanitized = sanitize_text(nul_text)
    logger.info(f"Test 2 (NUL characters): {'PASS' if sanitized == expected else 'FAIL'}")
    logger.info(f"  Original: {repr(nul_text)}")
    logger.info(f"  Sanitized: {repr(sanitized)}")
    
    # Test case 3: Text with other control characters
    control_text = "This text has\x01\x02\x03control\x04\x05\x06characters."
    expected = "This text hascontrolcharacters."
    sanitized = sanitize_text(control_text)
    logger.info(f"Test 3 (Control characters): {'PASS' if sanitized == expected else 'FAIL'}")
    logger.info(f"  Original: {repr(control_text)}")
    logger.info(f"  Sanitized: {repr(sanitized)}")
    
    # Test case 4: Binary content
    binary_data = b'%PDF-1.5\x00\x01\x02'
    sanitized = sanitize_text(binary_data)
    logger.info(f"Test 4 (Binary content): {'PASS' if isinstance(sanitized, str) else 'FAIL'}")
    logger.info(f"  Original: {repr(binary_data)}")
    logger.info(f"  Sanitized: {repr(sanitized)}")
    
    # Test case 5: None input
    none_input = None
    sanitized = sanitize_text(none_input)
    logger.info(f"Test 5 (None input): {'PASS' if sanitized == '' else 'FAIL'}")
    
    # Test case 6: Non-string input
    non_string = 12345
    sanitized = sanitize_text(non_string)
    logger.info(f"Test 6 (Non-string input): {'PASS' if isinstance(sanitized, str) else 'FAIL'}")
    logger.info(f"  Original: {repr(non_string)}")
    logger.info(f"  Sanitized: {repr(sanitized)}")

if __name__ == "__main__":
    logger.info("Testing sanitize_text function...")
    test_sanitize_text()
    logger.info("Tests complete!")