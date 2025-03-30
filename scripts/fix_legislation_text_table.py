#!/usr/bin/env python3
"""
Script to fix the legislation_text table to properly handle binary content.
This script:
1. Adds the file_size column if it doesn't exist
2. Modifies the text_content column to use BYTEA type for binary content
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

def fix_legislation_text_table():
    """Fix the legislation_text table to properly handle binary content."""
    db_url = get_db_url()
    
    try:
        # Create engine
        engine = create_engine(db_url)
        
        with engine.begin() as conn:
            # 1. Check if the file_size column exists, add it if it doesn't
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'legislation_text' AND column_name = 'file_size'
            """))
            
            if not result.fetchone():
                logger.info("Adding file_size column to legislation_text table")
                conn.execute(text("""
                    ALTER TABLE legislation_text 
                    ADD COLUMN file_size INTEGER
                """))
            else:
                logger.info("file_size column already exists in legislation_text table")
            
            # 2. Check if binary_content column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'legislation_text' AND column_name = 'binary_content'
            """))
            
            has_binary_content = bool(result.fetchone())
            
            # 3. Check the type of text_content column
            result = conn.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'legislation_text' AND column_name = 'text_content'
            """))
            
            text_content_type = result.scalar()
            logger.info(f"Current text_content column type: {text_content_type}")
            
            # 4. If text_content is not BYTEA, modify it
            if text_content_type != 'bytea':
                logger.info("Modifying text_content column to use BYTEA type")
                
                # If we have a binary_content column, we need to merge it with text_content
                if has_binary_content:
                    logger.info("Merging binary_content into text_content")
                    
                    # First, create a temporary column to hold the new BYTEA data
                    conn.execute(text("""
                        ALTER TABLE legislation_text 
                        ADD COLUMN temp_content BYTEA
                    """))
                    
                    # Copy text_content to temp_content for non-binary records
                    conn.execute(text("""
                        UPDATE legislation_text 
                        SET temp_content = text_content::bytea 
                        WHERE is_binary = FALSE OR is_binary IS NULL
                    """))
                    
                    # Copy binary_content to temp_content for binary records
                    conn.execute(text("""
                        UPDATE legislation_text 
                        SET temp_content = binary_content 
                        WHERE is_binary = TRUE AND binary_content IS NOT NULL
                    """))
                    
                    # Drop the text_content column
                    conn.execute(text("""
                        ALTER TABLE legislation_text 
                        DROP COLUMN text_content
                    """))
                    
                    # Rename temp_content to text_content
                    conn.execute(text("""
                        ALTER TABLE legislation_text 
                        RENAME COLUMN temp_content TO text_content
                    """))
                    
                    # Drop the binary_content column
                    conn.execute(text("""
                        ALTER TABLE legislation_text 
                        DROP COLUMN binary_content
                    """))
                else:
                    # Just alter the column type
                    conn.execute(text("""
                        ALTER TABLE legislation_text 
                        ALTER COLUMN text_content TYPE BYTEA USING text_content::bytea
                    """))
                
                logger.info("Successfully modified text_content column to BYTEA type")
            
            # 5. Make sure is_binary column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'legislation_text' AND column_name = 'is_binary'
            """))
            
            if not result.fetchone():
                logger.info("Adding is_binary column to legislation_text table")
                conn.execute(text("""
                    ALTER TABLE legislation_text 
                    ADD COLUMN is_binary BOOLEAN DEFAULT FALSE
                """))
            
            # 6. Make sure content_type column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'legislation_text' AND column_name = 'content_type'
            """))
            
            if not result.fetchone():
                logger.info("Adding content_type column to legislation_text table")
                conn.execute(text("""
                    ALTER TABLE legislation_text 
                    ADD COLUMN content_type VARCHAR(100)
                """))
            
            # 7. Make sure text_metadata column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'legislation_text' AND column_name = 'text_metadata'
            """))
            
            if not result.fetchone():
                logger.info("Adding text_metadata column to legislation_text table")
                conn.execute(text("""
                    ALTER TABLE legislation_text 
                    ADD COLUMN text_metadata JSONB
                """))
            
        logger.info("Successfully fixed legislation_text table")
        
    except Exception as e:
        logger.error(f"Error fixing legislation_text table: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting legislation_text table fix")
    fix_legislation_text_table()
    logger.info("Fix completed successfully")