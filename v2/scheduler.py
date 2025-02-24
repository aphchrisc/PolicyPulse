"""
scheduler.py

Runs the APScheduler for daily/backup syncs with LegiScan. 
Uses SyncMetadata to track progress and logs errors to SyncError.
"""

import sys
import signal
import logging
from datetime import datetime, timezone
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from models import init_db, SyncMetadata, SyncError, SyncStatusEnum
from models import Legislation  # query for final stats
from legiscan_api import LegiScanAPI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LegiScanSyncManager:
    """
    Orchestrates the actual data sync from LegiScan. 
    (You can break out logic further if needed.)
    """
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory

    def run_daily_sync(self) -> dict:
        """
        Example daily sync logic:
         1) For each monitored state, fetch session list
         2) For each active session, retrieve master list
         3) Compare each bill => upsert
        Returns a summary dict with counts, errors, etc.
        """
        db_session = self.db_session_factory()
        api = LegiScanAPI(db_session)

        summary = {
            "new_bills": 0,
            "bills_updated": 0,
            "errors": [],
        }

        try:
            # Loop over monitored jurisdictions
            for state in api.monitored_jurisdictions:
                sessions = api.get_session_list(state)
                for s in sessions:
                    # Example: only sync if year_end is this year or future
                    if s.get("year_end", 0) >= datetime.now().year:
                        master = api.get_master_list(s["session_id"])
                        # masterlist keys => "0" for metadata, "1", "2", ...
                        # skip key "0", which is the session info
                        for key, bill_info in master.items():
                            if key == "0":
                                continue
                            try:
                                bill_obj = api.get_bill(bill_info["bill_id"])
                                if bill_obj:
                                    saved = api.save_bill_to_db(bill_obj)
                                    if saved and saved.created_at == saved.updated_at:
                                        summary["new_bills"] += 1
                                    elif saved:
                                        summary["bills_updated"] += 1
                            except Exception as ex:
                                err_msg = f"Failed to save bill {bill_info.get('bill_id')}: {ex}"
                                logger.error(err_msg)
                                summary["errors"].append(err_msg)
            db_session.close()
        except Exception as e:
            logger.error(f"run_daily_sync encountered fatal error: {e}")
            db_session.close()
            summary["errors"].append(str(e))

        return summary


class SyncScheduler:
    """
    Sets up two daily jobs (10pm UTC & 4am UTC).
    Tracks progress in SyncMetadata & SyncError.
    """
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=timezone.utc)
        # Initialize DB once for entire process:
        self.db_session_factory = init_db()
        self.is_running = False

    def _daily_sync_job(self):
        """Daily sync job with try/except to update SyncMetadata and log errors."""
        db_session = self.db_session_factory()
        sync_start = datetime.now(timezone.utc)

        # Create a SyncMetadata record
        sync_meta = SyncMetadata(
            last_sync=sync_start,
            status=SyncStatusEnum.IN_PROGRESS,
            sync_type="daily"
        )
        db_session.add(sync_meta)
        db_session.commit()

        try:
            logger.info("Starting daily sync job...")

            sync_manager = LegiScanSyncManager(self.db_session_factory)
            summary = sync_manager.run_daily_sync()

            # Update sync metadata
            sync_meta.status = SyncStatusEnum.COMPLETED
            sync_meta.last_successful_sync = datetime.now(timezone.utc)
            sync_meta.new_bills = summary["new_bills"]
            sync_meta.bills_updated = summary["bills_updated"]

            if summary["errors"]:
                sync_meta.status = SyncStatusEnum.PARTIAL
                # record each error
                for err in summary["errors"]:
                    sync_error = SyncError(
                        sync_id=sync_meta.id,
                        error_type="sync_error",
                        error_message=err
                    )
                    db_session.add(sync_error)

            db_session.commit()
            logger.info(f"Daily sync completed. new_bills={summary['new_bills']}, "
                        f"updated={summary['bills_updated']}, errors={len(summary['errors'])}")

        except Exception as e:
            logger.error(f"Daily sync failed: {e}", exc_info=True)
            sync_meta.status = SyncStatusEnum.FAILED

            sync_err = SyncError(
                sync_id=sync_meta.id,
                error_type="fatal_error",
                error_message=str(e)
            )
            db_session.add(sync_err)

            db_session.commit()
        finally:
            db_session.close()

    def on_job_executed(self, event):
        """Log job completion/failure events."""
        if event.exception:
            logger.error(f"Sync job failed with error: {event.exception}")
        else:
            logger.info("Sync job executed successfully.")

    def setup_jobs(self):
        """
        Set up the daily job at 10 PM UTC, plus a backup at 4 AM UTC.
        """
        self.scheduler.add_listener(
            self.on_job_executed,
            EVENT_JOB_ERROR | EVENT_JOB_EXECUTED
        )

        self.scheduler.add_job(
            self._daily_sync_job,
            "cron",
            hour=22,
            minute=0,
            id="daily_legiscan_sync",
            misfire_grace_time=3600,
            coalesce=True
        )

        # Backup job
        self.scheduler.add_job(
            self._daily_sync_job,
            "cron",
            hour=4,
            minute=0,
            id="backup_legiscan_sync",
            misfire_grace_time=3600,
            coalesce=True
        )

    def start(self):
        """Start the background scheduler. Listen for signals to shut down."""
        self.is_running = True
        self.setup_jobs()
        self.scheduler.start()
        logger.info("SyncScheduler started")

        # Hook signals for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        while self.is_running:
            time.sleep(60)

    def handle_shutdown(self, signum, frame):
        logger.info("Shutdown signal received, stopping scheduler...")
        self.is_running = False
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        sys.exit(0)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    scheduler = SyncScheduler()
    try:
        scheduler.start()
    except Exception as e:
        logger.error(f"Scheduler main() crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------