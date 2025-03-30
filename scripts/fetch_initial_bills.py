#!/usr/bin/env python
"""
fetch_initial_bills.py

Script to fetch initial bills from LegiScan API and analyze them.
This script:
1. Fetches a set of bills from LegiScan (US Congress and Texas)
2. Saves them to the database
3. Runs AI analysis on them

Enhanced with:
- Better error handling and reporting
- Support for filtering by jurisdiction (US-only or TX-only)
- Dry-run mode for testing
- Option to retry failed analyses
- Support for custom models
- Detailed summary reporting
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, aliased
from sqlalchemy.sql import exists
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now we can import from app
from app.models import init_db, Legislation
from app.legiscan_api import LegiScanAPI
from app.ai_analysis import AIAnalysis, analyze_legislation

# Try to import LegislationAnalysis, but don't fail if it's not available
try:
    from app.models import LegislationAnalysis
    HAS_ANALYSIS_MODEL = True
except ImportError:
    HAS_ANALYSIS_MODEL = False
    LegislationAnalysis = None

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_url():
    """Get database URL from environment variables."""
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "postgres")
    dbname = os.environ.get("DB_NAME", "policypulse")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def fetch_bills_for_jurisdiction(api, state_code, limit, results, dry_run=False):
    """
    Fetch bills for a specific jurisdiction with improved error handling.
    
    Args:
        api: LegiScanAPI instance
        state_code: Two-letter state code
        limit: Maximum number of bills to fetch
        results: Dictionary to track results
        dry_run: If True, don't save to database
    
    Returns:
        List of fetched bills
    """
    fetched_bills = []

    try:
        # Get active sessions for this jurisdiction
        logger.info(f"Fetching sessions for {state_code}...")
        sessions = api.get_session_list(state_code)
        logger.info(f"Found {len(sessions)} sessions for {state_code}")
        
        if not sessions:
            logger.warning(f"No sessions found for {state_code}")
            return []

        # Use the most recent session
        session = sessions[0]
        session_id = session.get("session_id")
        logger.info(f"Using session {session_id} ({session.get('session_name', 'Unknown')})")

        if not session_id:
            logger.warning(f"No session ID found for {state_code}")
            return []

        # Get bill list for this session
        logger.info(f"Fetching master list for session {session_id}...")
        master_list = api.get_master_list(session_id)
        
        # Debug: Print the structure of master_list
        if master_list:
            logger.info(f"Master list has {len(master_list)} entries")
            if "0" in master_list:
                logger.info(f"Master list metadata: {master_list['0']}")
        else:
            logger.warning(f"No bills found for session {session_id}")
            return []

        # Get most recent bills (skipping metadata at key "0")
        bill_ids = []
        items = [(k, v) for k, v in master_list.items() if k != "0"]
        logger.info(f"Found {len(items)} bills in master list")

        # Sort by last action date (most recent first)
        sorted_items = sorted(
            items,
            key=lambda x: x[1].get("last_action_date", "1900-01-01"),
            reverse=True
        )
        
        # Take the top N bills
        logger.info(f"Taking top {limit} most recent bills")
        for i, (_, bill_info) in enumerate(sorted_items[:limit]):
            if bill_id := bill_info.get("bill_id"):
                bill_ids.append(bill_id)
                logger.info(f"Selected bill {i+1}: {bill_info.get('bill_number', 'Unknown')} (ID: {bill_id})")
        
        logger.info(f"Selected {len(bill_ids)} bills to fetch details for")

        # Fetch full bill details and save to database
        for bill_id in bill_ids:
            try:
                logger.info(f"Fetching details for bill ID {bill_id}...")
                bill_data = api.get_bill(bill_id)
                if not bill_data:
                    logger.warning(f"Failed to get bill data for bill_id={bill_id}")
                    continue
                
                logger.info(f"Got bill data: {bill_data.get('bill_number')} - {bill_data.get('title', '')[:50]}...")

                # Skip saving debug files to avoid potential issues
                logger.info("Skipping debug file save")

                if dry_run:
                    logger.info(f"DRY RUN: Would save bill {bill_data.get('bill_number')} to database")
                    # Create a mock bill object for tracking
                    bill_obj = type('MockBill', (), {
                        'id': bill_id,
                        'bill_number': bill_data.get('bill_number', 'Unknown'),
                        'title': bill_data.get('title', 'Unknown')
                    })
                    fetched_bills.append(bill_obj)
                    results["fetched"].append({
                        "bill_id": bill_id,
                        "bill_number": bill_data.get("bill_number"),
                        "state": bill_data.get("state")
                    })
                else:
                    # Set a timeout for the database operation
                    logger.info(f"Saving bill {bill_data.get('bill_number')} to database with timeout protection")
                    try:
                        # Use a timeout mechanism to prevent hanging
                        import signal
                        
                        def timeout_handler(signum, frame):
                            raise TimeoutError(f"Database operation timed out for bill {bill_id}")
                        
                        # Set timeout to 30 seconds
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(30)
                        
                        # Try to save to database with timeout protection
                        bill_obj = api.save_bill_to_db(bill_data, detect_relevance=True)
                        
                        # Cancel the alarm
                        signal.alarm(0)
                        
                        if bill_obj:
                            fetched_bills.append(bill_obj)
                            logger.info(f"Saved bill {bill_obj.bill_number} to database.")
                            results["fetched"].append({
                                "bill_id": bill_obj.id,
                                "bill_number": bill_obj.bill_number,
                                "state": bill_data.get("state")
                            })
                        else:
                            logger.warning(f"Failed to save bill {bill_data.get('bill_number')} to database")
                    except TimeoutError as e:
                        logger.error(f"Timeout while saving bill to database: {e}")
                        results["fetch_errors"].append({
                            "bill_id": bill_id,
                            "error": str(e)
                        })
                    except Exception as e:
                        logger.error(f"Error saving bill to database: {e}")
                        results["fetch_errors"].append({
                            "bill_id": bill_id,
                            "error": str(e)
                        })
            except Exception as e:
                logger.error(f"Error processing bill {bill_id}: {e}", exc_info=True)
                results["fetch_errors"].append({
                    "bill_id": bill_id,
                    "error": str(e)
                })

        return fetched_bills

    except Exception as e:
        logger.error(f"Error fetching bills for {state_code}: {e}", exc_info=True)
        results["fetch_errors"].append({
            "state": state_code,
            "error": str(e)
        })
        return []

def fetch_and_analyze_bills(limit=5, analyze=True, us_only=False, tx_only=False, 
                           retry_failed=False, dry_run=False, model=None):
    """
    Fetch and analyze bills with improved error handling and reporting.
    
    Args:
        limit: Maximum number of bills to fetch
        analyze: Whether to run AI analysis on the bills
        us_only: Only fetch US Congress bills
        tx_only: Only fetch Texas bills
        retry_failed: Retry previously failed analyses
        dry_run: Simulate without saving to database
        model: Specify AI model to use
    
    Returns:
        Dictionary with results and statistics
    """
    # Initialize tracking
    results = {
        "fetched": [],
        "fetch_errors": [],
        "analyzed": [],
        "analysis_errors": []
    }
    
    # Initialize database session
    db_session_factory = init_db()
    db_session = db_session_factory()
    
    try:
        # Initialize LegiScan API client
        api = LegiScanAPI(db_session)
        
        all_bills = []
        
        # Get some recent US Congress bills if not tx_only
        if not tx_only:
            logger.info("Fetching US Congress bills...")
            us_limit = limit if us_only else limit // 2
            us_bills = fetch_bills_for_jurisdiction(api, "US", us_limit, results, dry_run)
            all_bills.extend(us_bills)
        
        # Get some recent Texas bills if not us_only
        if not us_only:
            logger.info("Fetching Texas bills...")
            tx_limit = limit if tx_only else limit // 2
            tx_bills = fetch_bills_for_jurisdiction(api, "TX", tx_limit, results, dry_run)
            all_bills.extend(tx_bills)
        
        # Combine results
        logger.info(f"Fetched {len(all_bills)} bills in total.")
        
        # Run AI analysis if requested
        if analyze and all_bills:
            run_analysis(db_session, all_bills, results, model, dry_run)
        
        # If retry_failed is true, try to analyze bills that were saved but not analyzed
        if retry_failed and analyze and HAS_ANALYSIS_MODEL:
            retry_failed_analyses(db_session, results, model, dry_run)
            
        # Print summary
        print_summary(results)
            
        return all_bills
        
    except Exception as e:
        logger.error(f"Error fetching and analyzing bills: {e}", exc_info=True)
        results["fetch_errors"].append({"error": str(e), "bills": "all"})
        print_summary(results)
        return []
    finally:
        db_session.close()

def run_analysis(db_session, bills, results, model=None, dry_run=False):
    """
    Run AI analysis on a list of bills with improved tracking and error handling.
    
    Args:
        db_session: SQLAlchemy session
        bills: List of Legislation objects to analyze
        results: Dictionary to track results
        model: Optional model name to use for analysis
        dry_run: If True, don't save to database
    """
    logger.info(f"Running AI analysis on {len(bills)} bills...")
    
    try:
        # Initialize AI analysis
        analyzer = AIAnalysis(db_session)
        
        # Set model if specified
        if model:
            logger.info(f"Using custom model: {model}")
            analyzer.config.model_name = model
        
        total_bills = len(bills)
        for i, bill in enumerate(bills):
            try:
                logger.info(f"Analyzing bill {i+1}/{total_bills}: {bill.bill_number}")
                
                if dry_run:
                    logger.info(f"DRY RUN: Would analyze bill {bill.bill_number}")
                    results["analyzed"].append({
                        "bill_id": getattr(bill, 'id', 'unknown'),
                        "bill_number": bill.bill_number,
                        "status": "dry_run"
                    })
                    continue
                
                # Start timer for performance tracking
                start_time = time.time()
                
                # Add timeout protection for analysis
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Analysis timed out for bill {bill.bill_number}")
                
                # Set timeout to 60 seconds for analysis
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(60)
                
                try:
                    # Run the analysis - pass analyzer as the first argument
                    analysis = analyze_legislation(analyzer, bill.id)
                    
                    # Cancel the alarm
                    signal.alarm(0)
                    
                    # Calculate elapsed time
                    elapsed_time = time.time() - start_time
                    
                    logger.info(f"Analysis complete for {bill.bill_number}, version: {analysis.analysis_version} (took {elapsed_time:.2f}s)")
                    results["analyzed"].append({
                        "bill_id": bill.id,
                        "bill_number": bill.bill_number,
                        "analysis_id": analysis.id,
                        "analysis_version": analysis.analysis_version,
                        "elapsed_time": elapsed_time
                    })
                except TimeoutError as e:
                    logger.error(f"Analysis timed out for bill {bill.bill_number}: {e}")
                    results["analysis_errors"].append({
                        "bill_id": getattr(bill, 'id', 'unknown'),
                        "bill_number": bill.bill_number,
                        "error": str(e)
                    })
                    # Cancel the alarm in case of exception
                    signal.alarm(0)
                except Exception as e:
                    logger.error(f"Error during analysis for bill {bill.bill_number}: {e}", exc_info=True)
                    results["analysis_errors"].append({
                        "bill_id": getattr(bill, 'id', 'unknown'),
                        "bill_number": bill.bill_number,
                        "error": str(e)
                    })
                    # Cancel the alarm in case of exception
                    signal.alarm(0)
                
            except Exception as e:
                logger.error(f"Error analyzing bill {bill.bill_number}: {e}", exc_info=True)
                results["analysis_errors"].append({
                    "bill_id": getattr(bill, 'id', 'unknown'),
                    "bill_number": bill.bill_number,
                    "error": str(e)
                })
    except Exception as e:
        logger.error(f"Error initializing AI analysis: {e}", exc_info=True)
        results["analysis_errors"].append({"error": str(e), "bills": "all"})

def retry_failed_analyses(db_session, results, model=None, dry_run=False):
    """
    Retry analysis for bills that were saved but not analyzed.
    
    Args:
        db_session: SQLAlchemy session
        results: Dictionary to track results
        model: Optional model name to use for analysis
        dry_run: If True, don't save to database
    """
    if not HAS_ANALYSIS_MODEL:
        logger.warning("Cannot retry failed analyses: LegislationAnalysis model not available")
        return
        
    logger.info("Looking for bills that need analysis...")
    
    try:
        # Find bills that don't have any analysis
        LegislationAnalysis_alias = aliased(LegislationAnalysis)
        
        # Query for bills without analysis
        query = db_session.query(Legislation).filter(
            ~exists().where(LegislationAnalysis_alias.legislation_id == Legislation.id)
        )
        
        bills_without_analysis = query.all()
        
        if not bills_without_analysis:
            logger.info("No bills found that need analysis.")
            return
        
        logger.info(f"Found {len(bills_without_analysis)} bills that need analysis.")
        
        # Run analysis on these bills
        run_analysis(db_session, bills_without_analysis, results, model, dry_run)
        
    except Exception as e:
        logger.error(f"Error retrying failed analyses: {e}", exc_info=True)
        results["analysis_errors"].append({"error": str(e), "retry": "failed"})

def print_summary(results):
    """
    Print a summary of the fetch and analysis results.
    
    Args:
        results: Dictionary with tracking results
    """
    print("\n" + "="*80)
    print("SUMMARY OF BILL FETCH AND ANALYSIS")
    print("="*80)
    
    # Fetch summary
    print(f"\nFETCH RESULTS:")
    print(f"  Bills successfully fetched: {len(results['fetched'])}")
    print(f"  Fetch errors: {len(results['fetch_errors'])}")
    
    if results['fetched']:
        print("\n  Successfully fetched bills:")
        for i, bill in enumerate(results['fetched'][:10], 1):  # Show first 10
            print(f"    {i}. {bill.get('bill_number', 'Unknown')} ({bill.get('state', 'Unknown')})")
        if len(results['fetched']) > 10:
            print(f"    ... and {len(results['fetched']) - 10} more")
    
    if results['fetch_errors']:
        print("\n  Fetch errors:")
        for i, error in enumerate(results['fetch_errors'][:5], 1):  # Show first 5
            print(f"    {i}. Bill ID: {error.get('bill_id', 'Unknown')}, Error: {error.get('error', 'Unknown')}")
        if len(results['fetch_errors']) > 5:
            print(f"    ... and {len(results['fetch_errors']) - 5} more errors")
    
    # Analysis summary
    print(f"\nANALYSIS RESULTS:")
    print(f"  Bills successfully analyzed: {len(results['analyzed'])}")
    print(f"  Analysis errors: {len(results['analysis_errors'])}")
    
    if results['analyzed']:
        print("\n  Successfully analyzed bills:")
        for i, bill in enumerate(results['analyzed'][:10], 1):  # Show first 10
            elapsed = bill.get('elapsed_time', 'N/A')
            elapsed_str = f" (took {elapsed:.2f}s)" if isinstance(elapsed, (int, float)) else ""
            print(f"    {i}. {bill.get('bill_number', 'Unknown')}, version: {bill.get('analysis_version', 'Unknown')}{elapsed_str}")
        if len(results['analyzed']) > 10:
            print(f"    ... and {len(results['analyzed']) - 10} more")
    
    if results['analysis_errors']:
        print("\n  Analysis errors:")
        for i, error in enumerate(results['analysis_errors'][:5], 1):  # Show first 5
            print(f"    {i}. Bill: {error.get('bill_number', 'Unknown')}, Error: {error.get('error', 'Unknown')}")
        if len(results['analysis_errors']) > 5:
            print(f"    ... and {len(results['analysis_errors']) - 5} more errors")
    
    print("\n" + "="*80)

def save_results(results):
    """Save results to a JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"fetch_results_{timestamp}.json"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Results saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving results: {e}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Fetch initial bills from LegiScan API")
    parser.add_argument("--limit", type=int, default=10, help="Number of bills to fetch per jurisdiction")
    parser.add_argument("--jurisdictions", nargs="+", default=["US", "TX"], help="Jurisdictions to fetch bills for")
    parser.add_argument("--model", type=str, help="OpenAI model to use for analysis")
    parser.add_argument("--dry-run", action="store_true", help="Don't save to database")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip AI analysis")
    args = parser.parse_args()

    # Start timer for performance tracking
    start_time = time.time()
    
    # Initialize results tracking
    results = {
        "fetched": [],
        "fetch_errors": [],
        "analyzed": [],
        "analysis_errors": [],
        "stats": {
            "start_time": datetime.now().isoformat(),
            "jurisdictions": args.jurisdictions,
            "limit_per_jurisdiction": args.limit,
            "dry_run": args.dry_run
        }
    }
    
    logger.info(f"Starting fetch_initial_bills with limit={args.limit}, jurisdictions={args.jurisdictions}, dry_run={args.dry_run}")
    
    # Create database session
    try:
        engine = create_engine(get_db_url())
        Session = sessionmaker(bind=engine)
        db_session = Session()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}", exc_info=True)
        results["stats"]["error"] = f"Database connection failed: {str(e)}"
        save_results(results)
        return 1

    try:
        # Initialize LegiScan API
        api = LegiScanAPI(db_session)
        logger.info("LegiScan API initialized")
        
        # Fetch bills for each jurisdiction
        all_bills = []
        for jurisdiction in args.jurisdictions:
            logger.info(f"Processing jurisdiction: {jurisdiction}")
            jurisdiction_bills = fetch_bills_for_jurisdiction(
                api, 
                jurisdiction, 
                args.limit, 
                results, 
                dry_run=args.dry_run
            )
            all_bills.extend(jurisdiction_bills)
            logger.info(f"Fetched {len(jurisdiction_bills)} bills for {jurisdiction}")
        
        logger.info(f"Fetched {len(all_bills)} bills total across all jurisdictions")
        
        # Run analysis if requested
        if not args.skip_analysis and all_bills:
            logger.info(f"Running analysis on {len(all_bills)} bills")
            run_analysis(db_session, all_bills, results, model=args.model, dry_run=args.dry_run)
        elif args.skip_analysis:
            logger.info("Skipping analysis as requested")
        else:
            logger.info("No bills to analyze")
        
        # Commit session if not dry run
        if not args.dry_run:
            try:
                logger.info("Committing database session")
                db_session.commit()
                logger.info("Database session committed successfully")
            except Exception as e:
                logger.error(f"Error committing database session: {e}", exc_info=True)
                db_session.rollback()
                results["stats"]["error"] = f"Database commit failed: {str(e)}"
        else:
            logger.info("Dry run - not committing database changes")
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        results["stats"]["elapsed_time"] = elapsed_time
        results["stats"]["end_time"] = datetime.now().isoformat()
        
        logger.info(f"Script completed in {elapsed_time:.2f} seconds")
        logger.info(f"Fetched {len(results['fetched'])} bills, analyzed {len(results['analyzed'])} bills")
        logger.info(f"Errors: {len(results['fetch_errors'])} fetch errors, {len(results['analysis_errors'])} analysis errors")
        
        # Save results
        save_results(results)
        
        return 0
    
    except Exception as e:
        logger.error(f"Unhandled error in main: {e}", exc_info=True)
        results["stats"]["error"] = str(e)
        results["stats"]["end_time"] = datetime.now().isoformat()
        save_results(results)
        return 1
    finally:
        # Always close the session
        db_session.close()
        logger.info("Database session closed")

if __name__ == "__main__":
    main()
