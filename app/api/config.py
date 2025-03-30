"""
Configuration settings for the FastAPI application
"""

import os
from pydantic import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # API configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PolicyPulse API"
    DEBUG: bool = os.getenv("DEBUG", "").lower() in ("true", "1", "t")
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Response settings
    RESPONSE_CHUNK_SIZE: int = 1024  # Send large responses in chunks
    COMPRESS_RESPONSES: bool = True   # Enable Gzip/deflate compression
    MAX_RESPONSE_SIZE: int = 10 * 1024 * 1024  # 10MB max response size
    
    # Database settings
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    # External API keys
    LEGISCAN_API_KEY: Optional[str] = os.getenv("LEGISCAN_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings() 