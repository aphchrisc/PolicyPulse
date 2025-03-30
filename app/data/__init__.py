"""
app/data/__init__.py

This module provides a refactored and modular approach to database operations
for the legislative tracking system. The implementation separates concerns
into specialized store classes for better maintainability and testing.

Export all public classes to maintain backwards compatibility.
"""

from app.data.base_store import BaseStore, ensure_connection, validate_inputs
from app.data.user_store import UserStore
from app.data.search_store import SearchStore
from app.data.legislation_store import LegislationStore
from app.data.texas_store import TexasLegislationStore
from app.data.analytics_store import AnalyticsStore
from app.data.errors import (
    DataStoreError, ConnectionError, ValidationError, DatabaseOperationError
)

# Main DataStore class for backwards compatibility
from app.data.data_store import DataStore

__all__ = [
    'DataStore',
    'BaseStore',
    'UserStore',
    'SearchStore',
    'LegislationStore',
    'TexasLegislationStore',
    'AnalyticsStore',
    'DataStoreError',
    'ConnectionError',
    'ValidationError',
    'DatabaseOperationError',
    'ensure_connection',
    'validate_inputs',
] 