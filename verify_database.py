#!/usr/bin/env python
"""
Database Verification Script

Checks database connectivity and verifies if there's data in key tables.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_connection_string():
    """Get the database connection string from environment variables."""
    # For standard configuration
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    user = os.environ.get('DB_USER', 'postgres')
    password = os.environ.get('DB_PASSWORD', 'postgres')
    dbname = os.environ.get('DB_NAME', 'policypulse')

    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def verify_database():
    """Check database connectivity and verify if there's data in key tables."""
    try:
        # Create engine and connect
        engine = create_engine(get_connection_string())
        connection = engine.connect()
        logger.info("✅ Database connection successful")
        
        # Create a session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get all tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Found {len(tables)} tables in the database:")
        for table in tables:
            logger.info(f"  - {table}")
        
        # Check key tables for data
        key_tables = [
            'users', 
            'legislation', 
            'legislation_text', 
            'legislation_analysis',
            'sync_metadata'
        ]
        
        logger.info("\nChecking data in key tables:")
        for table in key_tables:
            if table in tables:
                result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                logger.info(f"  - {table}: {count} rows")
            else:
                logger.warning(f"  - {table}: Table does not exist")
        
        # Test a simple query
        logger.info("\nTesting a simple query:")
        user_query = "SELECT * FROM users LIMIT 5"
        result = connection.execute(text(user_query))
        users = result.fetchall()
        if users:
            logger.info(f"  ✅ Found {len(users)} users in the 'users' table")
            # Print user emails
            for user in users:
                logger.info(f"    - User ID: {user.id}, Email: {user.email}")
        else:
            logger.warning("  ❌ No users found in the 'users' table")
        
        logger.info("\n✅ Database verification complete")
        connection.close()
        session.close()
        return True
    
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function to run the database verification."""
    # Load environment variables
    load_dotenv()
    
    try:
        if verify_database():
            logger.info("Database verification completed successfully.")
            return 0
        else:
            logger.error("Database verification failed.")
            return 1
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 