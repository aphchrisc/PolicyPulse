"""
LegiScan API integration package.

This package provides a modular interface to the LegiScan API for retrieving
and managing legislation data.
"""

from app.legiscan.api import LegiScanConfig
from app.legiscan.exceptions import ApiError, RateLimitError
from app.legiscan.legiscan_api import LegiScanAPI

__all__ = ["LegiScanAPI", "LegiScanConfig", "ApiError", "RateLimitError"] 