#!/usr/bin/env python3
"""
Migration script to update the database schema to match the SQLAlchemy models.
This script addresses the following issues:
1. Adds the missing file_size column to the legislation_text table
2. Creates the api_call_logs table if it doesn't exist
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text, Column, Integer, String, Text, DateTime, Float, MetaData, Table, ForeignKey

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

def update_legislation_text_table(conn):
    """Update the legislation_text table to match the SQLAlchemy model."""
    # Check if the file_size column already exists
    result = conn.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'legislation_text' AND column_name = 'file_size'
    """))
    
    if result.fetchone():
        logger.info("file_size column already exists in legislation_text table")
    else:
        # Add the file_size column
        conn.execute(text("""
            ALTER TABLE legislation_text
            ADD COLUMN file_size INTEGER
        """))
        logger.info("Successfully added file_size column to legislation_text table")
    
    # Check if we need to migrate binary_content to text_content
    # This is a complex operation that requires careful handling
    # We'll check if there are any rows with binary_content that need migration
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM legislation_text
        WHERE binary_content IS NOT NULL AND binary_content != ''
    """))
    
    binary_content_count = result.scalar()
    
    if binary_content_count > 0:
        logger.info(f"Found {binary_content_count} rows with binary_content that may need migration")
        logger.info("Note: Manual review recommended before migrating binary content to text_content")
        logger.info("The FlexibleContentType in the model handles both text and binary content")

def create_api_call_logs_table(conn):
    """Create the api_call_logs table if it doesn't exist."""
    # Check if the table already exists
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'api_call_logs'
    """))
    
    if result.fetchone():
        logger.info("api_call_logs table already exists")
        return
    
    # Create the table
    conn.execute(text("""
        CREATE TABLE api_call_logs (
            id SERIAL PRIMARY KEY,
            service VARCHAR(50) NOT NULL,
            endpoint VARCHAR(100),
            model VARCHAR(100),
            tokens_used INTEGER,
            tokens_input INTEGER,
            tokens_output INTEGER,
            status_code INTEGER,
            error_message TEXT,
            response_time_ms INTEGER,
            cost_estimate FLOAT,
            api_metadata JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_by VARCHAR(50),
            updated_by VARCHAR(50)
        )
    """))
    
    # Create indexes
    conn.execute(text("""
        CREATE INDEX idx_api_logs_service ON api_call_logs(service)
    """))
    
    conn.execute(text("""
        CREATE INDEX idx_api_logs_created ON api_call_logs(created_at)
    """))
    
    # Create update trigger
    conn.execute(text("""
        CREATE TRIGGER update_api_call_logs_modtime 
        BEFORE UPDATE ON api_call_logs 
        FOR EACH ROW EXECUTE FUNCTION update_modified_column()
    """))
    
    logger.info("Successfully created api_call_logs table with indexes and trigger")

def run_migrations():
    """Run all database migrations."""
    db_url = get_db_url()
    
    try:
        # Create engine
        engine = create_engine(db_url)
        
        # Run migrations in a transaction
        with engine.begin() as conn:
            update_legislation_text_table(conn)
            create_api_call_logs_table(conn)
            
        logger.info("All migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting database schema migration")
    run_migrations()
    logger.info("Migration completed")