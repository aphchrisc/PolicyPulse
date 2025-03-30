"""
Legislation analysis module for handling both text and PDF content.

This module provides a clean implementation of legislation analysis functionality,
supporting both text and binary (PDF) content with appropriate handling for each.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union, Tuple

from .pdf_handler import get_pdf_metadata
from .errors import AIAnalysisError, TokenLimitError
from .text_preprocessing import ensure_plain_string
from .db_operations import store_legislation_analysis_async
from .async_analysis import _process_analysis_async
from .impact_analysis import update_legislation_priority
from .analysis_processing import call_structured_analysis_async, analyze_in_chunks_async

logger = logging.getLogger(__name__)


def analyze_legislation(analyzer, legislation_id: int) -> Any:
    """
    Analyze legislation by ID, handling both text and PDF content.
    
    This is a synchronous wrapper around the async version.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation to analyze
        
    Returns:
        LegislationAnalysis object or AIAnalysisError
    """
    try:
        return asyncio.run(analyze_legislation_async(analyzer, legislation_id))
    except AIAnalysisError:
        # Re-raise AIAnalysisError directly as these are expected domain exceptions
        raise
    except (asyncio.CancelledError, asyncio.TimeoutError) as e:
        # Handle specific asyncio exceptions
        logger.error("Async operation error in analyze_legislation: %s", e)
        raise AIAnalysisError(f"Failed to analyze legislation ID={legislation_id}: {str(e)}") from e
    except Exception as e:
        # Log and re-raise as AIAnalysisError for other exceptions
        logger.error("Unexpected error in analyze_legislation: %s", e)
        raise AIAnalysisError(f"Failed to analyze legislation ID={legislation_id}: {str(e)}") from e


async def analyze_legislation_async(analyzer, legislation_id: int) -> Any:
    """
    Asynchronously analyze legislation by ID, handling both text and PDF content.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation to analyze
        
    Returns:
        LegislationAnalysis object or AIAnalysisError
    """
    if cached_analysis := _check_cache(analyzer, legislation_id):
        return cached_analysis

    # Get legislation object
    leg_obj = _get_legislation_object(analyzer, legislation_id)

    # Extract content and determine if it's binary
    content, is_binary = _extract_content(analyzer, leg_obj)

    # Process the analysis based on content type - use imported async version
    analysis_data = await _process_analysis_async(analyzer, content, is_binary, legislation_id, leg_obj)

    # Store and return the analysis results
    return await _store_analysis_results(analyzer, legislation_id, analysis_data)


def _check_cache(analyzer: Any, legislation_id: int) -> Optional[Any]:
    """Check if analysis is available in cache and not expired."""
    # NOTE: Protected member access is intentional as this module is designed 
    # to work directly with the analyzer's internal caching mechanism
    with analyzer._cache_lock:  # pylint: disable=protected-access
        if legislation_id in analyzer._analysis_cache:  # pylint: disable=protected-access
            cache_time, cached_analysis = analyzer._analysis_cache[legislation_id]  # pylint: disable=protected-access
            cache_age_minutes = (datetime.now(timezone.utc) - cache_time).total_seconds() / 60
            if cache_age_minutes < analyzer.config.cache_ttl_minutes:
                logger.info("Using cached analysis for legislation ID=%s", legislation_id)
                return cached_analysis
            
            # Cache expired, remove it
            del analyzer._analysis_cache[legislation_id]  # pylint: disable=protected-access
    return None


def _get_legislation_object(analyzer: Any, legislation_id: int) -> Any:
    """Retrieve legislation object from database."""
    leg_obj = analyzer.db_session.query(analyzer.models.Legislation).filter_by(id=legislation_id).first()
    if leg_obj is None:
        error_msg = f"Legislation with ID={legislation_id} not found in DB."
        logger.error(error_msg)
        raise ValueError(error_msg)
    return leg_obj


def _extract_content(analyzer: Any, leg_obj: Any) -> Tuple[Union[str, bytes], bool]:
    """Extract content from legislation object and determine if it's binary."""
    text_rec = leg_obj.latest_text
    
    # No text record or content available, use description
    if text_rec is None or text_rec.text_content is None:
        content = ensure_plain_string(leg_obj.description if leg_obj.description is not None else "")
        return content, False
    
    is_binary = getattr(text_rec, 'is_binary', False)
    content_type = getattr(text_rec, 'content_type', None)
    
    # Handle PDF content with vision-enabled models
    if (is_binary and content_type == 'application/pdf' and
            analyzer.openai_client.vision_enabled and analyzer.openai_client.supports_vision):
        logger.info("Using vision-enabled analysis for PDF in LegislationText ID=%s", text_rec.id)
        
        if isinstance(text_rec.text_content, bytes):
            return text_rec.text_content, True
        
        # Try to encode string to bytes if marked as binary
        try:
            content = text_rec.text_content.encode('utf-8')
            return content, True
        except (AttributeError, UnicodeEncodeError):
            logger.error("Failed to get binary content from LegislationText ID=%s", text_rec.id)
            content = ensure_plain_string(leg_obj.description)
            return content, False
    
    # Handle non-PDF binary content
    if is_binary:
        logger.warning("Binary content in LegislationText ID=%s, using description", text_rec.id)
        content = ensure_plain_string(leg_obj.description)
        return content, False
    
    # Handle text content
    return ensure_plain_string(text_rec.text_content), False


async def _store_analysis_results(analyzer: Any, legislation_id: int, analysis_data: Dict[str, Any]) -> Any:
    """Store analysis results and update cache."""
    try:
        # Create a new analysis object
        analysis_obj = await store_legislation_analysis_async(
            analyzer, legislation_id, analysis_data
        )
        
        # Update the cache - protected access is necessary for internal cache management
        with analyzer._cache_lock:  # pylint: disable=protected-access
            analyzer._analysis_cache[legislation_id] = (datetime.now(timezone.utc), analysis_obj)  # pylint: disable=protected-access
        
        # Update priority in a separate transaction
        if hasattr(analyzer, 'HAS_PRIORITY_MODEL') and analyzer.HAS_PRIORITY_MODEL:
            await _update_legislation_priority_async(analyzer, legislation_id, analysis_data)
        
        # Ensure everything is committed
        analyzer.db_session.commit()
        logger.info("Successfully committed analysis for legislation ID=%s", legislation_id)
        
        return analysis_obj
    except Exception as e:
        analyzer.db_session.rollback()
        logger.error("Failed to store analysis for legislation ID=%s: %s", legislation_id, e, exc_info=True)
        raise

async def _analyze_binary_content_async(analyzer: Any, content: bytes, legislation_id: int) -> Dict[str, Any]:
    """
    Analyze binary content (PDF) using vision-enabled models.
    
    Args:
        analyzer: The AIAnalysis instance
        content: Binary content to analyze
        legislation_id: ID of the legislation
        
    Returns:
        Analysis data as a dictionary
    """
    logger.info("Analyzing binary content for legislation ID=%s", legislation_id)
    
    # Get PDF metadata
    metadata = get_pdf_metadata(content)
    logger.info("PDF metadata: %s", metadata)
    
    # Use the vision-enabled analysis
    async with analyzer.openai_client.async_transaction() as transaction_ctx:
        json_schema = analyzer.utils.get_analysis_json_schema()
        user_prompt = analyzer.utils.create_user_prompt("", is_chunk=False)  # Empty text since we'll use PDF
        
        analysis_data = await analyzer.openai_client.call_structured_analysis_with_pdf_async(
            content=content,
            prompt=user_prompt,
            json_schema=json_schema,
            transaction_ctx=transaction_ctx
        )
    
    return analysis_data

# Define a constant for the insufficient text message to avoid duplication
INSUFFICIENT_TEXT_MSG = "Unable to determine due to insufficient text"

def create_insufficient_text_analysis() -> Dict[str, Any]:
    """
    Create a minimal analysis structure for bills with insufficient text.
    
    Returns:
        A dictionary with minimal analysis data for insufficient text
    """
    return {
        "summary": "Insufficient text available for detailed analysis.",
        "key_points": [{"point": "Insufficient text for detailed analysis", "impact_type": "neutral"}],
        "public_health_impacts": {
            "direct_effects": [INSUFFICIENT_TEXT_MSG],
            "indirect_effects": [INSUFFICIENT_TEXT_MSG],
            "funding_impact": [INSUFFICIENT_TEXT_MSG],
            "vulnerable_populations": [INSUFFICIENT_TEXT_MSG]
        },
        "local_government_impacts": {
            "administrative": [INSUFFICIENT_TEXT_MSG],
            "fiscal": [INSUFFICIENT_TEXT_MSG],
            "implementation": [INSUFFICIENT_TEXT_MSG]
        },
        "economic_impacts": {
            "direct_costs": [INSUFFICIENT_TEXT_MSG],
            "economic_effects": [INSUFFICIENT_TEXT_MSG],
            "benefits": [INSUFFICIENT_TEXT_MSG],
            "long_term_impact": [INSUFFICIENT_TEXT_MSG]
        },
        "environmental_impacts": [INSUFFICIENT_TEXT_MSG],
        "education_impacts": [INSUFFICIENT_TEXT_MSG],
        "infrastructure_impacts": [INSUFFICIENT_TEXT_MSG],
        "recommended_actions": ["Monitor for more detailed information"],
        "immediate_actions": ["None required at this time"],
        "resource_needs": ["None identified due to insufficient text"],
        "impact_summary": {
            "primary_category": "public_health",
            "impact_level": "low",
            "relevance_to_texas": "low"
        },
        "insufficient_text": True
    }

async def _analyze_text_content_async(analyzer: Any, content: str, legislation_id: int) -> Dict[str, Any]:
    """
    Analyze text content using standard text-based models.
    
    Args:
        analyzer: The AIAnalysis instance
        content: Text content to analyze
        legislation_id: ID of the legislation
        
    Returns:
        Analysis data as a dictionary
    """
    logger.info("Analyzing text content for legislation ID=%s", legislation_id)
    
    # Count tokens to determine if chunking is needed
    token_count = analyzer.token_counter.count_tokens(content)
    if token_count > analyzer.config.max_context_tokens:
        raise TokenLimitError(f"Token count exceeds limit of {analyzer.config.max_context_tokens}")

    safe_limit = analyzer.config.max_context_tokens - analyzer.config.safety_buffer
    logger.info("Legislation %s has ~%s tokens (limit: %s)", legislation_id, token_count, safe_limit)

    # Process the analysis
    if token_count > safe_limit:
        logger.warning("Legislation %s exceeds token limit, using chunking", legislation_id)
        chunks, has_structure = analyzer.text_chunker.chunk_text(content, safe_limit)
        
        async with analyzer.openai_client.async_transaction() as transaction_ctx:
            if len(chunks) == 1:
                text_for_analysis = chunks[0]
                analysis_data = await call_structured_analysis_async(
                    analyzer, text_for_analysis, is_chunk=False, transaction_ctx=transaction_ctx)
            else:
                # Get the legislation object again to pass to analyze_in_chunks_async
                leg_obj = analyzer.db_session.query(analyzer.models.Legislation).filter_by(id=legislation_id).first()
                analysis_data = await analyze_in_chunks_async(
                    analyzer, chunks, has_structure, leg_obj, transaction_ctx=transaction_ctx)
    else:
        async with analyzer.openai_client.async_transaction() as transaction_ctx:
            analysis_data = await call_structured_analysis_async(
                analyzer, content, is_chunk=False, transaction_ctx=transaction_ctx)
    
    # If we didn't get a valid analysis, return insufficient text analysis
    if analysis_data is None:
        return create_insufficient_text_analysis()
    
    return analysis_data

async def _update_legislation_priority_async(analyzer: Any, legislation_id: int, analysis_data: Dict[str, Any]) -> None:
    """
    Asynchronously update legislation priority by running the synchronous version in an executor.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation
        analysis_data: Analysis data with impact information
    """
    # Get the event loop
    loop = asyncio.get_event_loop()
    
    # Define a function to run synchronously
    def update_priority_sync():
        try:
            update_legislation_priority(analyzer, legislation_id, analysis_data)
        except (ValueError, KeyError, AttributeError) as e:
            # Handle specific expected exceptions separately
            logger.error("Error updating legislation priority due to value/key/attribute error: %s", e)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # It's acceptable to broadly catch exceptions here since this is a background task
            # and we don't want errors to propagate and disrupt the main workflow
            logger.error("Unexpected error updating legislation priority: %s", e)
    
    # Run CPU-bound priority calculation in the executor
    await loop.run_in_executor(None, update_priority_sync)
