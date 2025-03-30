#!/usr/bin/env python
"""
Database Initialization Script

This script initializes the database schema for PolicyPulse.
Run this after force_reset_db.py to set up a fresh database.
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the project root to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import required modules
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import Base
    from app.models.db_init import init_db
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

def get_db_url():
    """Get database URL from environment variables."""
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "postgres")
    dbname = os.environ.get("DB_NAME", "policypulse")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def initialize_database():
    """Initialize the database schema."""
    db_url = get_db_url()
    logger.info(f"Using database: {db_url.replace(os.environ.get('DB_PASSWORD', 'postgres'), '********')}")
    
    try:
        # Create engine and initialize database
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        logger.info("Database schema created successfully")
        
        # Initialize database with session factory
        Session = sessionmaker(bind=engine)
        logger.info("Session factory created")
        
        return Session
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return None

def main():
    """Main entry point."""
    logger.info("Starting database initialization...")
    
    # Initialize database
    Session = initialize_database()
    if not Session:
        logger.error("Database initialization failed")
        return 1
    
    logger.info("Database initialization completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
