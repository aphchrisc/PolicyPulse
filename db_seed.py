#!/usr/bin/env python
"""
db_seed.py

This script checks the database for existing data and seeds it with test data if needed.
"""

import os
import sys
import logging
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the app directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our models
from app.models.base import Base
from app.models.legislation import Legislation
from app.models.analysis import Analysis
from app.OLD.data_store import DataStore

def get_db_url():
    """Get the database URL from environment variables."""
    # For local development or explicit configuration
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    user = os.environ.get('DB_USER', 'postgres')
    password = os.environ.get('DB_PASSWORD', 'postgres')
    dbname = os.environ.get('DB_NAME', 'policypulse')
    
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def check_database():
    """Check if the database exists and has data."""
    try:
        # Create engine
        engine = create_engine(get_db_url())
        
        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Tables in database: {tables}")
        
        # Check if Legislation table exists and has data
        if 'legislation' in tables:
            count = session.query(Legislation).count()
            logger.info(f"Found {count} legislation records in the database")
            return count
        else:
            logger.warning("Legislation table does not exist")
            return 0
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
        return 0

def purge_database():
    """Purge all data from the database."""
    try:
        # Create engine
        engine = create_engine(get_db_url())
        
        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Delete all legislation records
        session.query(Legislation).delete()
        session.commit()
        
        # Delete all analysis records
        if hasattr(Analysis, '__tablename__'):
            session.query(Analysis).delete()
            session.commit()
        
        logger.info("Database purged successfully")
        return True
    except Exception as e:
        logger.error(f"Error purging database: {str(e)}")
        return False

def seed_database(num_bills=20):
    """Seed the database with test data."""
    try:
        # Create engine
        engine = create_engine(get_db_url())
        
        # Create tables if they don't exist
        Base.metadata.create_all(engine)
        
        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Generate test data
        bill_types = ["HB", "SB", "AB", "HR"]
        statuses = ["Active", "Passed", "Failed", "Pending"]
        impact_levels = ["high", "medium", "low"]
        impact_areas = [
            "Healthcare", "Education", "Environment", "Transportation", 
            "Housing", "Public Safety", "Economic Development", "Infrastructure",
            "Energy", "Agriculture", "Technology", "Labor"
        ]
        
        # Generate bills
        for i in range(num_bills):
            # Generate random bill data
            bill_type = random.choice(bill_types)
            bill_number = random.randint(100, 999)
            bill_title = f"{bill_type} {bill_number}"
            
            # Create a new bill
            bill = Legislation(
                bill_id=f"{bill_type}{bill_number}",
                title=f"{bill_title} - {''.join(random.sample(impact_areas, 1))} {'Act' if random.random() > 0.5 else 'Bill'}",
                description=f"A bill related to {''.join(random.sample(impact_areas, 1)).lower()} policy.",
                status=random.choice(statuses),
                introduced_date=datetime.now() - timedelta(days=random.randint(1, 60)),
                last_action_date=datetime.now() - timedelta(days=random.randint(0, 30)),
                url=f"https://legiscan.com/bill/{bill_type}{bill_number}",
                state="CA"
            )
            
            # Create analysis for the bill
            impact_level = random.choice(impact_levels)
            selected_areas = random.sample(impact_areas, random.randint(1, 3))
            
            # Create analysis object
            analysis = Analysis(
                legislation=bill,
                summary="This is a test summary for the bill.",
                impact_level=impact_level,
                impact_areas={area: {"score": random.randint(1, 10)} for area in selected_areas},
                recommendations="These are test recommendations for the bill."
            )
            
            # Add to session
            session.add(bill)
            session.add(analysis)
        
        # Commit the session
        session.commit()
        logger.info(f"Database seeded with {num_bills} bills")
        return True
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if we have data
    count = check_database()
    
    if count > 0:
        # Ask if we want to purge and reseed
        response = input(f"Found {count} bills in the database. Do you want to purge and reseed? (y/n): ")
        if response.lower() == 'y':
            if purge_database():
                seed_database()
        else:
            logger.info("Database already has data. Exiting.")
    else:
        # No data, seed the database
        logger.info("No data found in the database. Seeding...")
        seed_database()
