"""
Analysis Routes

This module contains endpoints for AI-powered analysis of legislation.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from pydantic import BaseModel

from app.data.data_store import DataStore
from app.models.legislation_models import Legislation, LegislationAnalysis
from app.ai_analysis.models import LegislationAnalysisResult
from app.ai_analysis.errors import AIAnalysisError
from app.api.models import (
    AnalysisStatusResponse,
    AnalysisHistoryResponse,
    SetPriorityPayload,
    PriorityUpdateResponse
)

# Define enums here since they're not available in the models
from enum import Enum

class AnalysisType(str, Enum):
    STANDARD = "STANDARD"
    DETAILED = "DETAILED"
    IMPACT = "IMPACT"

class AnalysisOptions(BaseModel):
    """Options for controlling analysis behavior."""
    deep_analysis: bool = False
    texas_focus: bool = True
    focus_areas: Optional[List[str]] = None
    model_name: Optional[str] = None
from app.api.dependencies import get_data_store, get_ai_analyzer, get_bill_store, get_legiscan_api
from app.api.utils import log_api_call, run_in_background
from app.api.error_handlers import error_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# -----------------------------------------------------------------------------
# Analysis Endpoints
# -----------------------------------------------------------------------------
@router.post("/legislation/{leg_id}/analysis", tags=["Analysis"], response_model=AnalysisStatusResponse)
@log_api_call
def analyze_legislation_ai(
    leg_id: int,
    background_tasks: BackgroundTasks,
    options: Optional[AnalysisOptions] = None,
    store: DataStore = Depends(get_data_store),
    ai_analyzer = Depends(get_ai_analyzer)
):
    """
    Trigger an AI-based structured analysis for the specified Legislation ID.

    Args:
        leg_id: Legislation ID to analyze
        options: Optional analysis parameters
        background_tasks: FastAPI background tasks for async processing
        store: DataStore instance
        ai_analyzer: AIAnalysis instance

    Returns:
        Analysis status and results

    Raises:
        HTTPException: If legislation is not found or analysis fails
    """
    with error_handler("AI analysis", {
        ValueError: status.HTTP_400_BAD_REQUEST,
        Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
    }):
        # Validate legislation ID
        if leg_id <= 0:
            raise ValueError("Legislation ID must be a positive integer")

        # Check if db_session is available and retrieve the legislation
        if store.db_session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail="Database session is not initialized. Please try again later."
            )

        # Check if legislation exists
        leg_obj = store.db_session.query(Legislation).filter_by(id=leg_id).first()
        if not leg_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Legislation with ID {leg_id} not found"
            )

        # Set default options if none provided
        if options is None:
            options = AnalysisOptions(deep_analysis=False, texas_focus=True, focus_areas=None, model_name=None)

        # Asynchronous processing if requested and background_tasks available
        if options.deep_analysis:
            async def run_analysis_task():
                # Create a new DataStore instance with its own session for the background task
                from app.data.data_store import DataStore
                from app.models import LegislationAnalysis
                
                task_store = None
                try:
                    # Create a new DataStore with its own session
                    task_store = DataStore(max_retries=3)
                    
                    # Check if db_session is available
                    if task_store.db_session is None:
                        raise ValueError("Database session is not initialized in background task")
                    
                    # Create a new analyzer instance with the new session
                    from app.ai_analysis import AIAnalysis
                    task_analyzer = AIAnalysis(db_session=task_store.db_session)
                    
                    # Run the analysis
                    analysis_obj = task_analyzer.analyze_legislation(legislation_id=leg_id)
                    logger.info(f"Background analysis completed for legislation ID={leg_id}, analysis ID={analysis_obj.id}")
                    
                    # Verify the analysis was saved
                    saved_analysis = task_store.db_session.query(LegislationAnalysis).filter_by(id=analysis_obj.id).first()
                    if not saved_analysis:
                        logger.error(f"Analysis was not saved to database for legislation ID={leg_id}")
                except Exception as e:
                    logger.error(f"Error in background analysis task for legislation ID={leg_id}: {e}", exc_info=True)
                    # Try to record the error in the database if possible
                    try:
                        if task_store and task_store.db_session:
                            # Create a placeholder analysis record to indicate the error
                            error_analysis = LegislationAnalysis(
                                legislation_id=leg_id,
                                analysis_version=1,  # Default to 1 if this is the first attempt
                                summary=f"Analysis failed: {str(e)}",
                                raw_analysis={"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()},
                                model_version="error"
                            )
                            task_store.db_session.add(error_analysis)
                            task_store.db_session.commit()
                            logger.info(f"Recorded analysis error for legislation ID={leg_id}")
                    except Exception as db_error:
                        logger.error(f"Failed to record analysis error in database: {db_error}", exc_info=True)
                finally:
                    # Always close the session when done
                    if task_store:
                        task_store.close()

            # Add task to background tasks
            background_tasks.add_task(run_analysis_task)

            return {
                "status": "processing", 
                "message": "Analysis started in the background. Check back later.",
                "legislation_id": leg_id
            }

        # Synchronous processing
        try:
            # Set model parameters if needed
            if hasattr(options, "model_name") and options.model_name:
                ai_analyzer.config.model_name = options.model_name

            # Run analysis
            analysis_obj = ai_analyzer.analyze_legislation(legislation_id=leg_id)

            # Verify the analysis was saved
            from app.models import LegislationAnalysis
            if store.db_session is not None:
                saved_analysis = store.db_session.query(LegislationAnalysis).filter_by(id=analysis_obj.id).first()
                if not saved_analysis:
                    logger.warning(f"Analysis may not have been saved properly for legislation ID={leg_id}")
                    # Try to commit explicitly
                    try:
                        store.db_session.commit()
                        logger.info(f"Explicitly committed session for analysis of legislation ID={leg_id}")
                    except Exception as commit_error:
                        logger.error(f"Failed to explicitly commit session: {commit_error}", exc_info=True)
            else:
                logger.warning(f"Cannot verify if analysis was saved: db_session is None for legislation ID={leg_id}")

            response = {
                "status": "completed",
                "legislation_id": leg_id,
                "analysis_id": analysis_obj.id,
                "analysis_version": analysis_obj.analysis_version,
                "analysis_date": analysis_obj.analysis_date.isoformat() if analysis_obj.analysis_date else None
            }
            
            # Add insufficient_text flag if present
            if hasattr(analysis_obj, "insufficient_text") and analysis_obj.insufficient_text:
                response["insufficient_text"] = True
                response["message"] = "This bill contains insufficient text for detailed analysis."
                
            return response
        except ValueError as ve:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        except Exception as e:
            logger.error(f"Error analyzing legislation ID={leg_id} with AI: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI analysis failed.")

@router.get("/legislation/{leg_id}/analysis/history", tags=["Analysis"], response_model=AnalysisHistoryResponse)
@log_api_call
def get_legislation_analysis_history(
    leg_id: int,
    store: DataStore = Depends(get_data_store)
):
    """
    Returns the history of analyses for a legislation, showing how assessments
    have changed over time.

    Args:
        leg_id: Legislation ID
        store: DataStore instance

    Returns:
        Analysis history

    Raises:
        HTTPException: If legislation is not found or analysis history cannot be retrieved
    """
    with error_handler("Get analysis history", {
            ValueError: status.HTTP_400_BAD_REQUEST,
            Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
        }):
        # Validate legislation ID
        if leg_id <= 0:
            raise ValueError("Legislation ID must be a positive integer")

        # Check if db_session is available
        if store.db_session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database session is not initialized. Please try again later."
            )

        # Check if legislation exists
        leg = store.db_session.query(Legislation).filter_by(id=leg_id).first()
        if not leg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Legislation with ID {leg_id} not found"
            )

        # Get and format analyses
        analyses = []
        sorted_analyses = sorted(leg.analyses, key=lambda a: a.analysis_version)

        analyses.extend(
            {
                "id": analysis.id,
                "version": analysis.analysis_version,
                "date": (
                    analysis.analysis_date.isoformat()
                    if analysis.analysis_date
                    else None
                ),
                "summary": analysis.summary,
                "impact_category": (
                    analysis.impact_category.value
                    if analysis.impact_category
                    else None
                ),
                "impact_level": (
                    analysis.impact.value
                    if hasattr(analysis, 'impact') and analysis.impact
                    else None
                ),
                "model_version": analysis.model_version,
                "insufficient_text": (
                    analysis.insufficient_text
                    if hasattr(analysis, 'insufficient_text')
                    else False
                ),
            }
            for analysis in sorted_analyses
        )
        return {
            "legislation_id": leg_id,
            "analysis_count": len(analyses),
            "analyses": analyses
        }

@router.post("/legislation/{leg_id}/analysis/async", tags=["Analysis"], response_model=AnalysisStatusResponse)
@log_api_call
async def analyze_legislation_ai_async(
    leg_id: int,
    options: Optional[AnalysisOptions] = None,
    store: DataStore = Depends(get_data_store),
    ai_analyzer = Depends(get_ai_analyzer)
):
    """
    Trigger an asynchronous AI-based structured analysis for the specified Legislation ID.

    Args:
        leg_id: Legislation ID to analyze
        options: Optional analysis parameters
        store: DataStore instance
        ai_analyzer: AIAnalysis instance

    Returns:
        Analysis status and results
    """
    with error_handler("Async AI analysis", {
                ValueError: status.HTTP_400_BAD_REQUEST,
                Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
            }):
        # Validate legislation ID
        if leg_id <= 0:
            raise ValueError("Legislation ID must be a positive integer")

        # Check if db_session is available
        if store.db_session is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database session is not initialized. Please try again later."
            )

        # Query the legislation object
        leg_obj = store.db_session.query(Legislation).filter_by(id=leg_id).first()
        if not leg_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Legislation with ID {leg_id} not found"
            )

        # Set default options if none provided
        if options is None:
            options = AnalysisOptions(
                deep_analysis=False,
                texas_focus=True,
                focus_areas=None,
                model_name=None
            )

        try:
            if hasattr(options, "model_name") and options.model_name:
                ai_analyzer.config.model_name = options.model_name

            # Run analysis asynchronously
            analysis_obj = await ai_analyzer.analyze_legislation_async(legislation_id=leg_id)

            # Verify the analysis was saved
            from app.models import LegislationAnalysis
            if store.db_session is not None:
                saved_analysis = store.db_session.query(LegislationAnalysis).filter_by(id=analysis_obj.id).first()
                if not saved_analysis:
                    logger.warning(f"Async analysis may not have been saved properly for legislation ID={leg_id}")
                    # Try to commit explicitly
                    try:
                        store.db_session.commit()
                        logger.info(f"Explicitly committed session for async analysis of legislation ID={leg_id}")
                    except Exception as commit_error:
                        logger.error(f"Failed to explicitly commit session: {commit_error}", exc_info=True)
            else:
                logger.warning(f"Cannot verify if analysis was saved: db_session is None for legislation ID={leg_id}")

            response = {
                "status": "completed",
                "legislation_id": leg_id,
                "analysis_id": analysis_obj.id,
                "analysis_version": analysis_obj.analysis_version,
                "analysis_date": analysis_obj.analysis_date.isoformat() if analysis_obj.analysis_date else None
            }
            
            # Add insufficient_text flag if present
            if hasattr(analysis_obj, "insufficient_text") and analysis_obj.insufficient_text:
                response["insufficient_text"] = True
                response["message"] = "This bill contains insufficient text for detailed analysis."
                
            return response
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(ve)
            ) from ve
        except Exception as e:
            logger.error(f"Error analyzing legislation ID={leg_id} with AI: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Async AI analysis failed: {str(e)}",
            ) from e

@router.post("/legislation/batch-analyze", tags=["Analysis"], response_model=dict)
@log_api_call
async def batch_analyze_legislation(
    legislation_ids: List[int], 
    max_concurrent: int = 5,
    store: DataStore = Depends(get_data_store),
    ai_analyzer = Depends(get_ai_analyzer)
):
    """
    Analyze multiple pieces of legislation in parallel.

    Args:
        legislation_ids: List of legislation IDs to analyze
        max_concurrent: Maximum number of concurrent analyses
        store: DataStore instance
        ai_analyzer: AIAnalysis instance

    Returns:
        Results of batch analysis
    """
    with error_handler("Batch analyze legislation", {
                ValueError: status.HTTP_400_BAD_REQUEST,
                Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
            }):
        if not legislation_ids:
            raise ValueError("No legislation IDs provided")

        if len(legislation_ids) > 50:  # Set a reasonable limit
            raise ValueError("Too many legislation IDs (maximum 50)")

        # Run batch analysis
        try:
            return await ai_analyzer.batch_analyze_async(legislation_ids, max_concurrent)
        except Exception as e:
            logger.error(f"Error in batch analysis: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Batch analysis failed: {str(e)}",
            ) from e

@router.get("/legislation/{leg_id}/analysis/", tags=["Analysis"])
@log_api_call
def get_legislation_analysis(
    leg_id: int,
    store: DataStore = Depends(get_data_store),
    ai_analyzer = Depends(get_ai_analyzer)
):
    """
    Retrieve the latest analysis for a specific legislation.

    Args:
        leg_id: Legislation ID
        store: DataStore instance
        ai_analyzer: AI analyzer instance for on-demand analysis

    Returns:
        Analysis data for the specified legislation
    """
    with error_handler("retrieving legislation analysis", {
                IndexError: status.HTTP_404_NOT_FOUND,
                ValueError: status.HTTP_400_BAD_REQUEST,
                Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
            }):
        # Validate and fetch analysis from database
        if not store or not store.db_session:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )

        # Check if legislation exists
        legislation = store.db_session.query(Legislation).filter_by(id=leg_id).first()
        if not legislation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Legislation with ID {leg_id} not found"
            )

        # Get the latest analysis for this legislation
        analysis = store.db_session.query(LegislationAnalysis).filter_by(
            legislation_id=leg_id
        ).order_by(LegislationAnalysis.analysis_version.desc()).first()
        
        if not analysis:
            # Return an empty analysis object instead of raising an exception
            return {
                "legislation_id": leg_id,
                "analysis_id": None,
                "analysis_version": None,
                "analysis_date": None,
                "impact_category": None,
                "impact": None,
                "summary": "No analysis available for this legislation yet.",
                "key_points": [],
                "public_health_impacts": None,
                "local_gov_impacts": None,
                "economic_impacts": None,
                "environmental_impacts": None,
                "education_impacts": None,
                "infrastructure_impacts": None,
                "stakeholder_impacts": None,
                "recommended_actions": None,
                "immediate_actions": None,
                "resource_needs": None,
                "confidence_score": None,
                "model_version": None,
                "insufficient_text": True,
                "status": "pending"
            }
            
        # Format the analysis response
        return {
            "legislation_id": leg_id,
            "analysis_id": analysis.id,
            "analysis_version": analysis.analysis_version,
            "analysis_date": analysis.analysis_date.isoformat() if analysis.analysis_date else None,
            "impact_category": str(analysis.impact_category.value) if analysis.impact_category else None,
            "impact": str(analysis.impact.value) if analysis.impact else None,
            "summary": analysis.summary,
            "key_points": analysis.key_points,
            "public_health_impacts": analysis.public_health_impacts,
            "local_gov_impacts": analysis.local_gov_impacts,
            "economic_impacts": analysis.economic_impacts,
            "environmental_impacts": analysis.environmental_impacts,
            "education_impacts": analysis.education_impacts,
            "infrastructure_impacts": analysis.infrastructure_impacts,
            "stakeholder_impacts": analysis.stakeholder_impacts,
            "recommended_actions": analysis.recommended_actions,
            "immediate_actions": analysis.immediate_actions,
            "resource_needs": analysis.resource_needs,
            "confidence_score": analysis.confidence_score,
            "model_version": analysis.model_version,
            "insufficient_text": analysis.insufficient_text,
            "status": "complete"
        }

# -----------------------------------------------------------------------------
# Priority Endpoints
# -----------------------------------------------------------------------------
@router.post("/legislation/{leg_id}/priority", tags=["Priority"], response_model=PriorityUpdateResponse)
@log_api_call
def update_priority(
    leg_id: int,
    payload: SetPriorityPayload,
    store: DataStore = Depends(get_data_store)
):
    """
    Update the priority scores for a specific legislation.

    Args:
        leg_id: Legislation ID
        payload: Priority data to update
        store: DataStore instance

    Returns:
        Updated priority data

    Raises:
        HTTPException: If legislation is not found or priority cannot be updated
    """
    with error_handler("Update priority", {
                    ValueError: status.HTTP_400_BAD_REQUEST,
                    Exception: status.HTTP_500_INTERNAL_SERVER_ERROR
                }):
        # Validate legislation ID
        if leg_id <= 0:
            raise ValueError("Legislation ID must be a positive integer")

        try:
            # Check if db_session is available
            if not store or not store.db_session:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database connection not available"
                )

            # Check if legislation exists
            leg = store.db_session.query(Legislation).filter_by(id=leg_id).first()
            if not leg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Legislation with ID {leg_id} not found"
                )

            # Check if LegislationPriority model is available
            try:
                from app.models import LegislationPriority
                has_priority_model = True
            except ImportError as e:
                has_priority_model = False
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Priority updates not supported: LegislationPriority model not available",
                ) from e

            # Update priority directly since the method may not be available
            try:
                # Get existing priority or create a new one
                priority = store.db_session.query(LegislationPriority).filter_by(legislation_id=leg_id).first()
                update_data = payload.model_dump(exclude_unset=True)
                
                if not priority:
                    # Create new priority record
                    priority = LegislationPriority(legislation_id=leg_id)
                    store.db_session.add(priority)
                
                # Update fields
                for key, value in update_data.items():
                    if hasattr(priority, key):
                        setattr(priority, key, value)
                
                # Commit changes
                store.db_session.commit()
                store.db_session.refresh(priority)
                
                # Format response
                priority_dict = {
                    "id": priority.id,
                    "legislation_id": priority.legislation_id,
                    "public_health_relevance": priority.public_health_relevance,
                    "local_govt_relevance": priority.local_govt_relevance,
                    "overall_priority": priority.overall_priority,
                    "notes": priority.notes,
                    "updated_at": priority.updated_at.isoformat() if priority.updated_at else None
                }
                
                return {
                    "status": "success",
                    "message": f"Priority updated for legislation ID {leg_id}",
                    "priority": priority_dict
                }
                
            except Exception as priority_error:
                logger.error(f"Error updating priority: {priority_error}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update priority: {str(priority_error)}"
                )

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error updating priority for legislation {leg_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            ) from e
