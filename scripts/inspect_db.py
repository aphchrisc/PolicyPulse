#!/usr/bin/env python
"""
Database Inspector Script

This script connects to the PolicyPulse database and displays information about
all tables and their contents to verify data integrity.
"""

import os
import sys
import json
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from tabulate import tabulate
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the project root to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_db_url():
    """Get database URL from environment variables."""
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "postgres")
    dbname = os.environ.get("DB_NAME", "policypulse")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def inspect_database():
    """Inspect the database and display information about tables and their contents."""
    db_url = get_db_url()
    logger.info(f"Connecting to database: {db_url.replace(os.environ.get('DB_PASSWORD', 'postgres'), '********')}")
    
    try:
        # Create engine and connect
        engine = create_engine(db_url)
        inspector = inspect(engine)
        connection = engine.connect()
        
        # Get all table names
        table_names = inspector.get_table_names()
        logger.info(f"Found {len(table_names)} tables in the database")
        
        # Display table information
        for table_name in table_names:
            logger.info(f"\n{'='*80}\nTable: {table_name}")
            
            # Get table columns
            columns = inspector.get_columns(table_name)
            column_info = [[col['name'], col['type'], col.get('nullable', True)] for col in columns]
            print("\nColumns:")
            print(tabulate(column_info, headers=["Column Name", "Data Type", "Nullable"]))
            
            # Get row count
            row_count = connection.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            print(f"\nRow Count: {row_count}")
            
            # Display sample data (up to 5 rows)
            if row_count > 0:
                sample_data = connection.execute(text(f"SELECT * FROM {table_name} LIMIT 5")).fetchall()
                if sample_data:
                    # Get column names for the table
                    column_names = [col['name'] for col in columns]
                    
                    # Convert sample data to list of dicts for better display
                    sample_data_dicts = []
                    for row in sample_data:
                        row_dict = {}
                        for i, col_name in enumerate(column_names):
                            value = row[i]
                            # Truncate long text values
                            if isinstance(value, str) and len(value) > 100:
                                value = value[:97] + "..."
                            # Format datetime objects
                            elif isinstance(value, datetime):
                                value = value.strftime("%Y-%m-%d %H:%M:%S")
                            row_dict[col_name] = value
                        sample_data_dicts.append(row_dict)
                    
                    print("\nSample Data:")
                    for i, row_dict in enumerate(sample_data_dicts):
                        print(f"\nRow {i+1}:")
                        for key, value in row_dict.items():
                            print(f"  {key}: {value}")
            
            # Display foreign keys
            foreign_keys = inspector.get_foreign_keys(table_name)
            if foreign_keys:
                fk_info = [[fk.get('constrained_columns'), fk.get('referred_table'), fk.get('referred_columns')] 
                          for fk in foreign_keys]
                print("\nForeign Keys:")
                print(tabulate(fk_info, headers=["Constrained Columns", "Referred Table", "Referred Columns"]))
            
            # Display indexes
            indexes = inspector.get_indexes(table_name)
            if indexes:
                idx_info = [[idx.get('name'), idx.get('column_names'), idx.get('unique', False)] 
                           for idx in indexes]
                print("\nIndexes:")
                print(tabulate(idx_info, headers=["Index Name", "Columns", "Unique"]))
            
            print("\n")
        
        # Close connection
        connection.close()
        logger.info("Database inspection completed successfully")
        
    except Exception as e:
        logger.error(f"Error inspecting database: {e}")
        return False
    
    return True

def main():
    """Main entry point."""
    logger.info("Starting database inspection...")
    
    # Check if PostgreSQL is running
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = os.environ.get("DB_HOST", "localhost")
        port = int(os.environ.get("DB_PORT", "5432"))
        s.connect((host, port))
        s.close()
        logger.info("PostgreSQL server is running")
    except Exception as e:
        logger.error(f"PostgreSQL server is not running: {e}")
        logger.error("Please start PostgreSQL and try again")
        return 1
    
    # Inspect database
    if inspect_database():
        logger.info("Database inspection completed successfully!")
        return 0
    else:
        logger.error("Database inspection failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
