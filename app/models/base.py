"""
Base models and utility classes for the application's database layer.

Provides SQLAlchemy base model, custom field types, and utility methods 
for content handling and type conversion.
"""

import logging
from typing import Union, Optional

from sqlalchemy import (
    Column, DateTime, String, func, Text, LargeBinary
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create the base class for declarative models
Base = declarative_base()

class BaseModel(Base):
    """
    Abstract base model that provides common audit fields for all inheriting models.
    """
    __abstract__ = True

    created_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)

    @staticmethod
    def _detect_content_type(data: bytes) -> str:
        """
        Detect the content type based on binary signatures.
        """
        if data.startswith(b'%PDF-'):
            return 'application/pdf'
        elif data.startswith(b'\xD0\xCF\x11\xE0'):
            return 'application/msword'
        elif data.startswith(b'PK\x03\x04'):
            return 'application/zip'
        return 'application/octet-stream'

    @staticmethod
    def set_content_field(obj, content: Union[str, bytes],
                           content_field: str,
                           is_binary_field: str,
                           metadata_field: Optional[str] = None) -> None:
        """
        Set a content field (text or binary) with optional metadata.
        """
        if content is None:
            setattr(obj, content_field, None)
            setattr(obj, is_binary_field, False)
            if metadata_field:
                setattr(obj, metadata_field, None)
        elif isinstance(content, str):
            setattr(obj, content_field, content)
            setattr(obj, is_binary_field, False)
            if metadata_field:
                content_bytes = content.encode('utf-8')
                metadata = {
                    "is_binary": False,
                    "encoding": "utf-8",
                    "size_bytes": len(content_bytes)
                }
                setattr(obj, metadata_field, metadata)
        elif isinstance(content, bytes):
            setattr(obj, content_field, content)
            setattr(obj, is_binary_field, True)
            if metadata_field:
                content_type = BaseModel._detect_content_type(content)
                metadata = {
                    "is_binary": True,
                    "content_type": content_type,
                    "size_bytes": len(content)
                }
                setattr(obj, metadata_field, metadata)
        else:
            raise TypeError(
                f"Content must be either string or bytes, not {type(content).__name__}"
            )


class FlexibleContentType(TypeDecorator):
    """
    A custom SQLAlchemy type to store both text and binary content.
    """
    impl = Text  # Default is Text for fallback
    cache_ok = True

    def __init__(self, binary_type=None, **kwargs):
        self.binary_type = binary_type or BYTEA
        super().__init__(**kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            # For PostgreSQL, use the binary type (BYTEA by default)
            # This allows storing both text and binary data
            return dialect.type_descriptor(self.binary_type())
        else:
            # For other dialects, use LargeBinary
            return dialect.type_descriptor(LargeBinary())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        
        # For PostgreSQL, always ensure binary data is properly handled
        if dialect.name == 'postgresql':
            # If value is a string, encode it to bytes for PostgreSQL BYTEA
            if isinstance(value, str):
                logger.debug("Converting string to bytes for PostgreSQL column")
                return value.encode('utf-8', errors='replace')
            # If value is already bytes, return it directly
            elif isinstance(value, bytes):
                return value
            # For any other type, convert to string then bytes
            else:
                return str(value).encode('utf-8', errors='replace')
        
        # For non-PostgreSQL databases
        if isinstance(value, str):
            return value
        elif isinstance(value, bytes):
            try:
                # Try to decode bytes to string for text columns
                return value.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                # If decoding fails, return as-is and let the database handle it
                return value
        else:
            # Convert other types to string
            return str(value)

    def process_result_value(self, value, dialect):
        # Just return the value as-is, whether it's text or binary
        # The application code will handle the appropriate type conversion
        return value
    
    def process_literal_param(self, value, dialect):
        """Process literal parameter values in compiled SQL statements."""
        # Handle SQL literals in the same way as bind parameters
        return self.process_bind_param(value, dialect)
    
    @property
    def python_type(self):
        """Return the Python type handled by this type decorator."""
        return Union[str, bytes]
