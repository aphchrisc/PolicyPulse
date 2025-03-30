"""
API Package for PolicyPulse

This package provides the FastAPI application and routes for the PolicyPulse platform.
It's organized into modules by functionality to improve maintainability and readability.
"""

import logging
from fastapi import FastAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import the app instance from app.py
from .app import app

# This allows importing the app directly from app.api
__all__ = ['app']