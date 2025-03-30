"""
User Routes

This module contains endpoints for user management, preferences, and search history.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from app.data.data_store import DataStore
from app.models.user_models import User, UserPreference
from app.api.models import (
    UserCreate, 
    UserResponse, 
    UserPreferencesUpdate, 
    UserPreferencesResponse,
    UserPrefsPayload,
    UserSearchPayload,
    SearchHistoryResponse
)
from app.api.dependencies import get_data_store
from app.api.utils import log_api_call
from app.api.error_handlers import error_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/users")

# -----------------------------------------------------------------------------
# User endpoints
# -----------------------------------------------------------------------------
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: DataStore = Depends(get_data_store)):
    """
    Create a new user with default preferences.
    
    Args:
        user: User creation data
        db: DataStore dependency for database access
        
    Returns:
        Created user information
        
    Raises:
        HTTPException: If username or email already exists or database error occurs
    """
    # Check if db or db_session is None
    if db is None or db.db_session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    
    # Check if user is None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User data is required"
        )
    
    db_user = db.db_session.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = db.db_session.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # In a real app, you would hash the password here
    db_user = User(
        username=user.username,
        email=user.email,
        password=user.password  # This should be hashed in production
    )
    db.db_session.add(db_user)
    db.db_session.commit()
    db.db_session.refresh(db_user)
    
    # Create default user preferences
    default_preferences = UserPreference(
        user_id=db_user.id,
        notification_enabled=True,
        theme="light",
        default_state="CA"
    )
    db.db_session.add(default_preferences)
    db.db_session.commit()
    
    return db_user

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: DataStore = Depends(get_data_store)):
    """
    Get user information by ID.
    
    Args:
        user_id: User ID
        db: DataStore dependency for database access
        
    Returns:
        User information
        
    Raises:
        HTTPException: If user not found
    """
    # Check if db or db_session is None
    if db is None or db.db_session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
        
    db_user = db.db_session.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/{user_id}/preferences", response_model=UserPreferencesResponse)
def get_user_preferences(user_id: int, db: DataStore = Depends(get_data_store)):
    """
    Get user preferences by user ID.
    
    Args:
        user_id: User ID
        db: DataStore dependency for database access
        
    Returns:
        User preferences
        
    Raises:
        HTTPException: If user preferences not found or database error occurs
    """
    # Check if db or db_session is None
    if db is None or db.db_session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
        
    db_preferences = db.db_session.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if db_preferences is None:
        raise HTTPException(status_code=404, detail="User preferences not found")
    return db_preferences

@router.put("/{user_id}/preferences", response_model=UserPreferencesResponse)
def update_user_preferences(
    user_id: int,
    preferences: UserPreferencesUpdate,
    db: DataStore = Depends(get_data_store)
):
    """
    Update user preferences.
    
    Args:
        user_id: User ID
        preferences: Preferences data to update
        db: DataStore dependency for database access
        
    Returns:
        Updated user preferences
        
    Raises:
        HTTPException: If user preferences not found or database error occurs
    """
    # Check if db or db_session is None
    if db is None or db.db_session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
        
    # Check if preferences is None
    if preferences is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preferences data is required"
        )
        
    db_preferences = db.db_session.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if db_preferences is None:
        raise HTTPException(status_code=404, detail="User preferences not found")
    
    update_data = preferences.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_preferences, key, value)
    
    db.db_session.commit()
    db.db_session.refresh(db_preferences)
    return db_preferences

# -----------------------------------------------------------------------------
# User preferences endpoints
# -----------------------------------------------------------------------------
@router.post("/{email}/preferences", tags=["User"], response_model=dict)
@log_api_call
def update_user_preferences_by_email(
    email: str,
    prefs: UserPrefsPayload,
    store: DataStore = Depends(get_data_store)
):
    """
    Update or create user preferences for the given email.
    This includes keywords, health focus areas, local government focus areas,
    and regions of interest.

    Args:
        email: User's email address
        prefs: Preference data
        store: DataStore instance

    Returns:
        Status message

    Raises:
        HTTPException: If email is invalid or preferences cannot be saved
    """
    with error_handler("Update user preferences", {
        ValueError: status.HTTP_400_BAD_REQUEST,
        ConnectionError: status.HTTP_503_SERVICE_UNAVAILABLE,
        Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
    }):
        # Convert payload to dict for storage
        prefs_dict = prefs.model_dump(exclude_unset=True)

        # Save preferences
        if not (success := store.save_user_preferences(email, prefs_dict)):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update preferences."
            )
        else:
            return {
                "status": "success",
                "message": f"Preferences updated for {email}"
            }

@router.get("/{email}/preferences", tags=["User"], response_model=UserPreferencesResponse)
@log_api_call
def get_user_preferences_by_email(
    email: str,
    store: DataStore = Depends(get_data_store)
):
    """
    Retrieve user preferences for the given email, including focus areas
    and regions of interest.

    Args:
        email: User's email address
        store: DataStore instance

    Returns:
        User preferences

    Raises:
        HTTPException: If email is invalid
    """
    with error_handler("Get user preferences", {
        ValueError: status.HTTP_400_BAD_REQUEST
    }):
        prefs = store.get_user_preferences(email)
        return {"email": email, "preferences": prefs}

# -----------------------------------------------------------------------------
# Search history endpoints
# -----------------------------------------------------------------------------
@router.post("/{email}/search", tags=["Search"], response_model=dict)
@log_api_call
def add_search_history(
    email: str,
    payload: UserSearchPayload,
    store: DataStore = Depends(get_data_store)
):
    """
    Add search history item for a user.

    Args:
        email: User email address
        payload: Search query and results
        store: DataStore instance

    Returns:
        Status message

    Raises:
        HTTPException: If email is invalid or search history cannot be saved
    """
    with error_handler("Add search history", {
                ValueError: status.HTTP_400_BAD_REQUEST,
                Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
            }):
        # Check if payload is not None before accessing its attributes
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search payload is required."
            )

        if ok := store.add_search_history(
            email, payload.query, payload.results
        ):
            return {
                "status": "success", 
                "message": f"Search recorded for {email}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add search history."
            )

@router.get("/{email}/search", tags=["Search"], response_model=SearchHistoryResponse)
@log_api_call
def get_search_history(
    email: str,
    store: DataStore = Depends(get_data_store)
):
    """
    Retrieve search history for a user.

    Args:
        email: User email address
        store: DataStore instance

    Returns:
        Search history items

    Raises:
        HTTPException: If email is invalid
    """
    with error_handler("Get search history", {
        ValueError: status.HTTP_400_BAD_REQUEST
    }):
        history = store.get_search_history(email)
        return {"email": email, "history": history}