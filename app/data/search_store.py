"""
app/data/search_store.py

This module provides the SearchStore class for managing search history.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

from sqlalchemy.exc import SQLAlchemyError

from app.models import User, SearchHistory
from app.data.base_store import BaseStore, ensure_connection, validate_inputs
from app.data.errors import ValidationError, DatabaseOperationError
from app.data.user_store import UserStore

logger = logging.getLogger(__name__)


class SearchStore(BaseStore):
    """
    SearchStore handles all search history related database operations.
    """
    
    def __init__(self, max_retries: int = 3) -> None:
        """Initialize the SearchStore with a database session."""
        super().__init__(max_retries)
        # Create a UserStore instance to handle user operations
        self.user_store = UserStore(max_retries)

    def _validate_search_history(self, query_string: str, results_data: Dict[str, Any]) -> None:
        """
        Validate search history data before saving.

        Args:
            query_string: Search query string
            results_data: Results metadata dictionary

        Raises:
            ValidationError: If input data is invalid
        """
        if not isinstance(query_string, str):
            raise ValidationError(f"Query string must be a string, got {type(query_string).__name__}")

        if not isinstance(results_data, dict):
            raise ValidationError(f"Results data must be a dictionary, got {type(results_data).__name__}")

    @ensure_connection
    @validate_inputs(lambda self, email, query_string, results_data: (
        self._validate_email(email),
        self._validate_search_history(query_string, results_data)
    ))
    def add_search_history(self, email: str, query_string: str, results_data: dict) -> bool:
        """
        Log a user's search query and its results.

        Args:
            email: User's email.
            query_string: The search query.
            results_data: Metadata about the search results.

        Returns:
            bool: True if saved successfully, False otherwise.

        Raises:
            ValidationError: If inputs are invalid
            DatabaseOperationError: On database errors
        """
        try:
            # Get the user using the UserStore
            user = self.user_store.get_or_create_user(email)
            session = self._get_session()

            with self.transaction():
                new_search = SearchHistory(
                    user_id=user.id,
                    query=query_string,
                    results=results_data,
                    created_at=datetime.now(timezone.utc)
                )
                session.add(new_search)
                # Flush to catch any database errors early
                session.flush()

            logger.info(f"Search history added for user: {email}")
            return True
        except SQLAlchemyError as e:
            if self.db_session:
                self.db_session.rollback()
            error_msg = f"Database error adding search history for {email}: {e}"
            logger.error(error_msg)
            raise DatabaseOperationError(error_msg) from e
        except Exception as e:
            if self.db_session:
                self.db_session.rollback()
            error_msg = f"Unexpected error adding search history for {email}: {e}"
            logger.error(error_msg)
            raise DatabaseOperationError(error_msg) from e

    @ensure_connection
    @validate_inputs(lambda self, email: self._validate_email(email))
    def get_search_history(self, email: str) -> List[Dict[str, Any]]:
        """
        Retrieve the search history for a user.

        Args:
            email: User's email.

        Returns:
            List[Dict[str, Any]]: List of search history records.

        Raises:
            ValidationError: If email format is invalid
        """
        try:
            session = self._get_session()

            # Get the user by email
            user = session.query(User).filter_by(email=email).first()
            if not user:
                return []

            history = (
                session.query(SearchHistory)
                .filter_by(user_id=user.id)
                .order_by(SearchHistory.created_at.desc())
                .all()
            )

            return [
                {
                    "id": record.id,
                    "query": record.query,
                    "results": record.results,
                    "created_at": record.created_at.isoformat() if record.created_at is not None else None
                }
                for record in history
            ]
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving search history for {email}: {e}", exc_info=True)
            return [] 