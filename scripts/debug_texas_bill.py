#!/usr/bin/env python3
"""
Script to debug the issue with saving Texas bills to the database.
This script:
1. Fetches a single Texas bill
2. Prints detailed information about the bill's text content
3. Attempts to save it to the database with extra debugging
"""

import os
import sys
import logging
import base64
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app modules
from app.legiscan_api import LegiScanAPI
from app.models.base import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_url():
    """Get the database URL from environment variables."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    return db_url

def debug_texas_bill():
    """Debug the issue with saving Texas bills to the database."""
    db_url = get_db_url()
    
    try:
        # Create engine and session
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create LegiScanAPI instance
        api_key = os.environ.get("LEGISCAN_API_KEY")
        if not api_key:
            logger.error("LEGISCAN_API_KEY environment variable not set")
            sys.exit(1)
        
        api = LegiScanAPI(session, api_key)
        
        # Get active Texas sessions
        logger.info("Getting active Texas sessions...")
        sessions = api.get_session_list("TX")
        if not sessions:
            logger.error("No Texas sessions found")
            sys.exit(1)
        
        # Get the most recent session
        active_sessions = [s for s in sessions if s.get("year_end", 0) >= datetime.now().year]
        if not active_sessions:
            logger.info("No active sessions found, using most recent session")
            session_id = sessions[0]["session_id"]
        else:
            session_id = active_sessions[0]["session_id"]
        
        logger.info(f"Using session ID: {session_id}")
        
        # Get the master bill list
        logger.info("Getting master bill list...")
        master_list = api.get_master_list(session_id)
        if not master_list:
            logger.error("No bills found in master list")
            sys.exit(1)
        
        # Get the first bill ID
        bill_ids = []
        for key, bill_info in master_list.items():
            if key != "0" and bill_info.get("bill_id"):  # Skip metadata
                bill_ids.append(bill_info.get("bill_id"))
                if len(bill_ids) >= 1:
                    break
        
        if not bill_ids:
            logger.error("No bill IDs found in master list")
            sys.exit(1)
        
        bill_id = bill_ids[0]
        logger.info(f"Using bill ID: {bill_id}")
        
        # Get the bill details
        logger.info(f"Getting details for bill ID: {bill_id}")
        bill_data = api.get_bill(bill_id)
        if not bill_data:
            logger.error(f"Failed to get bill data for bill ID: {bill_id}")
            sys.exit(1)
        
        # Print bill information
        logger.info(f"Bill number: {bill_data.get('bill_number')}")
        logger.info(f"Title: {bill_data.get('title')}")
        
        # Debug text content
        texts = bill_data.get("texts", [])
        logger.info(f"Number of text versions: {len(texts)}")
        
        for i, text_info in enumerate(texts):
            logger.info(f"Text version {i+1}:")
            logger.info(f"  Type: {text_info.get('type')}")
            logger.info(f"  Date: {text_info.get('date')}")
            
            # Check if doc_id is present
            doc_id = text_info.get("doc_id")
            logger.info(f"  Doc ID: {doc_id}")
            
            # Check if doc is present (base64 content)
            has_doc = "doc" in text_info and text_info["doc"]
            logger.info(f"  Has base64 content: {has_doc}")
            
            if has_doc:
                # Try to decode the base64 content
                try:
                    doc_base64 = text_info["doc"]
                    decoded_content = base64.b64decode(doc_base64)
                    
                    # Check if it's binary
                    is_binary = False
                    binary_signatures = [
                        b'%PDF-',  # PDF
                        b'\xD0\xCF\x11\xE0',  # MS Office
                        b'PK\x03\x04'  # ZIP (often used for DOCX, XLSX)
                    ]
                    
                    for sig in binary_signatures:
                        if decoded_content.startswith(sig):
                            is_binary = True
                            logger.info(f"  Content is binary ({sig})")
                            break
                    
                    if not is_binary:
                        # Try to decode as text
                        try:
                            text_content = decoded_content.decode("utf-8", errors="ignore")
                            logger.info(f"  Content is text (first 100 chars): {text_content[:100]}")
                        except Exception as e:
                            logger.error(f"  Error decoding content as text: {e}")
                    
                    logger.info(f"  Content size: {len(decoded_content)} bytes")
                    
                except Exception as e:
                    logger.error(f"  Error decoding base64 content: {e}")
            
            # If no base64 content, try to fetch using doc_id
            elif doc_id:
                logger.info(f"  Fetching content using doc_id: {doc_id}")
                try:
                    content = api.get_bill_text(doc_id)
                    if content:
                        is_binary = isinstance(content, bytes)
                        logger.info(f"  Content is binary: {is_binary}")
                        logger.info(f"  Content size: {len(content)} bytes")
                        
                        if not is_binary and isinstance(content, str):
                            logger.info(f"  Content is text (first 100 chars): {content[:100]}")
                    else:
                        logger.info("  No content returned from get_bill_text")
                except Exception as e:
                    logger.error(f"  Error fetching content: {e}")
        
        # Try to save the bill with extra debugging
        logger.info("Attempting to save bill to database...")
        try:
            # Monkey patch the _update_or_insert_text method to add extra debugging
            original_update_or_insert = api._update_or_insert_text
            
            def debug_update_or_insert(existing, attrs):
                logger.info("Debug _update_or_insert_text:")
                logger.info(f"  Existing: {existing is not None}")
                
                for k, v in attrs.items():
                    if k == 'text_content':
                        if v is None:
                            logger.info(f"  {k}: None")
                        elif isinstance(v, bytes):
                            logger.info(f"  {k}: bytes[{len(v)}]")
                        elif isinstance(v, str):
                            logger.info(f"  {k}: str[{len(v)}] (first 50 chars): {v[:50]}")
                        else:
                            logger.info(f"  {k}: {type(v)}")
                    elif k in ('text_metadata', 'is_binary', 'content_type', 'file_size'):
                        logger.info(f"  {k}: {v}")
                
                # Call the original method
                return original_update_or_insert(existing, attrs)
            
            # Replace the method
            api._update_or_insert_text = debug_update_or_insert
            
            # Try to save the bill
            bill_obj = api.save_bill_to_db(bill_data)
            if bill_obj:
                logger.info(f"Successfully saved bill {bill_obj.bill_number} to database")
            else:
                logger.error("Failed to save bill to database")
            
            # Restore the original method
            api._update_or_insert_text = original_update_or_insert
            
        except Exception as e:
            logger.error(f"Error saving bill to database: {e}", exc_info=True)
        
        # Close the session
        session.close()
        
    except Exception as e:
        logger.error(f"Error in debug_texas_bill: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting Texas bill debug")
    debug_texas_bill()
    logger.info("Debug completed")