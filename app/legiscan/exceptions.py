"""
Custom exceptions for the LegiScan API integration.
"""


class ApiError(Exception):
    """Custom exception for LegiScan API errors."""
    pass


class RateLimitError(ApiError):
    """Custom exception for rate limiting errors."""
    pass 