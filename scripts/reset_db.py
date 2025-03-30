#!/usr/bin/env python
"""
Database Reset Script

This script purges and reinitializes the PolicyPulse database with sample data.
Use this for development and testing purposes only.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import random

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the project root to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import required modules
    from sqlalchemy import create_engine, text
    from app.models.base import Base
    from app.models import (
        User, UserPreference, Legislation, LegislationText, LegislationAnalysis,
        LegislationSponsor, LegislationPriority, ImpactRating, ImplementationRequirement,
        DataSourceEnum, GovtTypeEnum, BillStatusEnum, ImpactCategoryEnum, ImpactLevelEnum
    )
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

def drop_all_tables(db_url):
    """Drop all tables in the database."""
    engine = create_engine(db_url)
    try:
        # Set a timeout for database operations
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Database operation timed out while dropping tables")
        
        # Set timeout to 30 seconds
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        logger.info("Dropping all tables...")
        Base.metadata.drop_all(engine)
        
        # Cancel the alarm
        signal.alarm(0)
        
        logger.info("All tables dropped successfully.")
        return True
    except TimeoutError as e:
        logger.error(f"Timeout error: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        return False

def create_sample_data(Session):
    """Create sample data for the database."""
    logger.info("Creating sample data...")
    
    session = Session()
    try:
        # Set a timeout for database operations
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Database operation timed out while creating sample data")
        
        # Set timeout to 60 seconds
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(60)
        
        # Create a test user
        user = User(
            email="test@example.com",
            name="Test User",
            created_at=datetime.now()
        )
        session.add(user)
        
        # Create user preferences
        preferences = UserPreference(
            user_id=1,
            preferences={
                "keywords": ["healthcare", "education", "infrastructure"],
                "notifications": {"email": True, "push": False},
                "dashboard_view": "summary"
            }
        )
        session.add(user)
        session.flush()  # Flush to get the user ID
        
        # Update with the correct user ID
        preferences.user_id = user.id
        session.add(preferences)
        
        # Create sample legislation
        statuses = [
            "introduced", "in_committee", "passed_committee", 
            "floor_vote", "passed", "enacted", "vetoed"
        ]
        
        govt_types = ["state", "federal", "local"]
        
        # Create 20 sample bills with different statuses
        for i in range(1, 21):
            status = random.choice(statuses)
            govt_type = random.choice(govt_types)
            
            # Create legislation record
            bill = Legislation(
                external_id=f"EXT-{i}",
                data_source="legiscan",
                govt_source="tx",
                govt_type=govt_type,
                bill_number=f"HB {1000 + i}",
                title=f"Sample Bill {i} for {random.choice(['Healthcare', 'Education', 'Infrastructure', 'Environment', 'Economy'])}",
                description=f"This is a sample bill description for bill {i}. It contains various policy details.",
                bill_status=status,
                url=f"https://example.com/bills/{i}",
                bill_introduced_date=datetime.now() - timedelta(days=random.randint(1, 90)),
                last_updated=datetime.now() - timedelta(days=random.randint(0, 30))
            )
            session.add(bill)
            session.flush()  # Flush to get the bill ID
            
            # Create bill text
            text = LegislationText(
                legislation_id=bill.id,
                version_num=1,
                text_type="introduced",
                content=f"Sample text content for bill {i}. This would normally be the full text of the bill.",
                url=f"https://example.com/bills/{i}/text",
                created_at=datetime.now() - timedelta(days=random.randint(1, 90))
            )
            session.add(text)
            
            # Create bill analysis
            analysis = LegislationAnalysis(
                legislation_id=bill.id,
                analysis_version=1,
                analysis_type="summary",
                content={
                    "summary": f"This is an AI-generated summary of bill {i}.",
                    "key_points": ["Point 1", "Point 2", "Point 3"],
                    "impact_areas": ["Public Health", "Local Government"]
                },
                created_at=datetime.now() - timedelta(days=random.randint(0, 30))
            )
            session.add(analysis)
            
            # Create sponsor
            sponsor = LegislationSponsor(
                legislation_id=bill.id,
                sponsor_name=f"Senator Smith {i}",
                sponsor_state=f"District {i}",
                sponsor_type="primary"
            )
            session.add(sponsor)
            
            # Create priority rating
            priority = LegislationPriority(
                legislation_id=bill.id,
                public_health_relevance=random.randint(1, 10) * 10,
                local_govt_relevance=random.randint(1, 10) * 10,
                overall_priority=random.randint(1, 10) * 10,
                auto_categorized=True
            )
            session.add(priority)
            
            # Create impact ratings
            for category in ["public_health", "local_govt", "economic"]:
                impact = ImpactRating(
                    legislation_id=bill.id,
                    category=category,
                    impact_level=random.choice(["low", "medium", "high"]),
                    explanation=f"This bill has {random.choice(['low', 'medium', 'high'])} impact on {category}.",
                    created_at=datetime.now() - timedelta(days=random.randint(0, 30))
                )
                session.add(impact)
            
            # Create implementation requirements
            req = ImplementationRequirement(
                legislation_id=bill.id,
                requirement_type="resource",
                description=f"Implementation requires additional resources for bill {i}.",
                estimated_cost=random.randint(10000, 1000000),
                created_at=datetime.now() - timedelta(days=random.randint(0, 30))
            )
            session.add(req)
            
            # Commit every 5 bills to avoid large transactions
            if i % 5 == 0:
                session.commit()
                logger.info(f"Committed batch of 5 bills (up to bill {i})")
        
        # Commit all remaining changes
        session.commit()
        
        # Cancel the alarm
        signal.alarm(0)
        
        logger.info("Sample data created successfully.")
        return True
    
    except TimeoutError as e:
        session.rollback()
        logger.error(f"Timeout error: {e}")
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create sample data: {e}")
        return False
    finally:
        session.close()

def main():
    """Main function to reset the database and create sample data."""
    logger.info("Starting database reset...")
    
    # Get database URL
    db_url = get_db_url()
    logger.info(f"Using database: {db_url.replace(os.environ.get('DB_PASSWORD', 'postgres'), '********')}")
    
    # Check database connection
    try:
        engine = create_engine(db_url)
        conn = engine.connect()
        conn.close()
        logger.info("Database connection test successful")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error("Please check that PostgreSQL is running and the database exists")
        return 1
    
    # Drop all tables
    if not drop_all_tables(db_url):
        logger.error("Failed to drop tables. Exiting.")
        return 1
    
    # Initialize database
    try:
        # Set a timeout for database operations
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Database operation timed out while initializing database")
        
        # Set timeout to 30 seconds
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        Session = init_db(db_url)
        
        # Cancel the alarm
        signal.alarm(0)
        
        logger.info("Database schema created successfully.")
    except TimeoutError as e:
        logger.error(f"Timeout error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return 1
    
    # Create sample data
    if not create_sample_data(Session):
        logger.error("Failed to create sample data. Exiting.")
        return 1
    
    logger.info("Database reset completed successfully!")
    return 0

if __name__ == "__main__":
    main()
