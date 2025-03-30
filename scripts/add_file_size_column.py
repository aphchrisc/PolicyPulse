#!/usr/bin/env python3
"""
Migration script to add the file_size column to the legislation_text table.
This script should be run to fix the database schema mismatch.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_url():
    """Get the database URL from environment variables."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    return db_url

def add_file_size_column():
    """Add the file_size column to the legislation_text table."""
    db_url = get_db_url()
    
    try:
        # Create engine
        engine = create_engine(db_url)
        
        # Check if the column already exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'legislation_text' AND column_name = 'file_size'
            """))
            
            if result.fetchone():
                logger.info("file_size column already exists in legislation_text table")
                return
            
            # Add the column
            conn.execute(text("""
                ALTER TABLE legislation_text 
                ADD COLUMN file_size INTEGER
            """))
            
            # Commit the transaction
            conn.commit()
            
        logger.info("Successfully added file_size column to legislation_text table")
        
    except Exception as e:
        logger.error(f"Error adding file_size column: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting migration to add file_size column")
    add_file_size_column()
    logger.info("Migration completed successfully")