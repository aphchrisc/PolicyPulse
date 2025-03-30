"""
OpenAI client interface for making API calls with appropriate error handling.

This module combines the various OpenAI client capabilities into a single
client class that can be used for all OpenAI API operations.
"""

# Standard library imports
import logging
from typing import Any, Optional

# PDF handling capabilities from our internal modules
from .pdf_handler import encode_pdf_for_vision, is_pdf_content, prepare_vision_message

# Import OpenAI with version checking
try:
    import openai
    # These imports are needed by inherited classes (PDFProcessingClient and BatchProcessingClient)
    # pylint: disable=unused-import
    from openai import OpenAI, AsyncOpenAI
    HAS_NEW_OPENAI = hasattr(openai, 'OpenAI')
    HAS_ASYNC_OPENAI = hasattr(openai, 'AsyncOpenAI')
except ImportError as e:
    raise ImportError(
        "Failed to import OpenAI package. Please install with: pip install openai"
    ) from e

try:
    # These SQLAlchemy imports are used by the parent classes for database operations
    # pylint: disable=unused-import
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import SQLAlchemyError
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

# Import our error classes used in the parent classes
# pylint: disable=unused-import
from .errors import APIError, RateLimitError, AIAnalysisError, DatabaseError

# Import our specialized client modules
from .openai_core import OpenAIClient, check_openai_api
from .batch_processing import BatchProcessingClient
from .pdf_processing import PDFProcessingClient

logger = logging.getLogger(__name__)


class OpenAIUnifiedClient(PDFProcessingClient, BatchProcessingClient):
    """
    Unified OpenAI client that combines all functionality.
    
    This client inherits from all specialized clients to provide a complete
    interface for OpenAI operations, including:
    - Core API functionality
    - Structured analysis
    - Batch processing
    - PDF handling
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4o-2024-08-06",
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        db_session: Optional[Any] = None,
        vision_enabled: bool = True,
    ):
        """
        Initialize the unified OpenAI client.

        Args:
            api_key: OpenAI API key
            model_name: Name of the model to use
            max_retries: Maximum number of retry attempts
            retry_base_delay: Base delay for exponential backoff
            db_session: Optional SQLAlchemy session for transaction support
            vision_enabled: Whether to enable vision features when supported
        """
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            max_retries=max_retries,
            retry_base_delay=retry_base_delay,
            db_session=db_session,
            vision_enabled=vision_enabled
        )
        
        logger.info("Initialized OpenAIUnifiedClient with model %s", model_name)
        if self.supports_vision:
            logger.info("Vision capabilities are supported by the selected model")


# For backwards compatibility, expose the unified client as OpenAIClient
OpenAIClient = OpenAIUnifiedClient

# Export utility functions
__all__ = [
    'OpenAIClient',
    'OpenAIUnifiedClient',
    'check_openai_api',
    # Export PDF utilities for external use
    'encode_pdf_for_vision',
    'is_pdf_content',
    'prepare_vision_message'
]
