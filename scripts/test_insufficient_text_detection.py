#!/usr/bin/env python3
"""
Test script to verify the insufficient text detection feature.

This script loads a bill from a debug file, analyzes it, and checks if the
insufficient_text flag is set correctly in the response.

Usage:
    python scripts/test_insufficient_text_detection.py
"""

import os
import sys
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to make app imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

def get_db_url():
    """Get database URL from environment variables."""
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "postgres")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "policypulse")
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

def load_bill_data(file_path):
    """Load bill data from a debug file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading bill data: {e}")
        raise

        existing_bill = session.query(Legislation).filter_by(external_id=str(bill_data['bill_id'])).first()
        if existing_bill:
            session.delete(existing_bill)
            session.commit()
        # Always create a fresh test bill for deterministic testing
        
        # Create a test text record with minimal content to trigger the insufficient text detection
        analysis = analyzer.analyze_legislation(legislation_id=bill_id)
        
        # Check if the insufficient_text flag is set
        try:
            # Try to get the insufficient_text attribute
            insufficient_text = analysis.insufficient_text
            # Convert to Python primitive if needed
            if not isinstance(insufficient_text, bool):
                insufficient_text = bool(insufficient_text)
        except (AttributeError, TypeError):
            # Fallback if attribute doesn't exist or can't be converted
            insufficient_text = False
        
        if insufficient_text:
            logger.info("SUCCESS: Insufficient text flag is set correctly")
            result = True
        else:
            logger.warning("Insufficient text flag is not set. This could be because:")
            logger.warning("1. The bill text is sufficient for analysis")
            logger.warning("2. The implementation is not working correctly")
            logger.warning("3. The OpenAI model didn't return the expected marker")
            result = False
            logger.error("TEST FAILED: Insufficient text flag was not set as expected")
        
        # Print the analysis summary
        try:
            summary = str(analysis.summary) if hasattr(analysis, 'summary') else "No summary available"
            logger.info(f"Analysis summary: {summary}")
        except Exception as e:
            logger.warning(f"Could not get analysis summary: {e}")
        
def test_insufficient_text_detection():
    """Test the insufficient text detection feature."""
    # Load bill data
    bill_data = load_bill_data('debug_bill_TX_1891229.json')
    logger.info(f"Loaded bill data for {bill_data['bill_number']}")
    
    # Create database session
    db_url = get_db_url()
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Import required models and classes
        from app.models import Legislation, LegislationText
        from app.ai_analysis import AIAnalysis
        
        # First, delete any existing bill with the same external_id to avoid conflicts
        existing_bill = session.query(Legislation).filter_by(
            external_id=str(bill_data['bill_id'])
        ).first()
        
        if existing_bill:
            logger.info(f"Deleting existing bill with ID {existing_bill.id}")
            session.delete(existing_bill)
            session.commit()
        
        # Always create a fresh test bill for deterministic testing
        logger.info("Creating a test bill record")
        bill = Legislation(
            external_id=str(bill_data['bill_id']),
            data_source='LEGISCAN',
            govt_type='STATE',
            govt_source=bill_data['state'],
            bill_number=bill_data['bill_number'],
            title=bill_data['title'],
            description=bill_data.get('description', ''),
            url=bill_data.get('url', '')
        )
        session.add(bill)
        session.commit()
        
        # Create a test text record with minimal content to trigger the insufficient text detection
        logger.info("Creating a test text record with minimal content")
        text = LegislationText(
            legislation_id=bill.id,
            version_num=1,
            text_type='Introduced',
            text_content="HB408."  # Extremely short text that should trigger insufficient text detection
        )
        session.add(text)
        session.commit()
        
        # Create an AIAnalysis instance
        analyzer = AIAnalysis(db_session=session)
        
        # Run the analysis
        # Get the bill ID as a Python primitive using a query
        bill_id = session.query(Legislation.id).filter_by(id=bill.id).scalar()
        logger.info(f"Analyzing bill {bill_id}")
        analysis = analyzer.analyze_legislation(legislation_id=int(bill_id))
        
        # Check if the insufficient_text flag is set
        insufficient_text = getattr(analysis, 'insufficient_text', False)
        if not isinstance(insufficient_text, bool):
            insufficient_text = bool(insufficient_text)
        
        if insufficient_text:
            logger.info("SUCCESS: Insufficient text flag is set correctly")
            result = True
        else:
            logger.warning("Insufficient text flag is not set. This could be because:")
            logger.warning("1. The bill text is sufficient for analysis")
            logger.warning("2. The implementation is not working correctly")
            logger.warning("3. The OpenAI model didn't return the expected marker")
            result = False
            logger.error("TEST FAILED: Insufficient text flag was not set as expected")
        
        # Print the analysis summary
        summary = getattr(analysis, 'summary', "No summary available")
        logger.info(f"Analysis summary: {summary}")
        
        return result, analysis

    except Exception as e:
        logger.error(f"Error testing insufficient text detection: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    try:
        logger.info("Starting test for insufficient text detection")
        result, analysis = test_insufficient_text_detection()
        if result:
            logger.info("Test completed successfully")
        else:
            logger.error("Test completed but failed the assertion")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
