#!/usr/bin/env python
"""
seed_database.py

Script to seed the database with real legislation from LegiScan API.
This script includes a verification step to ensure the API analysis works properly.

Usage:
  python scripts/seed_database.py --start-date 2024-01-01 --jurisdictions US,TX --max-bills 100
"""

import os
import sys
import logging
import argparse
from datetime import datetime
import json
from pathlib import Path

# Add the parent directory to sys.path to allow imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

def check_api_keys():
    """Check if required API keys are configured."""
    required_keys = {
        "LEGISCAN_API_KEY": os.environ.get("LEGISCAN_API_KEY"),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY")
    }
    
    missing_keys = [key for key, value in required_keys.items() if not value]
    
    if missing_keys:
        logger.error("Missing required API keys: %s", ", ".join(missing_keys))
        logger.error("Please set these environment variables before running this script.")
        return False
        
    for key, value in required_keys.items():
        logger.info(f"{key} is set: {'Yes' if value else 'No'}")
        
    return True

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Seed the database with legislation data from LegiScan")
    parser.add_argument("--start-date", type=str, default="2025-01-01",
                       help="Start date for bills to include (YYYY-MM-DD)")
    parser.add_argument("--jurisdictions", type=str, default="US,TX",
                       help="Comma-separated list of jurisdictions to seed")
    parser.add_argument("--max-bills", type=int, default=50,
                       help="Maximum number of bills to add")
    parser.add_argument("--output", type=str, default="seed_results.json",
                       help="Output file for seeding results")
    parser.add_argument("--verification-only", action="store_true",
                       help="Only run the verification step without full seeding")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        
    # Check API keys
    if not check_api_keys():
        return 1
        
    # Parse jurisdictions
    jurisdictions = [j.strip() for j in args.jurisdictions.split(",")]
    
    try:
        # Import and initialize database
        from app.models import init_db
        db_session_factory = init_db()
        db_session = db_session_factory()
        
        logger.info("Database initialized successfully")
        
        # Run verification only if requested
        if args.verification_only:
            logger.info("Running verification step only")
            from app.scheduler.seeding import verify_analysis_pipeline, parse_start_date
            from app.legiscan_api import LegiScanAPI
            
            summary = {
                "start_date": args.start_date,
                "verification_success": False,
                "verification_errors": [],
                "errors": [],
            }
            
            start_datetime = parse_start_date(args.start_date)
            api = LegiScanAPI(db_session)
            
            verification_success = verify_analysis_pipeline(
                db_session, api, jurisdictions, start_datetime, summary
            )
            
            if verification_success:
                logger.info("Verification successful")
            else:
                logger.error("Verification failed")
                
            # Save results
            with open(args.output, "w") as f:
                json.dump(summary, f, indent=2, default=str)
                
            return 0 if verification_success else 1
        
        # Run full seeding
        logger.info("Starting seeding operation with the following parameters:")
        logger.info(f"  Start date: {args.start_date}")
        logger.info(f"  Jurisdictions: {jurisdictions}")
        logger.info(f"  Max bills: {args.max_bills}")
        
        # Import seed function directly
        from app.scheduler.seeding import seed_historical_data
        
        # Seed historical data
        result = seed_historical_data(
            db_session=db_session,
            start_date=args.start_date,
            target_jurisdictions=jurisdictions,
            max_bills=args.max_bills
        )
        
        # Save results to file
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
            
        # Summary
        logger.info("\n--- Seeding Summary ---")
        logger.info(f"Start date: {result['start_date']}")
        logger.info(f"Bills added: {result['bills_added']}")
        logger.info(f"Bills analyzed: {result['bills_analyzed']}")
        logger.info(f"Verification success: {result['verification_success']}")
        logger.info(f"Sessions processed: {len(result['sessions_processed'])}")
        
        if result['errors']:
            logger.warning(f"Errors: {len(result['errors'])}")
            for i, error in enumerate(result['errors'][:5]):
                logger.warning(f"  {i+1}. {error[:150]}...")
                
            if len(result['errors']) > 5:
                logger.warning(f"  ...and {len(result['errors'])-5} more errors (see {args.output})")
                
        logger.info(f"Full results saved to {args.output}")
        
        if not result.get("verification_success", False):
            logger.error("Verification step failed")
            return 1
            
        return 0
        
    except Exception as e:
        logger.exception(f"Error during seeding: {e}")
        return 1
    finally:
        # Close the database session
        try:
            db_session.close()
        except:
            pass
        
if __name__ == "__main__":
    sys.exit(main()) 