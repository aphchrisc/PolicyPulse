#!/usr/bin/env python
"""
Force Database Reset Script

This script forcefully resets the database by:
1. Terminating all connections to the database
2. Dropping the database
3. Creating a new empty database
"""

import os
import sys
import logging
import psycopg2
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

def get_db_params():
    """Get database connection parameters from environment variables."""
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", "postgres"),
        "dbname": "postgres"  # Connect to default postgres database
    }

def get_target_db_name():
    """Get the target database name from environment variables."""
    return os.environ.get("DB_NAME", "policypulse")

def force_reset_database():
    """Force reset the database by dropping and recreating it."""
    db_params = get_db_params()
    target_db = get_target_db_name()
    
    logger.info(f"Connecting to postgres database to reset {target_db}")
    
    try:
        # Connect to postgres database (not the target database)
        conn = psycopg2.connect(**db_params)
        conn.autocommit = True  # Important to avoid transaction issues
        cursor = conn.cursor()
        logger.info("Connected to postgres database successfully")
        
        # Terminate all connections to the target database
        logger.info(f"Terminating all connections to {target_db}...")
        terminate_sql = f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{target_db}'
        AND pid <> pg_backend_pid();
        """
        cursor.execute(terminate_sql)
        logger.info("All connections terminated")
        
        # Drop the database if it exists
        logger.info(f"Dropping database {target_db} if it exists...")
        drop_sql = f"DROP DATABASE IF EXISTS {target_db};"
        cursor.execute(drop_sql)
        logger.info(f"Database {target_db} dropped")
        
        # Create a new database
        logger.info(f"Creating new database {target_db}...")
        create_sql = f"CREATE DATABASE {target_db};"
        cursor.execute(create_sql)
        logger.info(f"Database {target_db} created successfully")
        
        # Close connection
        cursor.close()
        conn.close()
        logger.info("Database reset completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False

def main():
    """Main entry point."""
    logger.info("Starting force database reset...")
    
    # Check if PostgreSQL is running
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        db_params = get_db_params()
        s.connect((db_params["host"], int(db_params["port"])))
        s.close()
        logger.info("PostgreSQL server is running")
    except Exception as e:
        logger.error(f"PostgreSQL server is not running: {e}")
        logger.error("Please start PostgreSQL and try again")
        return 1
    
    # Reset database
    if force_reset_database():
        logger.info("Database reset completed successfully!")
        logger.info("You can now run the init_db.py script to recreate the schema")
        return 0
    else:
        logger.error("Database reset failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
