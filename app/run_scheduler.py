#!/usr/bin/env python3
"""
run_scheduler.py

Main entry point for running the PolicyPulse scheduler in standalone mode.
"""

import sys
import time
import signal
import logging
import argparse
from datetime import datetime

from app.scheduler import scheduler, handle_signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log')
    ]
)

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run PolicyPulse scheduler')
    parser.add_argument('--seed', action='store_true', help='Run historical data seeding')
    parser.add_argument('--sync', action='store_true', help='Run manual sync')
    parser.add_argument('--analyze', type=int, help='Run analysis for specific legislation ID')
    parser.add_argument('--date', type=str, default="2025-01-01",
                      help='Start date for seeding (YYYY-MM-DD)')
    
    return parser.parse_args()


def main():
    """Main entry point for scheduler."""
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    args = parse_arguments()
    
    # Run specific operations if requested
    if args.seed:
        start_date = args.date
        logger.info(f"Running historical data seeding from {start_date}...")
        result = scheduler.run_historical_seeding(start_date)
        logger.info(f"Seeding completed: {result}")
        return
        
    if args.sync:
        logger.info("Running manual sync...")
        result = scheduler.run_manual_sync()
        logger.info(f"Manual sync completed: {result}")
        return
        
    if args.analyze is not None:
        logger.info(f"Running analysis for legislation ID {args.analyze}...")
        result = scheduler.run_on_demand_analysis(args.analyze)
        logger.info(f"Analysis completed: {result}")
        return
    
    logger.info("Starting PolicyPulse scheduler in continuous mode...")
    
    # Start scheduler in continuous mode
    scheduler.start()
    
    # Keep main thread alive
    try:
        while scheduler.is_running:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if scheduler.is_running:
            scheduler.stop()
    
    logger.info("PolicyPulse scheduler shutdown complete")


if __name__ == "__main__":
    main() 