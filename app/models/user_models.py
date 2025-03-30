# models/user_models.py

import re
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import JSONB

from .base import BaseModel
from .enums import NotificationTypeEnum

# Notice we refer to Legislation by string in the relationship, to avoid import loops:
# "legislation.id" is the string reference for ForeignKey if needed.

class User(BaseModel):
    """
    Represents an application user.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default="user")  # e.g., user, admin

    preferences = relationship("UserPreference", back_populates="user",
                                uselist=False, cascade="all, delete-orphan")
    searches = relationship("SearchHistory", back_populates="user",
                             cascade="all, delete-orphan")
    alert_preferences = relationship("AlertPreference", back_populates="user",
                                      cascade="all, delete-orphan")
    alert_history = relationship("AlertHistory", back_populates="user",
                                  cascade="all, delete-orphan")

    @validates('email')
    def validate_email(self, key, address):
        if not isinstance(address, str):
            raise ValueError("Email must be a string")
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', address):
            raise ValueError(f"Invalid email format: {address}")
        return address


class UserPreference(BaseModel):
    """
    Stores user preferences such as keywords, focus areas, etc.
    """
    __tablename__ = 'user_preferences'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    keywords = Column(JSONB, nullable=True)
    health_focus = Column(JSONB, nullable=True)
    local_govt_focus = Column(JSONB, nullable=True)
    regions = Column(JSONB, nullable=True)

    default_view = Column(String(20), default="all")
    items_per_page = Column(Integer, default=25)
    sort_by = Column(String(20), default="updated_at")

    user = relationship("User", back_populates="preferences")

    @validates('items_per_page')
    def validate_items_per_page(self, key, value):
        if not isinstance(value, int) or value <= 0:
            raise ValueError("items_per_page must be a positive integer")
        return value


class SearchHistory(BaseModel):
    """
    Records user search queries and corresponding results.
    """
    __tablename__ = 'search_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    query = Column(String, nullable=True)
    filters = Column(JSONB, nullable=True)
    results = Column(JSONB, nullable=True)

    user = relationship("User", back_populates="searches")


class AlertPreference(BaseModel):
    """
    Stores alert preferences for a user.
    """
    __tablename__ = 'alert_preferences'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    email = Column(String(255), nullable=False)
    active = Column(Boolean, default=True)

    alert_channels = Column(JSONB, nullable=True)
    custom_keywords = Column(JSONB, nullable=True)
    ignore_list = Column(JSONB, nullable=True)
    alert_rules = Column(JSONB, nullable=True)

    health_threshold = Column(Integer, default=60)
    local_govt_threshold = Column(Integer, default=60)

    notify_on_new = Column(Boolean, default=False)
    notify_on_update = Column(Boolean, default=False)
    notify_on_analysis = Column(Boolean, default=True)

    user = relationship("User", back_populates="alert_preferences")

    @validates('health_threshold', 'local_govt_threshold')
    def validate_threshold(self, key, value):
        if not isinstance(value, int) or value < 0 or value > 100:
            raise ValueError(f"{key} must be an integer between 0 and 100")
        return value


class AlertHistory(BaseModel):
    """
    Logs the history of alerts sent to users.
    """
    __tablename__ = 'alert_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    legislation_id = Column(Integer, ForeignKey('legislation.id'), nullable=False)

    alert_type = Column(SQLEnum(NotificationTypeEnum), nullable=False)

    alert_content = Column(Text, nullable=True)
    delivery_status = Column(String(50), nullable=True)  # e.g., sent, error, pending
    error_message = Column(Text, nullable=True)

    user = relationship("User", back_populates="alert_history")
    legislation = relationship("Legislation", back_populates="alert_history")  # note the string reference in Legislation
