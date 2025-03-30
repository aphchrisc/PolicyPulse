"""
Asynchronous analysis functionality.

This module contains asynchronous methods for analyzing legislation,
including batch processing and async utilities.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Tuple

from .errors import AIAnalysisError
from .text_preprocessing import is_binary_pdf, ensure_plain_string, preprocess_text
from .analysis_processing import (
    extract_content_from_legislation,
    call_structured_analysis_async,
    analyze_in_chunks_async
)
from .bill_analysis import analyze_bill_async
from .db_operations import get_cached_analysis, get_legislation_object, store_legislation_analysis_async
from .impact_analysis import update_legislation_priority

logger = logging.getLogger(__name__)


async def analyze_legislation_async(analyzer, legislation_id: int) -> Any:
    """
    Asynchronously analyze legislation by ID, handling both text and PDF content.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation to analyze
        
    Returns:
        LegislationAnalysis object with the analysis results
    """
    # Check cache first
    if cached_analysis := get_cached_analysis(analyzer, legislation_id):
        return cached_analysis

    # Get legislation object from database
    leg_obj = get_legislation_object(analyzer, legislation_id)
    
    if leg_obj is None:
        error_msg = f"Legislation with ID={legislation_id} not found in the DB."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Extract content from legislation object
    content, is_binary = extract_content_from_legislation(analyzer, leg_obj)
    
    # Process the analysis based on content type
    analysis_data = await _process_analysis_async(analyzer, content, is_binary, legislation_id, leg_obj)
    
    # Store and return the analysis results
    return await _store_analysis_results_async(analyzer, legislation_id, analysis_data)


async def batch_analyze_async(analyzer, legislation_ids: List[int], max_concurrent: int = 5) -> Dict[str, Any]:
    """
    Analyze multiple legislation records in parallel.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_ids: List of legislation IDs to analyze
        max_concurrent: Maximum number of concurrent analyses
        
    Returns:
        Dictionary with analysis results and statistics
    """
    logger.info("Starting batch analysis of %d legislation records", len(legislation_ids))
    start_time = datetime.now(timezone.utc)
    
    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def analyze_with_semaphore(leg_id):
        async with semaphore:
            try:
                return await analyze_legislation_async(analyzer, leg_id)
            except (AIAnalysisError, ValueError, TypeError) as e:
                logger.error("Error analyzing legislation ID=%d: %s", leg_id, str(e))
                return {"error": str(e), "legislation_id": leg_id}
    
    # Create tasks for all legislation IDs
    tasks = [analyze_with_semaphore(leg_id) for leg_id in legislation_ids]
    
    # Execute all tasks and gather results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successful = []
    failed = []
    
    for i, result in enumerate(results):
        leg_id = legislation_ids[i]
        if isinstance(result, Exception):
            logger.error("Error in batch analysis for legislation ID=%d: %s", leg_id, str(result))
            failed.append({"legislation_id": leg_id, "error": str(result)})
        elif isinstance(result, dict) and "error" in result:
            logger.error("Error in batch analysis for legislation ID=%d: %s", leg_id, result['error'])
            failed.append(result)
        else:
            successful.append({"legislation_id": leg_id, "analysis": result})
    
    # Calculate statistics
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()
    
    return {
        "results": {
            "successful": successful,
            "failed": failed
        },
        "stats": {
            "total": len(legislation_ids),
            "success_count": len(successful),
            "failure_count": len(failed),
            "duration_seconds": duration,
            "avg_time_per_item": duration / len(legislation_ids) if legislation_ids else 0
        }
    }


async def _process_analysis_async(analyzer, content: Union[str, bytes], is_binary: bool, 
                                 legislation_id: int, leg_obj: Any) -> Dict[str, Any]:
    """
    Asynchronously process content for analysis based on its type.
    
    Args:
        analyzer: AIAnalysis instance
        content: Content to analyze (text or binary)
        is_binary: Whether the content is binary
        legislation_id: ID of the legislation
        leg_obj: Legislation object
        
    Returns:
        Analysis data as a dictionary
    """
    result: Optional[Dict[str, Any]] = None
    
    # For binary PDF content
    if is_binary_pdf(content) and analyzer.openai_client.vision_enabled and analyzer.openai_client.supports_vision:
        logger.info("Processing binary PDF content asynchronously for legislation ID=%d", legislation_id)
        
        # Use OpenAI to analyze the PDF directly
        async with analyzer.openai_client.async_transaction() as transaction_ctx:
            json_schema = analyzer.utils["get_analysis_json_schema"]()
            user_prompt = analyzer.utils["create_user_prompt"]("", is_chunk=False)
            
            try:
                pdf_content = await _prepare_pdf_content(content)
                analysis_data = await analyzer.openai_client.call_structured_analysis_with_pdf_async(
                    content=pdf_content,
                    prompt=user_prompt,
                    json_schema=json_schema,
                    transaction_ctx=transaction_ctx
                )
                
                if analysis_data is None:
                    return create_insufficient_text_analysis(analyzer)
                return analysis_data
            except (AIAnalysisError, UnicodeError) as e:
                logger.error("Error analyzing PDF content asynchronously: %s", str(e))
                return create_insufficient_text_analysis(analyzer)
    else:
        # For text content
        if isinstance(content, bytes):
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                logger.error("Failed to decode binary content for legislation ID=%d", legislation_id)
                text_content = ensure_plain_string(leg_obj.description if hasattr(leg_obj, 'description') else "")
        else:
            text_content = ensure_plain_string(content)
        
        # Preprocess text and get token count
        text_for_analysis, token_count = preprocess_text(analyzer, text_content)
        
        # Check if we have enough text to analyze
        if token_count < 300:
            logger.info("Token count (%d) below threshold; marking as insufficient text.", token_count)
            return create_insufficient_text_analysis(analyzer)
        elif token_count > analyzer.config.max_context_tokens:
            logger.warning("Content exceeds token limit: %d tokens. Using chunking.", token_count)
            safe_limit = analyzer.config.max_context_tokens - analyzer.config.safety_buffer
            chunks, has_structure = analyzer.text_chunker.chunk_text(text_for_analysis, safe_limit)
            
            # Process based on number of chunks
            result = await _process_chunks_async(analyzer, chunks, has_structure, leg_obj)
        else:
            # Content is within token limits, analyze directly
            result = await call_structured_analysis_async(analyzer, text_for_analysis)
            
    return result if result is not None else create_insufficient_text_analysis(analyzer)


async def _process_chunks_async(analyzer, chunks: List[str], has_structure: bool, leg_obj: Any) -> Optional[Dict[str, Any]]:
    """
    Process text chunks asynchronously for analysis.
    
    Args:
        analyzer: AIAnalysis instance
        chunks: List of text chunks to analyze
        has_structure: Whether the text has recognizable structure
        leg_obj: Legislation object
        
    Returns:
        Analysis data as a dictionary or None if analysis fails
    """
    if len(chunks) == 1:
        analysis_data = await call_structured_analysis_async(analyzer, chunks[0])
        return analysis_data
    else:
        analysis_data = await analyze_in_chunks_async(analyzer, chunks, has_structure, leg_obj)
        return analysis_data


async def _prepare_pdf_content(content: Union[str, bytes]) -> bytes:
    """
    Prepare PDF content for analysis.
    
    Args:
        content: PDF content as string or bytes
        
    Returns:
        PDF content as bytes
    
    Raises:
        UnicodeError: If string content cannot be encoded to bytes
    """
    if isinstance(content, str):
        return content.encode('utf-8')
    return content


def create_insufficient_text_analysis(analyzer) -> Dict[str, Any]:
    """
    Create a placeholder analysis for cases with insufficient text.
    
    Args:
        analyzer: AIAnalysis instance
        
    Returns:
        A minimal analysis data structure
    """
    return {
        "summary": "INSUFFICIENT_TEXT_FOR_ANALYSIS",
        "impact_summary": {
            "primary_category": "public_health",
            "impact_level": "low",
            "relevance_to_texas": "low"
        },
        "insufficient_text": True,
        "key_provisions": [],
        "stakeholders": [],
        "implementation_considerations": []
    }


async def _store_analysis_results_async(analyzer, legislation_id: int, analysis_data: Dict[str, Any]) -> Any:
    """
    Asynchronously store analysis results in the database.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation
        analysis_data: Analysis data to store
        
    Returns:
        LegislationAnalysis object with the analysis results
    """
    # If analysis_data is empty or None, create a minimal structure for insufficient text
    if not analysis_data:
        logger.warning("No analysis data generated for legislation ID=%d", legislation_id)
        analysis_data = create_insufficient_text_analysis(analyzer)
        
    # Check for special marker indicating insufficient text
    if analysis_data.get("summary") == "INSUFFICIENT_TEXT_FOR_ANALYSIS" or len(analysis_data.get("summary", "")) < 20:
        logger.warning("Insufficient text detected for legislation ID=%d", legislation_id)
        # Mark this as a special case
        analysis_data["insufficient_text"] = True
        analysis_data["summary"] = "Insufficient text available for detailed analysis."
        # Set minimal impact values
        analysis_data["impact_summary"] = {
            "primary_category": "public_health",
            "impact_level": "low",
            "relevance_to_texas": "low"
        }
    
    # Store analysis in database
    result_analysis = await store_legislation_analysis_async(analyzer, legislation_id, analysis_data)
    
    # Update cache with thread safety
    with analyzer._cache_lock:
        analyzer._analysis_cache[legislation_id] = (datetime.now(timezone.utc), result_analysis)
    
    # Update legislation priority if applicable
    if 'LegislationPriority' in globals() or hasattr(analyzer.models, 'LegislationPriority'):
        # Run in a separate task to avoid blocking
        await _update_priority_async(analyzer, legislation_id, analysis_data)
    
    return result_analysis


async def _update_priority_async(analyzer, legislation_id: int, analysis_data: Dict[str, Any]) -> None:
    """
    Asynchronously update legislation priority.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation
        analysis_data: Analysis data with impact information
    """
    # Run synchronously but in a separate task
    loop = asyncio.get_event_loop()
    
    # Use the impact_analysis module that was already imported at the top level
    def update_priority_sync():
        try:
            # Use the imported function from the module level
            update_legislation_priority(analyzer, legislation_id, analysis_data)
        except (AIAnalysisError, ValueError, AttributeError) as e:
            logger.error("Error updating legislation priority: %s", str(e))
            
    # Run CPU-bound priority calculation in the executor
    await loop.run_in_executor(None, update_priority_sync)


async def analyze_bill_with_custom_options(analyzer, bill_id: int, options: Optional[Dict[str, Any]] = None) -> Tuple[Any, Dict[str, Any]]:
    """
    Analyze a bill with custom options using the bill_analysis module.
    
    Args:
        analyzer: AIAnalysis instance
        bill_id: ID of the bill to analyze
        options: Optional dictionary of analysis options
        
    Returns:
        A tuple of (analysis_result, metadata)
    """
    options = options or {}
    
    # First, retrieve the legislation text from the database
    leg_obj = get_legislation_object(analyzer, bill_id)
    
    if leg_obj is None:
        raise ValueError("Bill with ID=%d not found in the database" % bill_id)
    
    # Extract content from legislation object
    bill_text, is_binary = extract_content_from_legislation(analyzer, leg_obj)
    
    # Extract title and state for additional context if available
    bill_title = getattr(leg_obj, 'title', None)
    state = getattr(leg_obj, 'state', None)
    
    # Demonstrates proper use of the imported analyze_bill_async function
    analysis_result = await analyze_bill_async(
        analyzer, 
        bill_text=bill_text, 
        bill_title=bill_title,
        state=state,
        **options
    )
    
    # Track metadata about the analysis
    metadata = {
        "analysis_time": datetime.now(timezone.utc),
        "bill_id": bill_id,
        "options_used": options,
        "async_method": True
    }
    
    return analysis_result, metadata
    