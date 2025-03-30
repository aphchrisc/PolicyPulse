"""
Admin Routes

This module contains administrative endpoints for cache management, rate limiting,
and logging configuration.
"""

import logging
import time
from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime, timezone
from typing import Optional

from app.api.middleware import cache_manager, rate_limiter, invalidate_cache
from app.api.utils import log_api_call
from app.api.error_handlers import error_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/admin")

# -----------------------------------------------------------------------------
# Cache Management Endpoints
# -----------------------------------------------------------------------------

@router.post("/cache/invalidate", tags=["Admin"])
@log_api_call
async def invalidate_cache_endpoint(endpoint_prefix: Optional[str] = None):
    """
    Invalidate the cache for a specific endpoint prefix or all endpoints.
    This is an admin-only endpoint that should be protected in production.
    
    Args:
        endpoint_prefix: Optional endpoint prefix to invalidate (e.g., "/legislation")
        
    Returns:
        Status message
    """
    # In production, this should be protected by authentication
    try:
        await invalidate_cache(cache_manager, endpoint_prefix)
        return {
            "status": "success",
            "message": f"Cache invalidated for {endpoint_prefix or 'all endpoints'}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error invalidating cache: {str(e)}",
        ) from e

@router.get("/cache/status", tags=["Admin"])
@log_api_call
async def cache_status():
    """
    Get the current cache status.
    This is an admin-only endpoint that should be protected in production.
    
    Returns:
        Cache status information
    """
    # In production, this should be protected by authentication
    try:
        # Count cached items and get memory usage estimate
        cache_size = len(cache_manager.cache)
        # Rough estimate of memory usage
        memory_usage = sum(len(str(v)) for v in cache_manager.cache.values()) / 1024  # KB

        return {
            "status": "success",
            "cache_info": {
                "items_count": cache_size,
                "memory_usage_kb": round(memory_usage, 2),
                "cacheable_endpoints": list({
                    "/health": 60,
                    "/legislation": 300,
                    "/legislation/search": 300,
                    "/texas/health-legislation": 300,
                    "/texas/local-govt-legislation": 300,
                    "/bills/": 300,
                    "/states/": 3600,
                    "/dashboard/impact-summary": 600,
                    "/dashboard/recent-activity": 300
                }.keys())
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting cache status: {str(e)}",
        ) from e

# -----------------------------------------------------------------------------
# Rate Limit Management Endpoints
# -----------------------------------------------------------------------------

@router.get("/rate-limit/status", tags=["Admin"])
@log_api_call
async def rate_limit_status():
    """
    Get the current rate limit status.
    This is an admin-only endpoint that should be protected in production.
    
    Returns:
        Rate limit status information
    """
    # In production, this should be protected by authentication
    try:
        # Get rate limit information
        rate_limit_info = {
            "active_ips": len(rate_limiter.tokens),
            "rate_limited_ips": sum(
                tokens == 0 for tokens, _ in rate_limiter.tokens.values()
            ),
            "endpoint_limits": {
                "/health": 200,
                "/legislation": 100,
                "/legislation/search": 50,
                "/texas/health-legislation": 50,
                "/texas/local-govt-legislation": 50,
                "/bills/": 100,
                "/states/": 200,
                "/dashboard/impact-summary": 50,
                "/dashboard/recent-activity": 50,
                "/search/advanced": 30
            },
        }

        return {
            "status": "success",
            "rate_limit_info": rate_limit_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting rate limit status: {str(e)}",
        ) from e

@router.post("/rate-limit/reset", tags=["Admin"])
@log_api_call
async def reset_rate_limits(ip_address: Optional[str] = None):
    """
    Reset rate limits for a specific IP or all IPs.
    This is an admin-only endpoint that should be protected in production.
    
    Args:
        ip_address: Optional IP address to reset
        
    Returns:
        Status message
    """
    # In production, this should be protected by authentication
    try:
        async with rate_limiter.lock:
            if ip_address:
                if ip_address in rate_limiter.tokens:
                    rate_limiter.tokens[ip_address] = (rate_limiter.rate_limit, time.time())
                    message = f"Rate limit reset for IP {ip_address}"
                else:
                    message = f"IP {ip_address} not found in rate limiter"
            else:
                rate_limiter.tokens.clear()
                message = "All rate limits reset"

        return {
            "status": "success",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error resetting rate limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting rate limits: {str(e)}",
        ) from e

# -----------------------------------------------------------------------------
# Logging Management Endpoints
# -----------------------------------------------------------------------------

@router.get("/logging/status", tags=["Admin"])
@log_api_call
async def logging_status():
    """
    Get the current logging status.
    This is an admin-only endpoint that should be protected in production.
    
    Returns:
        Logging status information
    """
    # In production, this should be protected by authentication
    try:
        # Get logging information
        logging_info = {
            "root_level": logging.getLevelName(logging.getLogger().level),
            "app_level": logging.getLevelName(logger.level),
            "handlers": [
                {
                    "name": handler.__class__.__name__,
                    "level": logging.getLevelName(handler.level)
                }
                for handler in logging.getLogger().handlers
            ]
        }

        return {
            "status": "success",
            "logging_info": logging_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting logging status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting logging status: {str(e)}",
        ) from e

@router.post("/logging/level", tags=["Admin"])
@log_api_call
async def set_logging_level(level: str = "INFO"):
    """
    Set the logging level.
    This is an admin-only endpoint that should be protected in production.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Status message
    """
    # In production, this should be protected by authentication
    try:
        # Validate logging level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level = level.upper()
        if level not in valid_levels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid logging level. Must be one of: {', '.join(valid_levels)}"
            )

        # Set logging level
        numeric_level = getattr(logging, level)
        logger.setLevel(numeric_level)

        return {
            "status": "success",
            "message": f"Logging level set to {level}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting logging level: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting logging level: {str(e)}",
        ) from e