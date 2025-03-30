"""
API Utilities

This module contains utility functions used across the API endpoints.
"""

import logging
import time
import asyncio
from typing import Callable, TypeVar, Dict, Any, Optional, Union
from functools import wraps
from datetime import datetime
from fastapi import Request, Response, BackgroundTasks
import json
from app.data.errors import ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Type variable for generic function
T = TypeVar('T')

def log_api_call(func: Callable):
    """
    Decorator to log API calls with timing information.

    Args:
        func: The API endpoint function to wrap

    Returns:
        Wrapped function with logging
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get request from args or kwargs
        request = kwargs.get('request')
        if request is None:
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
        
        # For endpoints without request parameter (like health check)
        func_name = func.__name__
        
        # Initialize endpoint variable with a default value
        endpoint = None
        
        # Log info based on what we have
        if request is not None:
            client_ip = request.client.host if hasattr(request, 'client') and request.client is not None else 'unknown'
            endpoint = f"{request.method} {request.url.path}"
            logger.info(f"API call from {client_ip}: {endpoint}")
        else:
            logger.info(f"API call to function: {func_name}")

        # Track timing
        start_time = datetime.now()
        try:
            # Execute the endpoint function
            response = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            # Log successful completion with timing
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            endpoint_name = endpoint if request else func_name
            logger.info(f"API call completed: {endpoint_name} ({elapsed:.2f}ms)")
            return response
        except Exception as e:
            # Log exception with timing
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            endpoint_name = endpoint if request else func_name
            logger.error(f"API call failed: {endpoint_name} ({elapsed:.2f}ms) - {str(e)}")
            raise

    return wrapper

def run_in_background(func):
    """
    Decorator to run a function in a background task with proper error handling.

    Args:
        func: The function to run in the background

    Returns:
        Wrapped function that executes in a background task
    """
    @wraps(func)
    def wrapper(background_tasks: BackgroundTasks, *args, **kwargs):
        # Define a wrapper that handles exceptions
        def background_wrapper():
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in background task {func.__name__}: {e}", exc_info=True)

        # Add the task to the background tasks list
        background_tasks.add_task(background_wrapper)

        # Return a simple status message
        return {
            "status": "processing",
            "message": f"Task {func.__name__} started in the background"
        }

    return wrapper

def add_pagination_headers(response: Response, request: Request, total_count: int, limit: int, offset: int):
    """
    Add pagination headers to the response.
    
    Args:
        response: FastAPI response object
        request: FastAPI request object
        total_count: Total number of items
        limit: Number of items per page
        offset: Offset from the beginning
        
    Returns:
        None, modifies the response in place
    """
    # Calculate pagination values
    page_size = max(1, limit)  # Ensure page size is at least 1
    current_page = (offset // page_size) + 1 if page_size > 0 else 1
    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

    # Add headers
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Page-Count"] = str(total_pages)
    response.headers["X-Current-Page"] = str(current_page)
    response.headers["X-Page-Size"] = str(page_size)

    base_url = str(request.url).split('?')[0]
    query_params = dict(request.query_params) | {
        "limit": str(limit),
        "offset": "0",
    }
    query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
    links = [f'<{base_url}?{query_string}>; rel="first"']
    # Previous page
    if current_page > 1:
        query_params["offset"] = str(max(0, offset - limit))
        query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
        links.append(f'<{base_url}?{query_string}>; rel="prev"')

    # Next page
    if current_page < total_pages:
        query_params["offset"] = str(offset + limit)
        query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
        links.append(f'<{base_url}?{query_string}>; rel="next"')

    # Last page
    last_offset = max(0, (total_pages - 1) * limit)
    query_params["offset"] = str(last_offset)
    query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
    links.append(f'<{base_url}?{query_string}>; rel="last"')

    # Add Link header
    response.headers["Link"] = ", ".join(links)

def validate_enum_parameter(param_value, enum_class, param_name):
    """Validate that a parameter value is a valid enum value."""
    if param_value and param_value not in [s.value for s in enum_class]:
        raise ValidationError(f"Invalid {param_name}: {param_value}")

def validate_date_format(date_str, param_name):
    """Validate that a date string is in the correct format."""
    try:
        datetime.fromisoformat(date_str)
    except ValueError as e:
        raise ValidationError(
            f"Invalid {param_name} date: {date_str}. Format should be YYYY-MM-DD"
        ) from e

def build_texas_legislation_filters(focus=None, bill_status=None, impact_level=None,
                                   introduced_after=None, keywords=None,
                                   municipality_type=None, relevance_threshold=None):
    """Build a filters dictionary for Texas legislation queries."""
    filters = {}
    
    if focus:
        filters["focus"] = focus
    if bill_status:
        filters["bill_status"] = bill_status
    if impact_level:
        filters["impact_level"] = impact_level
    if introduced_after:
        filters["introduced_after"] = introduced_after
    if keywords:
        filters["keywords"] = [k.strip() for k in keywords.split(",") if k.strip()]
    if municipality_type:
        filters["municipality_type"] = municipality_type
    if relevance_threshold is not None:
        filters["relevance_threshold"] = relevance_threshold
        
    return filters

def get_paginated_legislation_response(response, request, count_method, get_method, limit, offset, filters=None):
    """Get a paginated response for legislation endpoints."""
    filters = filters or {}
    
    # Get total count for pagination
    total_count = count_method(filters=filters)
    
    # Get legislation
    legislation = get_method(limit=limit, offset=offset, filters=filters)
    
    # Add pagination headers
    add_pagination_headers(response, request, total_count, limit, offset)
    
    # Format as LegislationListResponse
    return {
        "count": len(legislation),
        "items": legislation,
        "page_info": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(legislation) < total_count
        }
    }

def get_request_id(request: Request) -> str:
    """
    Get the current request ID from the request state.
    
    Args:
        request: FastAPI request
        
    Returns:
        Request ID string
    """
    return getattr(request.state, "request_id", "unknown")

class StreamingJSONResponse(Response):
    """
    A custom streaming JSON response class that correctly sets Content-Length.
    This works around issues with mismatched Content-Length in middleware chains.
    """
    media_type = "application/json"

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ):
        # Convert content to JSON bytes, safely handling various input types
        try:
            if content is None:
                # Default to empty JSON object for None
                self.content_bytes = b"{}"
            else:
                # Try to serialize the content to JSON
                self.content_bytes = json.dumps(content, default=str).encode("utf-8")
        except (TypeError, ValueError) as e:
            # Handle serialization errors by returning error message
            logger.error(f"Failed to serialize response content: {e}")
            error_content = {"error": "Failed to serialize response content"}
            self.content_bytes = json.dumps(error_content).encode("utf-8")
        
        # Calculate content length exactly
        content_length = len(self.content_bytes)
        
        # Set up headers with precise content length
        headers = headers or {}
        headers.update({"Content-Length": str(content_length)})
        
        # Initialize response without content
        super().__init__(
            None,  # We'll handle content ourselves
            status_code=status_code,
            headers=headers,
            media_type=media_type,
        )
        
        # Track whether headers have been sent
        self.headers_sent = False

    async def __call__(self, scope, receive, send):
        try:
            # Send headers
            await send({
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            })
            
            # Mark headers as sent
            self.headers_sent = True
            
            # Send body as a single chunk
            await send({
                "type": "http.response.body", 
                "body": self.content_bytes,
                "more_body": False
            })
        except Exception as e:
            # Log the error but don't crash
            logger.error(f"Error sending response: {e}")
            # Try to send a fallback error response if we haven't sent headers yet
            try:
                # Only try this if we haven't sent headers
                if not self.headers_sent:
                    fallback_body = json.dumps({"error": "Internal server error"}).encode("utf-8")
                    fallback_headers = [(b"content-type", b"application/json"), 
                                      (b"content-length", str(len(fallback_body)).encode())]
                    
                    await send({
                        "type": "http.response.start",
                        "status": 500,
                        "headers": fallback_headers,
                    })
                    
                    await send({
                        "type": "http.response.body", 
                        "body": fallback_body,
                        "more_body": False
                    })
            except Exception:
                # If even the fallback fails, just log and continue
                logger.error("Failed to send fallback error response", exc_info=True)
                # Reraise the original exception
                raise e

# Export all utility functions
__all__ = [
    'log_api_call',
    'run_in_background',
    'add_pagination_headers',
    'validate_enum_parameter',
    'validate_date_format',
    'build_texas_legislation_filters',
    'get_paginated_legislation_response',
    'get_request_id',
    'StreamingJSONResponse'
]