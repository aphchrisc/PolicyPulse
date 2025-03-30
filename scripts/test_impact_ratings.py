#!/usr/bin/env python
"""
test_impact_ratings.py

Script to test the impact ratings functionality by analyzing a specific bill.
"""

import sys
import os
import logging
import argparse
from datetime import datetime
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path to make app imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.legislation_models import Legislation, LegislationAnalysis, ImpactRating
from app.ai_analysis.analyzer import AIAnalysis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_db_url():
    """Get database URL from environment variables."""
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "postgres")
    dbname = os.environ.get("DB_NAME", "policypulse")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def analyze_bill(legislation_id, force_reanalysis=False):
    """
    Analyze a specific bill and check if impact ratings are created.
    
    Args:
        legislation_id: ID of the legislation to analyze
        force_reanalysis: Whether to force reanalysis even if already analyzed
    """
    logger.info(f"Testing impact ratings for legislation ID: {legislation_id}")
    
    # Create database session
    try:
        engine = create_engine(get_db_url())
        Session = sessionmaker(bind=engine)
        db_session = Session()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}", exc_info=True)
        return 1

    try:
        # Get the legislation
        legislation = db_session.query(Legislation).filter_by(id=legislation_id).first()
        if not legislation:
            logger.error(f"Legislation with ID {legislation_id} not found")
            return 1
            
        logger.info(f"Found legislation: {legislation.bill_number} - {legislation.title}")
        
        # Check for existing analysis
        existing_analysis = db_session.query(LegislationAnalysis).filter_by(legislation_id=legislation_id).first()
        if existing_analysis and not force_reanalysis:
            logger.info(f"Legislation already has analysis (version {existing_analysis.analysis_version})")
            logger.info("Use --force to reanalyze")
        else:
            # Initialize AI analysis
            analyzer = AIAnalysis(db_session)
            
            # Run analysis
            logger.info(f"Running analysis on {legislation.bill_number}...")
            try:
                analysis_result = analyzer.analyze_legislation(legislation_id)
                logger.info("Analysis completed successfully")
                
                # Get the analysis details
                analysis_obj = db_session.query(LegislationAnalysis).filter_by(legislation_id=legislation_id).order_by(LegislationAnalysis.analysis_version.desc()).first()
                if analysis_obj:
                    logger.info(f"Analysis stored with version {analysis_obj.analysis_version}")
                    logger.info(f"Impact category: {analysis_obj.impact_category}")
                    logger.info(f"Impact level: {analysis_obj.impact}")
                else:
                    logger.warning("Analysis object not found after analysis")
                
                # Commit the changes
                db_session.commit()
                logger.info("Database changes committed")
            except Exception as e:
                logger.error(f"Error during analysis: {e}", exc_info=True)
                db_session.rollback()
                return 1
        
        # Check for impact ratings
        impact_ratings = db_session.query(ImpactRating).filter_by(legislation_id=legislation_id).all()
        logger.info(f"Found {len(impact_ratings)} impact ratings for legislation {legislation_id}")
        
        # Display impact ratings
        for i, rating in enumerate(impact_ratings, 1):
            logger.info(f"Impact Rating #{i}:")
            logger.info(f"  Category: {rating.impact_category}")
            logger.info(f"  Level: {rating.impact_level}")
            logger.info(f"  Description: {rating.impact_description[:100]}..." if len(rating.impact_description) > 100 else f"  Description: {rating.impact_description}")
            logger.info(f"  Affected Entities: {rating.affected_entities}")
            logger.info(f"  Confidence Score: {rating.confidence_score}")
            logger.info(f"  AI Generated: {rating.is_ai_generated}")
            logger.info("---")
        
        return 0
    
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        return 1
    finally:
        # Always close the session
        db_session.close()

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Test impact ratings functionality")
    parser.add_argument("--legislation-id", type=int, required=True, help="ID of the legislation to analyze")
    parser.add_argument("--force", action="store_true", help="Force reanalysis even if already analyzed")
    args = parser.parse_args()

    return analyze_bill(args.legislation_id, args.force)

if __name__ == "__main__":
    sys.exit(main())
