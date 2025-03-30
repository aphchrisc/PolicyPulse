"""
app/data/base_store.py

This module provides the base functionality for all data store classes,
including connection management, transaction handling, and decorators.
"""

import contextlib
import logging
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, TypeVar, cast, Callable, Union

from sqlalchemy.exc import OperationalError, SQLAlchemyError, IntegrityError
from sqlalchemy import text
from sqlalchemy.orm import Session

# Import models and DB initialization function
from app.models import init_db
from app.data.errors import ConnectionError, ValidationError, DatabaseOperationError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Type variable for decorators
F = TypeVar('F', bound=Callable[..., Any])


def ensure_connection(func: F) -> F:
    """
    Decorator that ensures a valid database connection before executing the method.
    Calls self.check_connection() at the beginning of each method.

    Args:
        func: The method to wrap

    Returns:
        The wrapped method that ensures connection before execution
    """
    def wrapper(self, *args, **kwargs):
        try:
            self.check_connection()
            return func(self, *args, **kwargs)
        except (OperationalError, ConnectionError) as e:
            logger.error("Connection error in %s: %s", func.__name__, e)
            # Try to reconnect one more time
            self.init_connection()
            # If we get here, connection succeeded, try function again
            return func(self, *args, **kwargs)
    return cast(F, wrapper)


def validate_inputs(validation_func: Callable) -> Callable[[F], F]:
    """
    Decorator factory that applies a validation function to inputs before 
    executing the method.

    Args:
        validation_func: Function that validates inputs

    Returns:
        Decorator that applies validation before method execution
    """
    def decorator(func: F) -> F:
        def wrapper(self, *args, **kwargs):
            try:
                # Apply validation
                validation_func(self, *args, **kwargs)
                return func(self, *args, **kwargs)
            except ValidationError as e:
                logger.error("Validation error in %s: %s", func.__name__, e)
                raise
        return cast(F, wrapper)
    return decorator


class BaseStore:
    """
    BaseStore provides common functionality for all data store classes,
    including database connection management and transaction context.
    """

    def __init__(self, max_retries: int = 3) -> None:
        """
        Initialize the BaseStore with a database session.

        Args:
            max_retries: Number of attempts to establish a connection.

        Raises:
            ValidationError: If max_retries is not a positive integer
            ConnectionError: If unable to establish a database connection after max_retries
        """
        if not isinstance(max_retries, int) or max_retries < 1:
            raise ValidationError("max_retries must be a positive integer")

        self.max_retries = max_retries
        self.db_session: Optional[Session] = None
        self.init_connection()

    def _get_session(self) -> Session:
        """Return the current session or raise an error if none exists."""
        if not self.db_session:
            logger.error("Database session is None")
            raise DatabaseOperationError("No database session available")
        return self.db_session
    
    def init_connection(self) -> None:
        """
        Public method to initialize the database connection.
        This method is safe to call from decorators.
        
        Raises:
            ConnectionError: If unable to establish a connection
        """
        self._init_db_connection()

    def _init_db_connection(self) -> None:
        """
        Create the database session using the init_db factory with retry logic.

        Raises:
            ConnectionError: If unable to establish a connection after max_retries
        """
        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            try:
                session_factory = init_db(max_retries=1)  # init_db may have its own retry logic
                self.db_session = session_factory()
                # Verify connection works by executing a simple query
                if self.db_session:
                    self.db_session.execute(text("SELECT 1"))
                logger.info("Database session established successfully.")
                return
            except OperationalError as e:
                attempt += 1
                last_error = e
                logger.warning(
                    "DB connection attempt %s/%s failed: %s", 
                    attempt, self.max_retries, last_error
                )
                if attempt < self.max_retries:
                    # Exponential backoff
                    sleep_time = 2 ** attempt
                    logger.info("Retrying in %s seconds...", sleep_time)
                    time.sleep(sleep_time)

        # If we reach here, all attempts failed
        error_msg = "Failed to connect to database after %s attempts: %s" % (self.max_retries, last_error)
        logger.error(error_msg)
        raise ConnectionError(error_msg)

    def check_connection(self) -> None:
        """
        Verify database connection is working, attempting to reconnect if needed.

        Raises:
            ConnectionError: If reconnection fails
        """
        try:
            # If session doesn't exist, attempt to establish one
            if not self.db_session:
                logger.warning("No database session exists, attempting to reconnect")
                self.init_connection()
                return
            
            # Try to ping the database with a simple query
            try:
                self.db_session.execute(text("SELECT 1")).fetchone()
            except Exception as e:
                logger.warning(f"Database connection check failed: {str(e)}")
                
                # Explicitly close and reestablish
                try:
                    self.db_session.close()
                except Exception as close_error:
                    logger.warning(f"Error closing old session: {str(close_error)}")
                
                self.db_session = None
                logger.info("Attempting to reestablish database connection")
                self.init_connection()
            
        except Exception as e:
            logger.error(f"Connection check failed with error: {str(e)}")
            self.db_session = None
            raise ConnectionError(f"Database connection verification failed: {str(e)}")
        
    def _ensure_connection(self) -> None:
        """
        Private method that ensures a database connection is established.
        May be called from anywhere within the store.

        Raises:
            ConnectionError: If unable to establish a connection
        """
        if not self.db_session:
            logger.warning("No active database session, initializing connection")
            self.init_connection()
            if not self.db_session:
                raise ConnectionError("Unable to establish database connection")

    def transaction(self):
        """
        Provides a transaction context manager to wrap database operations.

        Usage:
            with self.transaction():
                # do database operations

        Returns:
            SQLAlchemy transaction context manager

        Raises:
            ConnectionError: If no database session is available
        """
        if not self.db_session:
            error_msg = "Cannot start transaction: No database session available"
            logger.error(error_msg)
            raise ConnectionError(error_msg)

        return self.db_session.begin()  # SQLAlchemy's built-in transactional context

    def close(self) -> None:
        """
        Close the database session to free resources.
        """
        if self.db_session:
            try:
                self.db_session.close()
                self.db_session = None
                logger.info("Database session closed.")
            except Exception as e:
                logger.error("Error closing database session: %s", e)
                # Reset the session to None even if close fails
                self.db_session = None

    def __enter__(self) -> "BaseStore":
        """
        Support context manager usage.

        Returns:
            This BaseStore instance
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Ensure the database session is closed on exit.

        Args:
            exc_type: Exception type if an exception was raised
            exc_value: Exception value if an exception was raised
            traceback: Traceback if an exception was raised
        """
        self.close()
        
    # Common validation functions
    def _validate_email(self, email: str) -> None:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Raises:
            ValidationError: If email format is invalid
        """
        if not email or not isinstance(email, str):
            raise ValidationError("Email cannot be empty and must be a string")

        # Basic email validation using regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format: %s" % email)
            
    def _validate_pagination_params(self, limit: int, offset: int) -> None:
        """
        Validate pagination parameters.

        Args:
            limit: Maximum records to return
            offset: Number of records to skip

        Raises:
            ValidationError: If parameters are invalid
        """
        if not isinstance(limit, int) or limit < 0:
            raise ValidationError("Limit must be a non-negative integer, got %s: %s" % (type(limit).__name__, limit))

        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("Offset must be a non-negative integer, got %s: %s" % (type(offset).__name__, offset))

        if limit > 1000:  # Prevent excessive queries
            raise ValidationError("Limit cannot exceed 1000, got %s" % limit)
            
    def _is_valid_date_format(self, date_str: str) -> bool:
        """
        Check if a string is in a valid date format (YYYY-MM-DD).

        Args:
            date_str: Date string to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False 