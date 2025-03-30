"""
scheduler/jobs.py

Defines scheduled jobs for the PolicyPulse application.
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.models import SyncError as DBSyncError
from app.ai_analysis import AIAnalysis
from app.scheduler.sync_manager import LegislationSyncManager

logger = logging.getLogger(__name__)


def nightly_sync_job(sync_manager: LegislationSyncManager) -> Dict[str, Any]:
    """
    Run the nightly sync job with immediate AI analysis of all new/changed bills.
    
    Args:
        sync_manager: Instance of LegislationSyncManager
        
    Returns:
        Dictionary with sync operation summary
    """
    logger.info("Starting nightly LegiScan sync job with immediate analysis...")
    try:
        summary = sync_manager.run_nightly_sync()
        logger.info(
            "Nightly sync completed. New bills: %(new)s, Updated: %(updated)s, Analyzed: %(analyzed)s, Errors: %(errors)s",
            {
                "new": summary['new_bills'],
                "updated": summary['bills_updated'],
                "analyzed": summary['bills_analyzed'],
                "errors": len(summary['errors'])
            })

        # Alert on high error count
        if len(summary['errors']) > 10:
            logger.warning(
                "High error count in nightly sync: %s errors",
                len(summary['errors'])
            )
            
        return summary
    except Exception as e:
        logger.error("Nightly sync job failed: %s", e, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "time": datetime.now()
        }


def daily_maintenance_job(db_session_factory: sessionmaker) -> Dict[str, Any]:
    """
    Perform daily database maintenance tasks.
    
    Args:
        db_session_factory: SQLAlchemy sessionmaker for creating database sessions
        
    Returns:
        Dictionary with maintenance operation summary
    """
    logger.info("Starting daily database maintenance job...")
    result = {
        "deleted_records": 0,
        "vacuum_success": False,
        "errors": [],
        "time": datetime.now(),
        "success": True
    }

    db_session = db_session_factory()
    try:
        # Clean up old sync error records (older than 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        deleted_count = db_session.query(DBSyncError).filter(
            DBSyncError.error_time < thirty_days_ago
        ).delete()
        result["deleted_records"] = deleted_count

        # Vacuum analyze if using PostgreSQL
        try:
            db_session.execute("VACUUM ANALYZE")
            result["vacuum_success"] = True
        except Exception as e:
            result["vacuum_success"] = False
            error_msg = "VACUUM ANALYZE failed: %s" % e
            logger.warning(error_msg)
            result["errors"].append(error_msg)

        logger.info(
            "Daily maintenance completed. Removed %s old error records. VACUUM success: %s",
            deleted_count, result['vacuum_success']
        )
        db_session.commit()
    except SQLAlchemyError as e:
        error_msg = "Database error in maintenance job: %s" % e
        logger.error(error_msg, exc_info=True)
        result["errors"].append(error_msg)
        result["success"] = False
        db_session.rollback()
    except Exception as e:
        error_msg = "Daily maintenance job failed: %s" % e
        logger.error(error_msg, exc_info=True)
        result["errors"].append(error_msg)
        result["success"] = False
        db_session.rollback()
    finally:
        db_session.close()
        
    return result


def run_on_demand_analysis(db_session_factory: sessionmaker, legislation_id: int) -> Dict[str, Any]:
    """
    Run AI analysis for a specific piece of legislation.

    Args:
        db_session_factory: SQLAlchemy sessionmaker for creating database sessions
        legislation_id: Database ID of legislation to analyze

    Returns:
        Dictionary with analysis result summary
    """
    logger.info("Running on-demand analysis for legislation ID %s", legislation_id)
    result = {
        "legislation_id": legislation_id,
        "success": False,
        "time": datetime.now(),
        "errors": []
    }

    db_session = db_session_factory()
    try:
        analyzer = AIAnalysis(db_session=db_session)
        analyzer.analyze_legislation(legislation_id=legislation_id)
        logger.info("On-demand analysis completed for legislation ID %s", legislation_id)
        result["success"] = True
    except Exception as e:
        error_msg = f"On-demand analysis failed for legislation ID {legislation_id}: {e}"
        logger.error(error_msg, exc_info=True)
        result["errors"].append(error_msg)
    finally:
        db_session.close()

    return result 
