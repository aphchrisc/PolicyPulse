#!/usr/bin/env python3
"""
Test script to verify the insufficient text detection feature with PDF files.

This script tests the insufficient text detection feature with PDF files,
which are common in legislative bills.

Usage:
    python scripts/test_pdf_insufficient_text.py
"""

import os
import sys
import json
import logging
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO

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

def download_pdf(url):
    """Download a PDF file from a URL."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        return None

def test_pdf_insufficient_text_detection():
    """Test the insufficient text detection feature with PDF files."""
    # Load bill data for HB706
    bill_data = load_bill_data('debug_bill_US_1939480.json')
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
        
        # Check if the bill exists in the database
        bill = session.query(Legislation).filter_by(
            external_id=str(bill_data['bill_id']),
            bill_number=bill_data['bill_number']
        ).first()
        
        if not bill:
            logger.info("Bill not found in database, creating a test record")
            # Create a test bill record
            bill = Legislation(
                external_id=str(bill_data['bill_id']),
                data_source='LEGISCAN',
                govt_type='FEDERAL',
                govt_source=bill_data['state'],
                bill_number=bill_data['bill_number'],
                title=bill_data['title'],
                description=bill_data['description'],
                url=bill_data['url']
            )
            session.add(bill)
            session.commit()
            
            # Try to download the PDF from the state_link
            pdf_content = None
            for text_entry in bill_data['texts']:
                if text_entry['mime'] == 'application/pdf':
                    logger.info(f"Downloading PDF from {text_entry['state_link']}")
                    pdf_content = download_pdf(text_entry['state_link'])
                    if pdf_content:
                        break
            
            # If we couldn't download the PDF, create a minimal PDF for testing
            if not pdf_content:
                logger.warning("Could not download PDF, creating a minimal PDF for testing")
                # Create a minimal PDF content (just the header)
                pdf_content = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000015 00000 n \n0000000060 00000 n \n0000000111 00000 n \ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n'
            
            # Create a test text record with the PDF content
            text = LegislationText(
                legislation_id=bill.id,
                version_num=1,
                text_type='Introduced',
                text_content=pdf_content,
                is_binary=True,
                content_type='application/pdf'
            )
            session.add(text)
            session.commit()
        
        # Create an AIAnalysis instance
        analyzer = AIAnalysis(db_session=session)
        
        # Run the analysis
        # Get the bill ID as a Python primitive
        try:
            bill_id = session.query(Legislation.id).filter_by(id=bill.id).scalar()
            if bill_id is None:
                bill_id = int(str(bill.id))
        except Exception:
            # Fallback to string conversion then int
            bill_id = int(str(bill.id))
            
        logger.info(f"Analyzing bill {bill_id}")
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
            logger.info("SUCCESS: Insufficient text flag is set correctly for PDF")
        else:
            logger.warning("Insufficient text flag is not set for PDF. This could be because:")
            logger.warning("1. The PDF content is sufficient for analysis")
            logger.warning("2. The implementation is not working correctly with PDFs")
            logger.warning("3. The OpenAI model didn't return the expected marker")
        
        # Print the analysis summary
        try:
            summary = str(analysis.summary) if hasattr(analysis, 'summary') else "No summary available"
            logger.info(f"Analysis summary: {summary}")
        except Exception as e:
            logger.warning(f"Could not get analysis summary: {e}")
        
        return analysis
    
    except Exception as e:
        logger.error(f"Error testing PDF insufficient text detection: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    try:
        logger.info("Starting test for PDF insufficient text detection")
        analysis = test_pdf_insufficient_text_detection()
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
