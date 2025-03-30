"""
Configuration settings for the AI Analysis module.
"""

import os
import logging
from typing import Optional
from pydantic import BaseModel, field_validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')  # levelname is a standard logging placeholder
logger = logging.getLogger(__name__)


class AIAnalysisConfig(BaseModel):
    """Configuration parameters for the AIAnalysis class."""
    openai_api_key: Optional[str] = None
    model_name: str = "gpt-4o-2024-08-06"
    max_context_tokens: int = 120_000
    safety_buffer: int = 20_000
    max_retries: int = 3
    retry_base_delay: float = 1.0
    cache_ttl_minutes: int = 30
    log_level: str = "INFO"

    @field_validator('max_context_tokens')
    @classmethod
    def validate_max_context_tokens(cls, v):
        """
        Validate that max_context_tokens is within reasonable bounds.
        
        Args:
            v: The value to validate
            
        Returns:
            The validated value
            
        Raises:
            ValueError: If the value is outside acceptable range
        """
        if v < 1000:
            raise ValueError("max_context_tokens must be at least 1000")
        if v > 1_000_000:
            raise ValueError("max_context_tokens seems unreasonably high")
        return v

    @field_validator('safety_buffer')
    @classmethod
    def validate_safety_buffer(cls, v):
        """
        Validate that safety_buffer is non-negative.
        
        Args:
            v: The value to validate
            
        Returns:
            The validated value
            
        Raises:
            ValueError: If the value is negative
        """
        if v < 0:
            raise ValueError("safety_buffer cannot be negative")
        return v

    @field_validator('max_retries')
    @classmethod
    def validate_max_retries(cls, v):
        """
        Validate that max_retries is within reasonable bounds.
        
        Args:
            v: The value to validate
            
        Returns:
            The validated value
            
        Raises:
            ValueError: If the value is outside acceptable range
        """
        if v < 0:
            raise ValueError("max_retries cannot be negative")
        if v > 10:
            raise ValueError("max_retries seems unreasonably high")
        return v

    @field_validator('retry_base_delay')
    @classmethod
    def validate_retry_base_delay(cls, v):
        """
        Validate that retry_base_delay is positive and reasonable.
        
        Args:
            v: The value to validate
            
        Returns:
            The validated value
            
        Raises:
            ValueError: If the value is outside acceptable range
        """
        if v <= 0:
            raise ValueError("retry_base_delay must be positive")
        if v > 10:
            raise ValueError("retry_base_delay seems unreasonably high")
        return v

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """
        Validate that log_level is a valid logging level.
        
        Args:
            v: The value to validate
            
        Returns:
            The validated value
            
        Raises:
            ValueError: If the value is not a valid logging level
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(
                f"log_level must be one of: {', '.join(valid_levels)}")
        return v

    @field_validator('openai_api_key')
    @classmethod
    def validate_api_key(cls, v):
        """
        Validate that an OpenAI API key is available, either directly
        or from environment variables.
        
        Args:
            v: The API key value to validate
            
        Returns:
            The validated API key
            
        Raises:
            ValueError: If no API key is provided or available
        """
        # Check the environment variable if v is None
        if v is None and not os.environ.get("OPENAI_API_KEY"):
            raise ValueError(
                "OpenAI API key must be provided or set in OPENAI_API_KEY environment variable"
            )
        return v


# Set up logger level based on environment
def configure_logging(level_name="INFO"):
    """
    Configure logging level from string name.
    
    Args:
        level_name: String name of the logging level (e.g., "INFO", "DEBUG")
        
    Returns:
        Logger: Configured logger instance
    """
    level = getattr(logging, level_name)
    logger.setLevel(level)

    # Return logger for convenience
    return logger
