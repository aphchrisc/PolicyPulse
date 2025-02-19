from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, ForeignKey, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import update
from sqlalchemy.orm import sessionmaker, relationship
import os
from datetime import datetime, timezone, timedelta
import time
import logging
from urllib.parse import urlparse, parse_qs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    searches = relationship("SearchHistory", back_populates="user")

class UserPreference(Base):
    __tablename__ = 'user_preferences'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    keywords = Column(JSON)  # Store keywords as JSON array
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    user = relationship("User", back_populates="preferences")

class SearchHistory(Base):
    __tablename__ = 'search_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    query = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    results = Column(JSON)  # Store search results as JSON
    user = relationship("User", back_populates="searches")

class LegislationTracker(Base):
    __tablename__ = 'legislation_tracker'

    id = Column(Integer, primary_key=True)
    congress = Column(Integer)
    bill_type = Column(String)
    bill_number = Column(String)
    title = Column(String)
    status = Column(String)
    introduced_date = Column(DateTime)
    public_health_impact = Column(String, default='unknown')  
    local_gov_impact = Column(String, default='unknown')      
    public_health_reasoning = Column(Text)  
    local_gov_reasoning = Column(Text)      

    # Law tracking fields
    law_number = Column(String)  
    law_type = Column(String)    
    law_enacted_date = Column(DateTime)
    law_description = Column(Text)
    progression_history = Column(JSON)  
    document_formats = Column(JSON)  # Store URLs for different formats (PDF, HTML, XML)

    first_stored_date = Column(DateTime, default=lambda: datetime.now(timezone.utc)) 
    last_api_check = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))      
    analysis_timestamp = Column(DateTime)                          

    raw_api_response = Column(JSON)  
    bill_text = Column(Text)         
    analysis = Column(JSON)          

    __table_args__ = (
        UniqueConstraint('congress', 'bill_type', 'bill_number', name='unique_bill_identifier'),
    )

def init_db(max_retries=3, initial_delay=1):
    """Initialize database connection with enhanced retry logic and SSL settings"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    # Add SSL mode and timeout settings to connection URL
    parsed_url = urlparse(database_url)
    query_params = parse_qs(parsed_url.query)

    # Add SSL mode if not present
    if 'sslmode' not in query_params:
        if '?' in database_url:
            database_url += '&sslmode=require'
        else:
            database_url += '?sslmode=require'

    retry_count = 0
    current_delay = initial_delay
    last_exception = None

    while retry_count < max_retries:
        try:
            logger.info(f"Attempting database connection (attempt {retry_count + 1}/{max_retries})")

            # Create engine with extended timeout and pool settings
            engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args={
                    'connect_timeout': 30,
                    'options': '-c statement_timeout=30000'
                }
            )

            # Test the connection using SQLAlchemy's text() function
            with engine.connect() as connection:
                from sqlalchemy import text
                connection.execute(text("SELECT 1"))
                connection.commit()

            logger.info("Database connection established successfully")
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            return Session()

        except Exception as e:
            last_exception = e
            logger.warning(f"Database connection attempt {retry_count + 1} failed: {str(e)}")
            logger.debug(f"Connection error details: {type(e).__name__}: {str(e)}")

            if retry_count < max_retries - 1:
                logger.info(f"Retrying in {current_delay} seconds...")
                time.sleep(current_delay)
                current_delay *= 2  # Exponential backoff

            retry_count += 1

    logger.error(f"Failed to connect to database after {max_retries} attempts")
    if last_exception is not None:
        raise last_exception
    else:
        raise Exception("Unknown error during database connection attempts")

class DataStore:
    def __init__(self):
        self.db_session = init_db()

    def flush_database(self):
        """Remove all records from the legislation tracker table"""
        try:
            self.db_session.query(LegislationTracker).delete()
            self.db_session.commit()
            logger.info("Database flushed successfully")
            return True
        except Exception as e:
            logger.error(f"Error flushing database: {e}")
            self.db_session.rollback()
            raise
    def get_unanalyzed_bills(self):
        """Get bills that haven't been analyzed by AI yet"""
        try:
            bills = self.db_session.query(LegislationTracker)\
                .filter(LegislationTracker.analysis.is_(None))\
                .all()
            return [
                {
                    'number': bill.bill_number,
                    'bill_text': bill.bill_text,
                    'congress': bill.congress,
                    'type': bill.bill_type
                }
                for bill in bills
            ]
        except Exception as e:
            logger.error(f"Error getting unanalyzed bills: {e}")
            return []

    def check_for_updates(self, days_threshold=1):
        """Check for updates on bills we haven't checked recently"""
        try:
            threshold = datetime.now(timezone.utc) - timedelta(days=days_threshold)

            # Get bills we haven't checked recently
            bills_to_check = self.db_session.query(LegislationTracker)\
                .filter(LegislationTracker.last_api_check < threshold)\
                .all()

            if not bills_to_check:
                return []  # No updates needed

            updated_bills = [bill for bill in bills_to_check]

            # Use bulk update to update all bills at once
            self.db_session.query(LegislationTracker)\
                .filter(LegislationTracker.id.in_([bill.id for bill in bills_to_check]))\
                .update({"last_api_check": datetime.now(timezone.utc)}, synchronize_session=False)

            self.db_session.commit()
            return updated_bills
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            self.db_session.rollback()
            return []
