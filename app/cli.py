#!/usr/bin/env python
"""
cli.py

Command-line interface for PolicyPulse administration tasks.
Provides tools for database seeding, syncing, analysis, and maintenance.

Usage:
  python cli.py seed [--start-date YYYY-MM-DD] [--jurisdiction US,TX]
  python cli.py sync [--force]
  python cli.py analyze <legislation_id>
  python cli.py analyze-pending [--limit N]
  python cli.py maintenance
  python cli.py stats
"""

import argparse
import logging
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy.sql.functions import count

from app.models import init_db, Legislation, LegislationAnalysis, SyncMetadata
from app.models import SyncError
from app.ai_analysis import AIAnalysis
from app.scheduler import PolicyPulseScheduler
from app.scheduler.sync_manager import LegislationSyncManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_resources():
    """Initialize database session and required resources."""
    db_session_factory = init_db()
    db_session = db_session_factory()
    return db_session, db_session_factory


def print_seeding_results(result):
    """
    Print the results of a seeding operation.
    
    Args:
        result (dict): Dictionary containing seeding operation results
    """
    print("\n=== Seeding Results ===")
    print(f"Start date: {result['start_date']}")
    print(f"Bills added: {result['bills_added']}")
    print(f"Bills analyzed: {result['bills_analyzed']}")
    print(f"Sessions processed: {len(result['sessions_processed'])}")
    
    if result['errors']:
        print(f"\nErrors: {len(result['errors'])}")
        for i, err in enumerate(result['errors'][:5]):
            print(f"  {i+1}. {err[:100]}...")
        
        if len(result['errors']) > 5:
            print(f"  ...and {len(result['errors'])-5} more errors")


def seed_command(args):
    """
    Seed the database with historical legislation.
    """
    logger.info("Starting seed operation from %s", args.start_date)
    
    db_session, db_session_factory = init_resources()
    sync_manager = LegislationSyncManager(db_session_factory)
    
    jurisdictions = [j.strip() for j in args.jurisdictions.split(',')]
    sync_manager.target_jurisdictions = jurisdictions
    
    try:
        result = sync_manager.seed_historical_data(args.start_date)
        print_seeding_results(result)
    finally:
        db_session.close()


def sync_command(args):
    """
    Trigger a sync operation.
    """
    logger.info("Starting %ssync operation", 'forced ' if args.force else '')
    
    db_session, _ = init_resources()
    scheduler: Any = PolicyPulseScheduler()
    
    try:
        result = scheduler.run_manual_sync()  # Using the correct method name
        print("\n=== Sync Results ===")
        print(f"Success: {result}")
    finally:
        db_session.close()


def analyze_command(args):
    """
    Analyze a specific legislation by ID.
    """
    logger.info("Starting analysis for legislation ID: %s", args.legislation_id)

    db_session, _ = init_resources()
    analyzer = AIAnalysis(db_session=db_session)

    try:
        # Check if legislation exists
        legislation = db_session.query(Legislation).filter_by(id=args.legislation_id).first()
        if not legislation:
            print(f"Error: Legislation ID {args.legislation_id} not found")
            return

        # Run analysis
        analysis = analyzer.analyze_legislation(legislation_id=args.legislation_id)

        print("\n=== Analysis Results ===")
        title_preview = (
            f"{legislation.title[:50]}..."
            if len(legislation.title) > 50
            else legislation.title
        )
        print(f"Legislation: {legislation.bill_number} - {title_preview}")
        print(f"Analysis ID: {analysis.id}")
        print(f"Version: {analysis.analysis_version}")
        print(f"Date: {analysis.analysis_date.isoformat()}")
        # Handle summary display safely
        summary_str = str(analysis.summary)
        summary_preview = (
            f"{summary_str[:150]}..."
            if len(summary_str) > 150
            else summary_str
        )
        print(f"Summary: {summary_preview}")
    except Exception as e:
        print(f"Error analyzing legislation: {e}")
    finally:
        db_session.close()


def analyze_pending_command(args):
    """
    Analyze pending (unanalyzed) legislation.
    """
    logger.info("Starting analysis for up to %s pending legislation", args.limit)

    db_session, _ = init_resources()
    analyzer = AIAnalysis(db_session=db_session)

    try:
        # Find legislation without analysis
        subquery = db_session.query(
            LegislationAnalysis.legislation_id
        ).distinct().subquery()

        # Get unanalyzed legislation, prioritizing more recent bills
        unanalyzed = db_session.query(Legislation).filter(
            ~Legislation.id.in_(subquery)
        ).order_by(Legislation.updated_at.desc()).limit(args.limit).all()

        if not unanalyzed:
            print("No pending legislation found for analysis")
            return

        print(f"Found {len(unanalyzed)} legislation without analysis, processing...")

        # Process each bill
        for i, leg in enumerate(unanalyzed):
            try:
                # Handle title display safely
                title_str = str(leg.title)
                title_preview = f"{title_str[:50]}..." if len(title_str) > 50 else title_str
                print(f"\n[{i+1}/{len(unanalyzed)}] Analyzing {leg.bill_number} - {title_preview}")
                analysis = analyzer.analyze_legislation(legislation_id=leg.id)
                print(f"  ✓ Analysis completed: version {analysis.analysis_version}")
            except Exception as e:
                print(f"  ✗ Error: {e}")
    finally:
        db_session.close()


def perform_database_maintenance(db_session):
    """
    Perform database maintenance tasks.
    
    Args:
        db_session: SQLAlchemy database session
        
    Returns:
        dict: Results of maintenance operations
    """
    print("Performing database maintenance...")
    
    # Example maintenance tasks
    
    # 1. Vacuum analyze (PostgreSQL)
    print("Running vacuum analyze...")
    db_session.execute("VACUUM ANALYZE")
    
    # 2. Clean up old sync errors
    print("Cleaning up old sync errors...")
    
    thirty_days_ago = datetime.now() - timedelta(days=30)
    count = db_session.query(SyncError).filter(
        SyncError.error_time < thirty_days_ago
    ).delete()
    db_session.commit()
    print(f"Removed {count} old sync error records")
    
    return {"removed_errors": count}


def maintenance_command(_):
    """
    Run database maintenance tasks.
    """
    logger.info("Starting database maintenance")
    
    db_session, _ = init_resources()
    
    try:
        perform_database_maintenance(db_session)
        print("\nMaintenance completed successfully")
    except Exception as e:
        print(f"Error during maintenance: {e}")
    finally:
        db_session.close()


def gather_system_statistics(db_session):
    """
    Gather various system statistics from the database.
    
    Args:
        db_session: SQLAlchemy database session
        
    Returns:
        dict: Dictionary containing various statistics
    """
    # Count legislation by state
    us_count = db_session.query(Legislation).filter(
        Legislation.govt_type == "federal"
    ).count()
    
    tx_count = db_session.query(Legislation).filter(
        Legislation.govt_source.ilike("%Texas%")
    ).count()
    
    # Count analyses
    analysis_count = db_session.query(LegislationAnalysis).count()
    
    # Get recent syncs
    recent_syncs = db_session.query(SyncMetadata).order_by(
        SyncMetadata.last_sync.desc()
    ).limit(3).all()
    
    # Get total bill count
    total_bills = db_session.query(Legislation).count()
    
    # Get bill statuses
    status_counts = db_session.query(
        Legislation.bill_status, count(Legislation.id).label('count')
    ).group_by(Legislation.bill_status).all()
    
    return {
        "total_bills": total_bills,
        "us_count": us_count,
        "tx_count": tx_count,
        "analysis_count": analysis_count,
        "status_counts": status_counts,
        "recent_syncs": recent_syncs
    }


def print_system_statistics(stats):
    """
    Print system statistics in a formatted way.
    
    Args:
        stats (dict): Dictionary containing system statistics
    """
    print("\n=== System Statistics ===")
    print(f"Total legislation in database: {stats['total_bills']}")
    print(f"US Federal bills: {stats['us_count']}")
    print(f"Texas bills: {stats['tx_count']}")
    print(f"Total analyses: {stats['analysis_count']}")
    
    print("\nBill status breakdown:")
    for status, count in stats['status_counts']:
        status_name = status.name if hasattr(status, 'name') else str(status)
        print(f"  {status_name}: {count}")
    
    print("\nRecent syncs:")
    for sync in stats['recent_syncs']:
        status = sync.status.name if hasattr(sync.status, 'name') else str(sync.status)
        print(f"  {sync.last_sync.strftime('%Y-%m-%d %H:%M:%S')} - {sync.sync_type} - {status}")
        print(f"    New bills: {sync.new_bills}, Updated: {sync.bills_updated}")


def stats_command(_):
    """
    Show system statistics.
    """
    logger.info("Gathering system statistics")
    
    db_session, _ = init_resources()
    
    try:
        stats = gather_system_statistics(db_session)
        print_system_statistics(stats)
    finally:
        db_session.close()


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='PolicyPulse Administration CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Seed command
    _seed_parser = subparsers.add_parser('seed', help='Seed database with historical legislation')
    _seed_parser.add_argument('--start-date', type=str, default="2023-01-01",
                              help='Start date in YYYY-MM-DD format (default: 2023-01-01)')
    _seed_parser.add_argument('--jurisdictions', type=str, default="US,TX",
                            help='Comma-separated jurisdictions to seed (default: US,TX)')
    
    # Sync command
    _sync_parser = subparsers.add_parser('sync', help='Trigger a sync operation')
    _sync_parser.add_argument('--force', action='store_true', help='Force sync even if recently run')
    
    # Analyze command
    _analyze_parser = subparsers.add_parser('analyze', help='Analyze a specific legislation')
    _analyze_parser.add_argument('legislation_id', type=int, help='Legislation ID to analyze')
    
    # Analyze pending command
    _analyze_pending_parser = subparsers.add_parser('analyze-pending', 
                                                help='Analyze pending (unanalyzed) legislation')
    _analyze_pending_parser.add_argument('--limit', type=int, default=10, 
                                      help='Maximum number of legislation to analyze (default: 10)')
    
    # Maintenance command
    _maintenance_parser = subparsers.add_parser('maintenance', help='Run database maintenance tasks')
    
    # Stats command
    _stats_parser = subparsers.add_parser('stats', help='Show system statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute the appropriate command
    if args.command == 'seed':
        seed_command(args)
    elif args.command == 'sync':
        sync_command(args)
    elif args.command == 'analyze':
        analyze_command(args)
    elif args.command == 'analyze-pending':
        analyze_pending_command(args)
    elif args.command == 'maintenance':
        maintenance_command(args)
    elif args.command == 'stats':
        stats_command(args)


if __name__ == '__main__':
    main()
