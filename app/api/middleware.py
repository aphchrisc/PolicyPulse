"""
API Middleware

This module contains middleware implementations for the PolicyPulse API.
Middleware components process requests and responses to add functionality
like rate limiting, caching, and request logging.
"""

# pylint: disable=broad-exception-caught

import logging
import time
import json
import uuid
import asyncio
from typing import Dict, Any, Optional, List, Union, Protocol
from datetime import datetime, timezone
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Rate Limiting Implementation
# -----------------------------------------------------------------------------

class RateLimiter:  # pylint: disable=too-few-public-methods
    """
    Rate limiter implementation using a token bucket algorithm.
    Limits requests based on client IP address.
    """
    def __init__(self, rate_limit: int = 100, time_window: int = 60):
        """
        Initialize the rate limiter.
        
        Args:
            rate_limit: Maximum number of requests allowed in the time window
            time_window: Time window in seconds
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.tokens = {}  # IP -> (tokens, last_refill_time)
        self.lock = asyncio.Lock()
    
    async def is_rate_limited(self, ip: str) -> tuple[bool, int, int]:
        """
        Check if a request from the given IP should be rate limited.
        
        Args:
            ip: Client IP address
            
        Returns:
            Tuple of (is_limited, remaining_tokens, retry_after)
        """
        async with self.lock:
            now = time.time()

            # Initialize if this is the first request from this IP
            if ip not in self.tokens:
                self.tokens[ip] = (self.rate_limit, now)

            tokens, last_refill = self.tokens[ip]

            # Calculate token refill based on time elapsed
            time_elapsed = now - last_refill
            token_refill = int((time_elapsed / self.time_window) * self.rate_limit)

            # Refill tokens up to the maximum
            tokens = min(self.rate_limit, tokens + token_refill)

            # If we refilled tokens, update the last refill time
            if token_refill > 0:
                last_refill = now

            if tokens <= 0:
                return True, 0, max(0, int(self.time_window - (now - last_refill)))
            tokens -= 1
            self.tokens[ip] = (tokens, last_refill)
            return False, tokens, 0

class RateLimitMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """
    Middleware for rate limiting requests based on client IP.
    """
    def __init__(self, app, rate_limiter_instance: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter_instance
        self.public_endpoints = {
            "/health": 200,  # Higher limit for health checks
            "/legislation": 100,
            "/legislation/search": 50,
            "/texas/health-legislation": 50,
            "/texas/local-govt-legislation": 50,
            "/bills/": 100,
            "/states/": 200,
            "/dashboard/impact-summary": 50,
            "/dashboard/recent-activity": 50,
            "/search/advanced": 30
        }
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for non-public endpoints or if not configured
        path = request.url.path
        
        # Find matching endpoint pattern
        matching_endpoint = None
        for endpoint in self.public_endpoints:
            if path.startswith(endpoint):
                matching_endpoint = endpoint
                break
        
        if not matching_endpoint:
            # No rate limiting for this endpoint
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Use custom rate limit for this endpoint
        custom_rate_limit = self.public_endpoints[matching_endpoint]
        custom_limiter = RateLimiter(rate_limit=custom_rate_limit, time_window=60)
        
        # Check rate limit
        is_limited, remaining, retry_after = await custom_limiter.is_rate_limited(client_ip)
        
        if is_limited:
            # Return rate limit exceeded response
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "error",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded. Please try again later.",
                    "details": {
                        "retry_after": retry_after
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(custom_rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + retry_after)
        
        return response

# -----------------------------------------------------------------------------
# Caching Implementation
# -----------------------------------------------------------------------------

class CacheManager:
    """
    Simple in-memory cache manager with TTL support.
    """
    def __init__(self):
        self.cache = {}
        self.ttl = {}
        self.lock = asyncio.Lock()
    
    async def get(self, key: str) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        async with self.lock:
            if key not in self.cache:
                return None
            
            # Check if the key has expired
            if key in self.ttl and self.ttl[key] < time.time():
                # Remove expired key
                del self.cache[key]
                del self.ttl[key]
                return None
            
            return self.cache[key]
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """
        Set a value in the cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        async with self.lock:
            self.cache[key] = value
            if ttl_seconds > 0:
                self.ttl[key] = time.time() + ttl_seconds
    
    async def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
            if key in self.ttl:
                del self.ttl[key]
    
    async def clear(self) -> None:
        """Clear the entire cache."""
        async with self.lock:
            self.cache.clear()
            self.ttl.clear()

class SimpleCacheProtocol(Protocol):
    """Protocol defining the interface for cache implementations."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache by key."""
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache with optional TTL."""
    
    def delete(self, key: str) -> None:
        """Delete a value from the cache by key."""

class CacheMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """Middleware for caching responses."""
    
    def __init__(self, app: ASGIApp, cache_manager_instance: Union['SimpleCache', CacheManager]):
        super().__init__(app)
        self.cache_manager = cache_manager_instance
    
    # pylint: disable=too-many-return-statements,too-many-branches,too-many-statements
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and cache response if applicable."""
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Generate cache key
        cache_key = f"{request.method}:{request.url.path}:{request.url.query}"
        
        # Try to get from cache
        cached_response = await self._get_from_cache(cache_key)
        if cached_response:
            return cached_response
        
        # Process the request
        response = await call_next(request)
        
        # Don't cache streaming responses or errors
        if isinstance(response, StreamingResponse) or response.status_code >= 400:
            response.headers["X-Cache"] = "BYPASS"
            return response
        
        # Try to cache the response
        return await self._cache_response(request, response, cache_key)
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Response]:
        """Attempt to retrieve and return a cached response."""
        if not self.cache_manager or not hasattr(self.cache_manager, 'get'):
            return None
            
        # Try to get from cache - handle both async and non-async methods
        try:  # pylint: disable=broad-exception-caught
            cached_data = None
            if asyncio.iscoroutinefunction(self.cache_manager.get):
                cached_data = await self.cache_manager.get(cache_key)
            else:
                cached_data = self.cache_manager.get(cache_key)
                
            # Validate and return cached response
            if cached_data and isinstance(cached_data, dict):
                try:  # pylint: disable=broad-exception-caught
                    return Response(
                        content=cached_data["content"],
                        status_code=cached_data["status_code"],
                        headers={**cached_data["headers"], "X-Cache": "HIT"},
                        media_type=cached_data["media_type"]
                    )
                except (KeyError, TypeError) as e:
                    logger.error("Invalid cache data format: %s", str(e))
        except Exception as e:
            logger.error("Error accessing cache: %s", str(e))
            
        return None
    
    async def _cache_response(self, request: Request, response: Response, cache_key: str) -> Response:
        """Extract content from response and cache it if possible."""
        try:
            # Extract body content from response
            body = self._extract_response_body(response)
            if body is None:
                # If body extraction failed, the response has been modified with headers
                return response
                
            # Create cache data
            cache_data = {
                "content": body,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "media_type": response.media_type
            }
            
            # Determine TTL based on request path
            ttl = self._determine_cache_ttl(request)
            
            # Store in cache
            await self._store_in_cache(cache_key, cache_data, ttl)
            
            # Return new response with cache miss header
            headers = dict(response.headers)
            headers["X-Cache"] = "MISS"
            
            return Response(
                content=body,
                status_code=cache_data["status_code"],
                headers=headers,
                media_type=cache_data["media_type"]
            )
        except Exception as e:
            # If caching fails, log and return original response
            logger.error("Cache error: %s", str(e), exc_info=True)
            response.headers["X-Cache"] = "ERROR"
            return response
    
    def _extract_response_body(self, response: Response) -> Optional[bytes]:
        """Extract body content from a response object."""
        # Skip non-Response or StreamingResponse objects
        if not isinstance(response, Response) or isinstance(response, StreamingResponse):
            response.headers["X-Cache"] = "BYPASS (Unsupported Response Type)"
            return None
            
        try:  # pylint: disable=broad-exception-caught
            # Try to access the body attribute
            if hasattr(response, "body"):
                try:  # pylint: disable=broad-exception-caught
                    return getattr(response, "body")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.debug("Error accessing body property: %s", str(e))
                    response.headers["X-Cache"] = "BYPASS (Body Access Error)"
                    return None
                    
            # No body attribute found
            logger.warning("No known body attribute found on response: %s", type(response))
            response.headers["X-Cache"] = "BYPASS (No Body Attribute)"
            return None
        except Exception as e:
            logger.warning("Cannot access response body: %s", str(e))
            response.headers["X-Cache"] = "BYPASS (Body Access Error)"
            return None
    
    def _determine_cache_ttl(self, request: Request) -> int:
        """Determine appropriate TTL based on request path."""
        # Default TTL: 10 minutes
        ttl = 600
        
        # Legislation details: 1 hour
        if "/legislation/" in request.url.path and "search" not in request.url.path:
            ttl = 3600
        # Search results: 5 minutes
        elif "/search/" in request.url.path:
            ttl = 300
            
        return ttl
    
    async def _store_in_cache(self, cache_key: str, cache_data: dict, ttl: int) -> None:
        """Store data in cache, handling both async and non-async cache managers."""
        if not self.cache_manager or not hasattr(self.cache_manager, 'set'):
            return
            
        try:  # pylint: disable=broad-exception-caught
            if asyncio.iscoroutinefunction(self.cache_manager.set):
                await self.cache_manager.set(cache_key, cache_data, ttl)
            else:
                self.cache_manager.set(cache_key, cache_data, ttl)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error storing in cache: %s", str(e))

# -----------------------------------------------------------------------------
# Request Logging Middleware
# -----------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """
    Middleware for logging all requests and responses.
    """
    async def dispatch(self, request: Request, call_next):
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state for use in endpoint handlers
        request.state.request_id = request_id
        
        # Get client info
        client_host = request.client.host if request.client else "unknown"
        
        # Start timer
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request %s: %s %s from %s - Query: %s",
            request_id, request.method, request.url.path,
            client_host, dict(request.query_params)
        )
        
        # Process the request
        try:  # pylint: disable=broad-exception-caught
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            
            # Log response
            logger.info(
                "Response %s: %s processed in %.4fs",
                request_id, response.status_code, process_time
            )
            
            return response
        except Exception as e:
            # Log exception
            logger.error(
                "Error %s: %s processing %s %s",
                request_id, str(e), request.method, request.url.path,
                exc_info=True
            )
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {
                        "request_id": request_id,
                        "error_type": type(e).__name__
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                headers={
                    "X-Request-ID": request_id,
                    "X-Process-Time": f"{process_time:.4f}"
                }
            )

# Function to invalidate cache for specific endpoints
async def invalidate_cache(cache_manager_instance: CacheManager, endpoint_prefix: Optional[str] = None):
    """
    Invalidate cache for a specific endpoint prefix or all if None.
    
    Args:
        cache_manager_instance: The cache manager instance
        endpoint_prefix: Endpoint prefix to invalidate, or None for all
    """
    # For a more sophisticated implementation, we would store
    # cache keys by endpoint prefix, but for simplicity we'll
    # just clear the entire cache if endpoint_prefix is None
    await cache_manager_instance.clear()
    message = f"Cache invalidated for {endpoint_prefix}" if endpoint_prefix else "Cache invalidated for all endpoints"
    logger.info(message)

# Initialize global instances
rate_limiter = RateLimiter()
cache_manager = CacheManager()

# Export middleware classes and instances
__all__ = [
    'RateLimiter',
    'RateLimitMiddleware',
    'CacheManager',
    'CacheMiddleware',
    'RequestLoggingMiddleware',
    'invalidate_cache',
    'rate_limiter',
    'cache_manager',
]

# =============================================================================
# Simplified in-memory implementations for cache and rate limiting
# =============================================================================

class SimpleCache:
    """Simple in-memory cache implementation."""
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        if key in self.cache:
            item = self.cache[key]
            if item["expiry"] > time.time():
                return item["value"]
            # Remove expired item
            del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache."""
        expiry = time.time() + (ttl if ttl is not None else self.ttl_seconds)
        self.cache[key] = {"value": value, "expiry": expiry}
    
    def delete(self, key: str) -> None:
        """Delete a key from the cache."""
        if key in self.cache:
            del self.cache[key]


class SimpleRateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, limit: int = 100, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}
    
    def check(self, key: str) -> bool:
        """Check if a key is within rate limits."""
        now = time.time()
        
        if key not in self.requests:
            self.requests[key] = [now]
            return True
        
        # Remove entries older than the window
        window_start = now - self.window_seconds
        self.requests[key] = [t for t in self.requests[key] if t >= window_start]
        
        # Check if under limit
        if len(self.requests[key]) < self.limit:
            self.requests[key].append(now)
            return True
        
        return False
    
    def get_headers(self, key: str) -> Dict[str, str]:
        """Get headers for rate limiting."""
        if key not in self.requests:
            return {
                "X-RateLimit-Limit": str(self.limit),
                "X-RateLimit-Remaining": str(self.limit),
                "X-RateLimit-Reset": str(int(time.time() + self.window_seconds))
            }
        
        # Count requests in current window
        now = time.time()
        window_start = now - self.window_seconds
        current_requests = [t for t in self.requests[key] if t >= window_start]
        
        remaining = max(0, self.limit - len(current_requests))
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(now + self.window_seconds))
        }


# Create instances for dependency injection
simple_cache_manager = SimpleCache()
simple_rate_limiter = SimpleRateLimiter()

# =============================================================================
# Middleware Components
# =============================================================================

class StreamingResponseFixMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """Middleware to fix content-length issues with streaming responses."""
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and fix content-length for streaming responses."""
        try:  # pylint: disable=broad-exception-caught
            # Execute the request handler
            response = await call_next(request)

            # Skip processing for StreamingResponse objects
            if isinstance(response, StreamingResponse):
                return response

            # Only attempt to check body for regular Response objects
            if isinstance(response, Response):
                logger.info("Skipping large response optimization due to body access issues")
                return response

            return response
        except Exception as e:
            logger.error("Error in StreamingResponseFixMiddleware: %s", str(e), exc_info=True)
            return Response(
                content=json.dumps({"error": "Internal Server Error"}),
                status_code=500,
                media_type="application/json"
            )
