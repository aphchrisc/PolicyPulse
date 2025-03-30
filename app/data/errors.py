"""
app/data/errors.py

This module defines exception classes for the data module.
"""


class DataStoreError(Exception):
    """Base exception class for DataStore-related errors."""
    pass


class ConnectionError(DataStoreError):
    """Raised when unable to establish or maintain a database connection."""
    pass


class ValidationError(DataStoreError):
    """Raised when input validation fails."""
    pass


class DatabaseOperationError(DataStoreError):
    """Raised when a database operation fails."""
    pass 