"""
scheduler/__init__.py

PolicyPulse scheduler package for managing scheduled jobs for legislation sync and analysis.
"""

import sys
import signal
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.triggers.cron import CronTrigger

from app.models import init_db
from app.scheduler.sync_manager import LegislationSyncManager
from app.scheduler.jobs import nightly_sync_job, daily_maintenance_job, run_on_demand_analysis
from app.scheduler.errors import SyncError, DataSyncError, AnalysisError

logger = logging.getLogger(__name__)

# Re-export modules for a clean public API
__all__ = [
    'PolicyPulseScheduler',
    'scheduler',
    'handle_signal',
    'SyncError',
    'DataSyncError', 
    'AnalysisError',
    'LegislationSyncManager'
]


class PolicyPulseScheduler:
    """
    Manages scheduled jobs for PolicyPulse, including:
    - Nightly LegiScan sync at 10 PM, followed by immediate AI analysis
    - Historical data seeding (manual trigger)
    - Daily database maintenance
    """

    def __init__(self):
        """Initialize the scheduler with APScheduler."""
        self.scheduler = BackgroundScheduler(timezone=timezone.utc)
        # Initialize DB once for entire process
        self.db_session_factory = init_db()
        self.is_running = False
        # Create sync manager
        self.sync_manager = LegislationSyncManager(self.db_session_factory)
        
        # Store job functions
        self._nightly_sync_job_func = nightly_sync_job
        self._daily_maintenance_job_func = daily_maintenance_job
        self._run_on_demand_analysis_func = run_on_demand_analysis

    def _nightly_sync_job(self):
        """Run the nightly sync job."""
        return self._nightly_sync_job_func(self.sync_manager)

    def _daily_maintenance_job(self):
        """Run the daily maintenance job."""
        return self._daily_maintenance_job_func(self.db_session_factory)

    def _job_listener(self, event: Any) -> None:
        """
        Event listener for scheduled jobs.
        
        Args:
            event: Job execution event with job_id and optional exception
        """
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.info(f"Job {event.job_id} completed successfully")

    def start(self) -> bool:
        """
        Start the scheduler with configured jobs.
        
        Returns:
            True if scheduler started successfully, False otherwise
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return False

        try:
            return self._initialize_and_start_scheduler()
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)
            return False

    def _initialize_and_start_scheduler(self) -> bool:
        """
        Initialize and start the scheduler with configured jobs.
        
        Returns:
            True if scheduler started successfully, False otherwise
        """
        # Register event listener for job execution events
        self.scheduler.add_listener(self._job_listener,
                                    EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

        # Add the nightly sync job (runs at 10 PM UTC)
        self.scheduler.add_job(self._nightly_sync_job,
                              CronTrigger(hour=22, minute=0),
                              id='nightly_sync',
                              name='LegiScan Nightly Sync',
                              replace_existing=True)

        # Add daily maintenance job (runs at 4 AM UTC)
        self.scheduler.add_job(self._daily_maintenance_job,
                              CronTrigger(hour=4, minute=0),
                              id='daily_maintenance',
                              name='Daily Database Maintenance',
                              replace_existing=True)

        # Start the scheduler
        self.scheduler.start()
        self.is_running = True
        logger.info(
            "Scheduler started. Nightly sync scheduled for 10 PM UTC, maintenance for 4 AM UTC."
        )
        return True

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return

        try:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}", exc_info=True)

    def run_manual_sync(self) -> Dict[str, Any]:
        """
        Manually trigger a sync job.

        Returns:
            Dictionary with sync operation summary
        """
        logger.info("Starting manual sync job...")
        return self.sync_manager.run_nightly_sync()

    def run_historical_seeding(self, start_date: str = "2025-01-01") -> Dict[str, Any]:
        """
        Manually trigger historical data seeding.

        Args:
            start_date: ISO format date string (YYYY-MM-DD)

        Returns:
            Dictionary with seeding operation summary
        """
        logger.info(f"Starting historical data seeding from {start_date}...")
        return self.sync_manager.seed_historical_data(start_date)

    def run_on_demand_analysis(self, legislation_id: int) -> Dict[str, Any]:
        """
        Run AI analysis for a specific piece of legislation.

        Args:
            legislation_id: Database ID of legislation to analyze

        Returns:
            Dictionary with analysis result summary
        """
        logger.info(f"Running on-demand analysis for legislation ID {legislation_id}")
        return self._run_on_demand_analysis_func(self.db_session_factory, legislation_id)


def handle_signal(sig: int, frame: Any) -> None:
    """
    Signal handler for graceful shutdown.
    
    Args:
        sig: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {sig}. Shutting down...")
    
    # Safely access the global scheduler if it exists
    scheduler_instance = globals().get('scheduler')
    if scheduler_instance and scheduler_instance.is_running:
        scheduler_instance.stop()
    
    sys.exit(0)


# Initialize the scheduler when module is imported
scheduler = PolicyPulseScheduler() 