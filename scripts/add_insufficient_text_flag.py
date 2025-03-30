#!/usr/bin/env python3
"""
Script to add the insufficient_text column to the legislation_analysis table.

This script adds a boolean column 'insufficient_text' to the legislation_analysis table
to flag bills that don't have enough text for detailed analysis.

Usage:
    python scripts/add_insufficient_text_flag.py
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text, Column, Boolean
from sqlalchemy.exc import SQLAlchemyError

# Add parent directory to path to make app imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

def get_db_url():
    """Get database URL from environment variables."""
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "postgres")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "policypulse")
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

def add_insufficient_text_column():
    """Add the insufficient_text column to the legislation_analysis table."""
    db_url = get_db_url()
    engine = create_engine(db_url)
    
    try:
        # Check if column already exists
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'legislation_analysis' AND column_name = 'insufficient_text'"
            ))
            if result.fetchone():
                logger.info("Column 'insufficient_text' already exists in legislation_analysis table.")
                return
            
            # Add the column
            conn.execute(text(
                "ALTER TABLE legislation_analysis "
                "ADD COLUMN insufficient_text BOOLEAN DEFAULT FALSE"
            ))
            conn.commit()
            
            logger.info("Successfully added 'insufficient_text' column to legislation_analysis table.")
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    try:
        logger.info("Starting database migration to add insufficient_text column")
        add_insufficient_text_column()
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
