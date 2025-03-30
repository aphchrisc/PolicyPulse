"""
Core AIAnalysis orchestration module.

This module provides the main entry point for analyzing legislation,
coordinating between the various specialized modules.
"""

import logging

# Import the core class from refactored modules
from .core_analysis import AIAnalysis

# Import methods from specialized modules
from .analysis_processing import (
    extract_content_from_legislation,
    process_analysis,
    call_structured_analysis,
    analyze_in_chunks
)

# Import processing utilities
from .text_preprocessing import preprocess_text, is_binary_pdf, ensure_plain_string

# Import database operations
from .db_operations import (
    get_cached_analysis,
    get_legislation_object, 
    store_legislation_analysis,
    store_legislation_analysis_async
)

# Import impact analysis capabilities
from .impact_analysis import update_legislation_priority, calculate_priority_scores

# Import core analysis functionality
from .bill_analysis import analyze_bill, analyze_bill_async
from .async_analysis import analyze_legislation_async, batch_analyze_async

logger = logging.getLogger(__name__)

# Re-export the AIAnalysis class and key functions
__all__ = [
    # Core class and analysis functions
    'AIAnalysis',
    'analyze_bill',
    'analyze_bill_async',
    'analyze_legislation_async',
    'batch_analyze_async',
    
    # Analysis processing functions
    'extract_content_from_legislation',
    'process_analysis',
    'call_structured_analysis', 
    'analyze_in_chunks',
    
    # Text preprocessing utilities
    'preprocess_text',
    'is_binary_pdf',
    'ensure_plain_string',
    
    # Database operations
    'get_cached_analysis',
    'get_legislation_object',
    'store_legislation_analysis',
    'store_legislation_analysis_async',
    
    # Impact analysis
    'update_legislation_priority',
    'calculate_priority_scores'
]
