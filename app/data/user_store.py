"""
app/data/user_store.py

This module provides the UserStore class for managing user-related operations.
"""

import logging
from typing import Dict, Any, Optional, List

from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.models import User, UserPreference
from app.data.base_store import BaseStore, ensure_connection, validate_inputs
from app.data.errors import ValidationError, DatabaseOperationError

logger = logging.getLogger(__name__)


class UserStore(BaseStore):
    """
    UserStore handles all user-related database operations including
    user management and preferences.
    """

    def _validate_preferences(self, prefs: Dict[str, Any]) -> None:
        """
        Validate user preferences data structure.

        Args:
            prefs: User preferences dictionary

        Raises:
            ValidationError: If preferences format is invalid
        """
        if not isinstance(prefs, dict):
            raise ValidationError(f"Preferences must be a dictionary, got {type(prefs).__name__}")

        # Validate list-type fields
        list_fields = ['keywords', 'health_focus', 'local_govt_focus', 'regions']
        for field in list_fields:
            if field in prefs:
                if not isinstance(prefs[field], list):
                    raise ValidationError(f"{field} must be a list, got {type(prefs[field]).__name__}")

                # Validate list items
                for item in prefs[field]:
                    if not isinstance(item, str):
                        raise ValidationError(f"Items in {field} must be strings, got {type(item).__name__}")

    @ensure_connection
    def get_or_create_user(self, email: str) -> User:
        """
        Retrieve a user by email or create one if it does not exist.

        Args:
            email: User's email address.

        Returns:
            User: The existing or newly created user.

        Raises:
            ValidationError: If email format is invalid
            DatabaseOperationError: On database errors
        """
        # Validate email format
        self._validate_email(email)

        try:
            # Get the session directly and handle None case
            session = self._get_session()
            
            user = session.query(User).filter_by(email=email).first()
            if not user:
                # Start a transaction to create the user
                with self.transaction():
                    user = User(email=email)
                    session.add(user)
                    # Explicitly flush to get the ID and check for database errors
                    session.flush()
                logger.info(f"Created new user with email: {email}")
            return user
        except IntegrityError as e:
            # Could happen if another process created the user simultaneously
            session = self._get_session()  # Get session again in case it was lost
            session.rollback()
            logger.warning(f"Integrity error while creating user {email}, attempting to retrieve: {e}")
            # Try to retrieve again in case it was created by another process
            user = session.query(User).filter_by(email=email).first()
            if user:
                return user
            # If still not found, raise error
            raise DatabaseOperationError(
                f"Failed to create or retrieve user {email}: {e}"
            ) from e
        except SQLAlchemyError as e:
            if self.db_session:
                self.db_session.rollback()
            error_msg = f"Database error retrieving/creating user {email}: {e}"
            logger.error(error_msg)
            raise DatabaseOperationError(error_msg) from e

    @ensure_connection
    @validate_inputs(lambda self, email, new_prefs: (self._validate_email(email), self._validate_preferences(new_prefs)))
    def save_user_preferences(self, email: str, new_prefs: Dict[str, Any]) -> bool:
        """
        Create or update user preferences.

        Args:
            email: User's email.
            new_prefs: Preference settings.

        Returns:
            bool: True if successful, False otherwise.

        Raises:
            ValidationError: If inputs are invalid
            DatabaseOperationError: On database errors
        """
        try:
            # Get the user (creates one if doesn't exist)
            user = self.get_or_create_user(email)
            session = self._get_session()

            with self.transaction():
                if user.preferences:
                    # Update existing preferences
                    user_pref = user.preferences
                    if 'keywords' in new_prefs:
                        user_pref.keywords = new_prefs.get('keywords', [])
                    for field in ['health_focus', 'local_govt_focus', 'regions']:
                        if field in new_prefs:
                            setattr(user_pref, field, new_prefs.get(field, []))
                else:
                    # Create new preferences record
                    pref_data = {'user_id': user.id, 'keywords': new_prefs.get('keywords', [])}
                    for field in ['health_focus', 'local_govt_focus', 'regions']:
                        if field in new_prefs:
                            pref_data[field] = new_prefs.get(field, [])
                    user_pref = UserPreference(**pref_data)
                    session.add(user_pref)
                # Flush to catch any database errors
                session.flush()

            logger.info(f"Preferences saved for user: {email}")
            return True
        except SQLAlchemyError as e:
            if self.db_session:
                self.db_session.rollback()
            error_msg = f"Database error saving preferences for {email}: {e}"
            logger.error(error_msg)
            raise DatabaseOperationError(error_msg) from e
        except Exception as e:
            if self.db_session:
                self.db_session.rollback()
            error_msg = f"Unexpected error saving preferences for {email}: {e}"
            logger.error(error_msg)
            raise DatabaseOperationError(error_msg) from e

    @ensure_connection
    @validate_inputs(lambda self, email: self._validate_email(email))
    def get_user_preferences(self, email: str) -> Dict[str, Any]:
        """
        Retrieve preferences for a user.

        Args:
            email: User's email.

        Returns:
            Dict[str, Any]: User preferences or default values.

        Raises:
            ValidationError: If email format is invalid
        """
        try:
            session = self._get_session()
            
            user = session.query(User).filter_by(email=email).first()
            if user and user.preferences:
                prefs = {"keywords": user.preferences.keywords or []}
                for field in ['health_focus', 'local_govt_focus', 'regions']:
                    prefs[field] = getattr(user.preferences, field, []) or []
                return prefs
            return {"keywords": [], "health_focus": [], "local_govt_focus": [], "regions": []}
        except SQLAlchemyError as e:
            logger.error(f"Error loading preferences for {email}: {e}", exc_info=True)
            return {"keywords": [], "health_focus": [], "local_govt_focus": [], "regions": []} 