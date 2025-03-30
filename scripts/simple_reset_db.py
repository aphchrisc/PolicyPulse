#!/usr/bin/env python
"""
Simple Database Reset Script

This script uses direct SQL commands to reset the PolicyPulse database.
It's a simplified version that avoids potential hanging issues.
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
        "dbname": os.environ.get("DB_NAME", "policypulse")
    }

def execute_with_timeout(conn, cursor, sql, timeout=10):
    """Execute SQL with timeout protection."""
    import signal
    
    result = None
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"SQL operation timed out: {sql[:100]}...")
    
    try:
        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        # Execute SQL
        cursor.execute(sql)
        
        # Cancel alarm
        signal.alarm(0)
        
        return True
    except TimeoutError as e:
        logger.error(f"Timeout error: {e}")
        return False
    except Exception as e:
        logger.error(f"SQL error: {e}")
        return False

def reset_database():
    """Reset the database by dropping all tables and recreating schema."""
    db_params = get_db_params()
    logger.info(f"Connecting to database: {db_params['host']}:{db_params['port']}/{db_params['dbname']}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(**db_params)
        conn.autocommit = True  # Important to avoid transaction issues
        cursor = conn.cursor()
        logger.info("Connected to database successfully")
        
        # Get list of all tables
        logger.info("Getting list of tables...")
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        # Drop all tables
        if tables:
            logger.info("Dropping all tables...")
            
            # Disable foreign key checks temporarily
            execute_with_timeout(conn, cursor, "SET session_replication_role = 'replica';")
            
            for table in tables:
                logger.info(f"Dropping table: {table}")
                success = execute_with_timeout(
                    conn, cursor, f"DROP TABLE IF EXISTS {table} CASCADE;"
                )
                if not success:
                    logger.warning(f"Failed to drop table {table}, continuing anyway...")
            
            # Re-enable foreign key checks
            execute_with_timeout(conn, cursor, "SET session_replication_role = 'origin';")
            
            logger.info("All tables dropped successfully")
        else:
            logger.info("No tables found to drop")
        
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
    logger.info("Starting simple database reset...")
    
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
    if reset_database():
        logger.info("Database reset completed successfully!")
        logger.info("You can now run the init_db.py script to recreate the schema")
        return 0
    else:
        logger.error("Database reset failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
