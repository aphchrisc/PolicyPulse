"""
legiscan_api.py

Wrapper module to maintain backwards compatibility for the LegiScan API.
Redirects to the new modular implementation.

This module imports and re-exports the LegiScanAPI class from the new modular structure
to ensure that existing code continues to work.
"""

from app.legiscan.legiscan_api import LegiScanAPI
from app.legiscan.exceptions import ApiError, RateLimitError

# Re-export for backward compatibility
__all__ = ["LegiScanAPI", "ApiError", "RateLimitError"]
