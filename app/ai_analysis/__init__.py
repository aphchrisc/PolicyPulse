"""
AI Analysis Module for Legislation

This module provides functionality for AI-powered analysis of legislative
documents, including:

1. Structured analysis of bill text
2. PDF processing with vision capabilities
3. Impact assessment and categorization
4. Asynchronous processing for batch operations

Example usage:

```python
from app.ai_analysis import AIAnalysis, analyze_bill

# Initialize the analyzer
analyzer = AIAnalysis(db_session=db.session)

# Analyze bill text directly
analysis = analyze_bill(analyzer, bill_text="The text of the bill...", 
                       bill_title="Sample Bill", state="Texas")

# Analyze legislation from the database
from app.ai_analysis import analyze_legislation
analysis_obj = analyze_legislation(analyzer, legislation_id=42)

# Analyze a PDF document
from app.ai_analysis import analyze_pdf
analysis_data = analyze_pdf(analyzer, pdf_content=pdf_bytes, title="Sample PDF Bill")

# Batch analyze multiple bills asynchronously
from app.ai_analysis import batch_analyze_async
import asyncio

async def run_batch():
    results = await batch_analyze_async(analyzer, [1, 2, 3, 4, 5])
    print(f"Completed {results['stats']['success_count']} analyses")

asyncio.run(run_batch())
```
"""

# Import the core class and main functions
from .core_analysis import AIAnalysis
from .bill_analysis import analyze_bill, analyze_bill_async
from .legislation_analyzer import analyze_legislation, analyze_legislation_async
from .async_analysis import batch_analyze_async
from .pdf_analyzer import analyze_pdf, analyze_pdf_async

# Import error types
from .errors import (
    AIAnalysisError, 
    TokenLimitError, 
    APIError, 
    RateLimitError, 
    ContentProcessingError,
    DatabaseError
)

# Import supporting utility functions
from .text_preprocessing import preprocess_text, is_binary_pdf
from .impact_analysis import calculate_priority_scores, update_legislation_priority
from .utils import TokenCounter, create_analysis_instructions, get_analysis_json_schema

# Import OpenAI client that handles API interactions
from .openai_client import OpenAIClient, check_openai_api

# Import special handling for PDF documents
from .pdf_handler import encode_pdf_for_vision, prepare_vision_message

# Import database operations
from .db_operations import (
    get_cached_analysis,
    get_legislation_object,
    store_legislation_analysis,
    store_legislation_analysis_async
)

# Define the public API
__all__ = [
    # Core classes
    'AIAnalysis',
    'TokenCounter',
    'OpenAIClient',
    
    # Main analysis functions
    'analyze_bill',
    'analyze_bill_async',
    'analyze_legislation',
    'analyze_legislation_async',
    'batch_analyze_async',
    'analyze_pdf',
    'analyze_pdf_async',
    
    # Error types
    'AIAnalysisError',
    'TokenLimitError',
    'APIError',
    'RateLimitError',
    'ContentProcessingError',
    'DatabaseError',
    
    # Supporting utilities
    'preprocess_text',
    'is_binary_pdf',
    'calculate_priority_scores',
    'update_legislation_priority',
    'create_analysis_instructions',
    'get_analysis_json_schema',
    'check_openai_api',
    
    # PDF handling
    'encode_pdf_for_vision',
    'prepare_vision_message',
    
    # Database operations
    'get_cached_analysis',
    'get_legislation_object',
    'store_legislation_analysis',
    'store_legislation_analysis_async'
]

__version__ = '1.0.0'