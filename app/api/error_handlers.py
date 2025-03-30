"""
API Error Handlers

This module contains error handling functions and utilities for the PolicyPulse API.
It provides consistent error responses and logging across the application.
"""

import logging
import traceback
from typing import Dict, Type, Any, Optional
from datetime import datetime, timezone
from contextlib import contextmanager
from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import custom exceptions
from app.data.errors import ConnectionError, ValidationError, DatabaseOperationError

def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom handler for validation errors to provide more user-friendly error messages.

    Args:
        request: The request that caused the validation error
        exc: The validation error

    Returns:
        JSONResponse with detailed error information
    """
    errors = []
    for error in exc.errors():
        error_location = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": error_location,
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "code": "VALIDATION_ERROR",
            "message": "Input validation error",
            "details": errors,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

def general_exception_handler(request: Request, exc: Exception):
    """
    Generic exception handler to provide consistent error responses.

    Args:
        request: The request that caused the exception
        exc: The exception that was raised

    Returns:
        JSONResponse with error details
    """
    # Log the error with traceback
    logger.error(f"Unhandled exception processing {request.method} {request.url}: {exc}")
    logger.error(traceback.format_exc())

    # Get error code and status code based on exception type
    # Map specific exceptions to error codes and status codes
    error_mapping = {
        ConnectionError: ("CONNECTION_ERROR", status.HTTP_503_SERVICE_UNAVAILABLE),
        DatabaseOperationError: ("DATABASE_ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR),
        ValidationError: ("VALIDATION_ERROR", status.HTTP_400_BAD_REQUEST),
        ValueError: ("VALUE_ERROR", status.HTTP_400_BAD_REQUEST),
        KeyError: ("KEY_ERROR", status.HTTP_400_BAD_REQUEST),
        HTTPException: (getattr(exc, "error_code", "HTTP_ERROR"), exc.status_code if isinstance(exc, HTTPException) else status.HTTP_500_INTERNAL_SERVER_ERROR),
    }
    
    # Find the most appropriate matching exception type
    exc_type = type(exc)
    matching_exc_types = [et for et in error_mapping.keys() if issubclass(exc_type, et)]
    
    if matching_exc_types:
        # Use the most specific matching type (the one with the shortest MRO)
        best_match = min(matching_exc_types, key=lambda et: len(et.__mro__))
        error_code, status_code = error_mapping[best_match]
    else:
        # Default if no match found
        error_code = f"{type(exc).__name__}".upper()
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Return a standard error response
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "code": error_code,
            "message": str(exc) or "An unexpected error occurred",
            "details": {
                "error_type": type(exc).__name__,
                "path": str(request.url)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@contextmanager
def error_handler(operation_name: str, error_map: Optional[Dict[Type[Exception], int]] = None):
    """
    Context manager for consistent error handling in API endpoints.

    Args:
        operation_name: Name of the operation for logging
        error_map: Mapping of exception types to HTTP status codes

    Yields:
        Control to the wrapped code block

    Raises:
        HTTPException: With the appropriate status code and detail message
    """
    # Default error mapping if none provided
    if error_map is None:
        error_map = {
            ValidationError: status.HTTP_400_BAD_REQUEST,
            ConnectionError: status.HTTP_503_SERVICE_UNAVAILABLE,
            DatabaseOperationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
            Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
        }

    try:
        # Yield control to the wrapped code block
        yield
    except Exception as e:
        # Get the exception type
        exc_type = type(e)

        # Find the most specific matching exception type in the error map
        matching_types = [t for t in error_map.keys() if issubclass(exc_type, t)]
        
        if not matching_types:
            # Default to Exception if no match
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            logger.error(f"Error in {operation_name}: {e}", exc_info=True)
        else:
            # Get the most specific type (the one with the shortest MRO)
            most_specific_type = min(matching_types, key=lambda t: len(t.__mro__))
            status_code = error_map[most_specific_type]
            
            # Log the error with appropriate severity
            if status_code >= 500:
                logger.error(f"Error in {operation_name}: {e}", exc_info=True)
            else:
                logger.warning(f"Error in {operation_name}: {e}")

        # Raise HTTPException with appropriate status code and detail
        # Note: We don't set 'from e' here to avoid linter errors
        raise HTTPException(
            status_code=status_code,
            detail=f"{operation_name} failed: {str(e)}",
        )

# Export all error handlers
__all__ = [
    'validation_exception_handler',
    'general_exception_handler',
    'error_handler',
]