#!/usr/bin/env python
"""
list_legislation.py

Script to list legislation in the database.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add parent directory to path to make app imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def get_db_url():
    """Get database URL from environment variables."""
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "postgres")
    dbname = os.environ.get("DB_NAME", "policypulse")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def list_legislation():
    """List legislation in the database."""
    try:
        # Create database connection
        engine = create_engine(get_db_url())
        
        # Query legislation
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, bill_number, title FROM legislation LIMIT 10"))
            
            # Print results
            print("Legislation in the database:")
            print("----------------------------")
            for row in result:
                print(f"ID: {row[0]}, Bill: {row[1]}, Title: {row[2]}")
                
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(list_legislation())
