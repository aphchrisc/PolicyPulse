# models/sync_models.py

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, ForeignKey, Index, Enum
)
from sqlalchemy.orm import relationship, validates, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from .base import BaseModel
from .enums import SyncStatusEnum

class APICallLog(BaseModel):
    """
    Logs API calls to external services like OpenAI or LegiScan.
    """
    __tablename__ = 'api_call_logs'

    id = Column(Integer, primary_key=True)
    service = Column(String(50), nullable=False)
    endpoint = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)

    tokens_used = Column(Integer, nullable=True)
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)

    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    cost_estimate = Column(Float, nullable=True)
    api_metadata = Column(JSONB, nullable=True)  # Renamed from 'metadata' to avoid conflict with SQLAlchemy

    __table_args__ = (
        Index('idx_api_logs_service', 'service'),
        Index('idx_api_logs_created', 'created_at'),
    )

    @validates('service')
    def validate_service(self, key, value):
        if not value or not value.strip():
            raise ValueError("Service name cannot be empty")
        return value


class SyncMetadata(BaseModel):
    """
    Tracks synchronization metadata.
    """
    __tablename__ = 'sync_metadata'

    id: Mapped[int] = mapped_column(primary_key=True)
    last_sync: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow())
    last_successful_sync: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[SyncStatusEnum] = mapped_column(Enum(SyncStatusEnum), nullable=False, default=SyncStatusEnum.pending)
    sync_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_bills: Mapped[int] = mapped_column(Integer, default=0)
    bills_updated: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    sync_errors: Mapped[List["SyncError"]] = relationship("SyncError", back_populates="sync_metadata")


class SyncError(BaseModel):
    """
    Logs errors encountered during synchronization operations.
    """
    __tablename__ = 'sync_errors'

    id = Column(Integer, primary_key=True)
    sync_id = Column(Integer, ForeignKey('sync_metadata.id'), nullable=False)
    error_type = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    error_time = Column(DateTime, default=datetime.utcnow(), nullable=False)

    sync_metadata = relationship("SyncMetadata", back_populates="sync_errors")
