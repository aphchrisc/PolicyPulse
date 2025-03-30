"""
scheduler/errors.py

Defines exception classes for scheduler and sync operations.
"""

class SyncError(Exception):
    """Base exception for sync-related errors."""


class DataSyncError(SyncError):
    """Exception raised when syncing data from external APIs."""


class AnalysisError(SyncError):
    """Exception raised when analyzing legislation.""" 
