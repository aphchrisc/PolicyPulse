"""
Bill analysis functionality.

This module contains methods for analyzing bill texts directly,
handling both textual and binary content.
"""

import logging
from typing import Dict, Any, Optional, Union

from .errors import AIAnalysisError, TokenLimitError, ContentProcessingError
from .text_preprocessing import preprocess_text, is_binary_pdf, ensure_plain_string
from .analysis_processing import (
    call_structured_analysis, 
    analyze_in_chunks,
    call_structured_analysis_async, 
    analyze_in_chunks_async
)

logger = logging.getLogger(__name__)


def analyze_bill(analyzer, 
                bill_text: Union[str, bytes], 
                bill_title: Optional[str] = None, 
                state: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze a bill's text directly (without DB storage).
    
    Args:
        analyzer: AIAnalysis instance
        bill_text: The text content of the bill
        bill_title: Optional title of the bill
        state: Optional state where the bill was introduced
        
    Returns:
        Dictionary with analysis results
        
    Raises:
        ValueError: If bill text is too short
        TokenLimitError: If bill text exceeds token limit
        AIAnalysisError: If analysis fails due to API issues
    """
    if not bill_text or len(bill_text) < 10:
        logger.warning("Bill text is too short or empty, cannot analyze")
        raise ValueError("Bill text is too short or empty")

    # Preprocess the text
    if isinstance(bill_text, bytes):
        is_binary = is_binary_pdf(bill_text)
        text_for_analysis = bill_text  # Keep as bytes for PDF handling
    else:
        is_binary = False
        # Convert to string if needed
        text_as_str = ensure_plain_string(bill_text)
        text_for_analysis, token_count = preprocess_text(analyzer, text_as_str)

        # Check token count for text content
        if not is_binary and token_count > analyzer.config.max_context_tokens:
            logger.warning("Bill text exceeds token limit: %s tokens", token_count)
            raise TokenLimitError(f"Bill text exceeds token limit of {analyzer.config.max_context_tokens}")

    # Add context information to the prompt
    context = {}
    if bill_title:
        context["title"] = bill_title
    if state:
        context["state"] = state

    # Get analysis result - create insufficient_analysis only once
    insufficient_analysis = get_insufficient_analysis(analyzer)

    # Analyze the content
    analysis_data = None
    if is_binary and isinstance(bill_text, bytes):
        analysis_data = _analyze_binary_bill(analyzer, bill_text, context)
    else:
        # Ensure we have a string for text analysis
        if isinstance(text_for_analysis, bytes):
            text_as_str = ensure_plain_string(text_for_analysis)
        else:
            text_as_str = text_for_analysis

        analysis_data = _analyze_text_bill(analyzer, text_as_str, context)

    # Return insufficient analysis if we failed to get a proper analysis
    return insufficient_analysis if analysis_data is None else analysis_data


async def analyze_bill_async(analyzer, 
                           bill_text: Union[str, bytes], 
                           bill_title: Optional[str] = None, 
                           state: Optional[str] = None) -> Dict[str, Any]:
    """
    Asynchronously analyze a bill's text directly (without DB storage).
    
    Args:
        analyzer: AIAnalysis instance
        bill_text: The text content of the bill
        bill_title: Optional title of the bill
        state: Optional state where the bill was introduced
        
    Returns:
        Dictionary with analysis results
        
    Raises:
        ValueError: If bill text is too short
        TokenLimitError: If bill text exceeds token limit
        AIAnalysisError: If analysis fails due to API issues
    """
    if not bill_text or len(bill_text) < 10:
        logger.warning("Bill text is too short or empty, cannot analyze")
        raise ValueError("Bill text is too short or empty")

    # Preprocess the text
    if isinstance(bill_text, bytes):
        is_binary = is_binary_pdf(bill_text)
        text_for_analysis = bill_text  # Keep as bytes for PDF handling
    else:
        is_binary = False
        # Convert to string if needed
        text_as_str = ensure_plain_string(bill_text)
        text_for_analysis, token_count = preprocess_text(analyzer, text_as_str)

        # Check token count for text content
        if not is_binary and token_count > analyzer.config.max_context_tokens:
            logger.warning("Bill text exceeds token limit: %s tokens", token_count)
            raise TokenLimitError(f"Bill text exceeds token limit of {analyzer.config.max_context_tokens}")

    # Add context information to the prompt
    context = {}
    if bill_title:
        context["title"] = bill_title
    if state:
        context["state"] = state

    # Get analysis result - create insufficient_analysis only once
    insufficient_analysis = get_insufficient_analysis(analyzer)

    # Analyze the content
    analysis_data = None
    if is_binary and isinstance(bill_text, bytes):
        analysis_data = await _analyze_binary_bill_async(analyzer, bill_text, context)
    else:
        # Ensure we have a string for text analysis
        if isinstance(text_for_analysis, bytes):
            text_as_str = ensure_plain_string(text_for_analysis)
        else:
            text_as_str = text_for_analysis

        analysis_data = await _analyze_text_bill_async(analyzer, text_as_str, context)

    # Return insufficient analysis if we failed to get a proper analysis
    return insufficient_analysis if analysis_data is None else analysis_data


def get_insufficient_analysis(analyzer) -> Dict[str, Any]:
    """
    Get a standardized insufficient analysis result.
    
    Args:
        analyzer: AIAnalysis instance
        
    Returns:
        Dictionary with insufficient analysis
    """
    try:
        # Use the method via public interface if available
        if hasattr(analyzer, "create_insufficient_text_analysis"):
            return analyzer.create_insufficient_text_analysis()
        
        # If no public method, we need to create our own insufficient analysis
        # rather than using the protected method directly
        return {
            "summary": "Insufficient text available for analysis.",
            "key_points": [{"point": "Insufficient text for detailed analysis", "impact_type": "neutral"}],
            "public_health_impacts": {
                "direct_effects": ["Unable to determine due to insufficient text"],
                "indirect_effects": ["Unable to determine due to insufficient text"],
                "funding_impact": ["Unable to determine due to insufficient text"],
                "vulnerable_populations": ["Unable to determine due to insufficient text"]
            },
            "local_government_impacts": {
                "administrative": ["Unable to determine due to insufficient text"],
                "fiscal": ["Unable to determine due to insufficient text"],
                "implementation": ["Unable to determine due to insufficient text"]
            },
            "economic_impacts": {
                "direct_costs": ["Unable to determine due to insufficient text"],
                "economic_effects": ["Unable to determine due to insufficient text"],
                "benefits": ["Unable to determine due to insufficient text"],
                "long_term_impact": ["Unable to determine due to insufficient text"]
            },
            "environmental_impacts": ["Unable to determine due to insufficient text"],
            "education_impacts": ["Unable to determine due to insufficient text"],
            "infrastructure_impacts": ["Unable to determine due to insufficient text"],
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
    except AttributeError as e:
        # If neither method is available, create a simple fallback
        logger.error("Error creating insufficient analysis: %s", e)
        return {
            "summary": "Insufficient text available for analysis.",
            "error": "Could not analyze document"
        }


def _analyze_binary_bill(analyzer, pdf_content: bytes, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Analyze a bill from binary PDF content.
    
    Args:
        analyzer: AIAnalysis instance
        pdf_content: Binary PDF content
        context: Optional context information
        
    Returns:
        Analysis data as a dictionary or None if analysis fails
    """
    # Add context to prompt if available
    context_str = ""
    if context:
        if title := context.get("title"):
            context_str += f"Title: {title}\n"
        if state := context.get("state"):
            context_str += f"State: {state}\n"
            
    # Create prompt with context
    prompt = f"{context_str}\nAnalyze this legislation document and provide a structured analysis."
    
    try:
        # Use PDF processing capability
        with analyzer.openai_client.transaction() as transaction_ctx:
            json_schema = analyzer.utils["get_analysis_json_schema"]()
            
            return analyzer.openai_client.call_structured_analysis_with_pdf(
                content=pdf_content,
                prompt=prompt,
                json_schema=json_schema,
                transaction_ctx=transaction_ctx
            )
    except (AIAnalysisError, TokenLimitError) as e:
        logger.error("Error analyzing binary bill: %s", e)
        return None
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Unexpected error analyzing binary bill: %s", e)
        return None


async def _analyze_binary_bill_async(analyzer, pdf_content: bytes, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Asynchronously analyze a bill from binary PDF content.
    
    Args:
        analyzer: AIAnalysis instance
        pdf_content: Binary PDF content
        context: Optional context information
        
    Returns:
        Analysis data as a dictionary or None if analysis fails
    """
    # Add context to prompt if available
    context_str = ""
    if context:
        if title := context.get("title"):
            context_str += f"Title: {title}\n"
        if state := context.get("state"):
            context_str += f"State: {state}\n"
            
    # Create prompt with context
    prompt = f"{context_str}\nAnalyze this legislation document and provide a structured analysis."
    
    try:
        # Use PDF processing capability
        async with analyzer.openai_client.async_transaction() as transaction_ctx:
            json_schema = analyzer.utils["get_analysis_json_schema"]()
            
            return await analyzer.openai_client.call_structured_analysis_with_pdf_async(
                content=pdf_content,
                prompt=prompt,
                json_schema=json_schema,
                transaction_ctx=transaction_ctx
            )
    except (AIAnalysisError, TokenLimitError) as e:
        logger.error("Error analyzing binary bill asynchronously: %s", e)
        return None
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Unexpected error analyzing binary bill asynchronously: %s", e)
        return None


def _analyze_text_bill(analyzer, text: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Analyze a bill from text content.
    
    Args:
        analyzer: AIAnalysis instance
        text: Text content of the bill
        context: Optional context information
        
    Returns:
        Analysis data as a dictionary or None if analysis fails
    """
    try:
        # Add context to prompt if available
        context_str = ""
        if context:
            if title := context.get("title"):
                context_str += f"Title: {title}\n"
            if state := context.get("state"):
                context_str += f"State: {state}\n"
                
        # Check token count
        token_count = analyzer.token_counter.count_tokens(text)
        safe_limit = analyzer.config.max_context_tokens - analyzer.config.safety_buffer
        
        # If token count is too high, use chunking
        if token_count > safe_limit:
            logger.info("Bill text exceeds safe token limit (%s > %s), using chunking", 
                       token_count, safe_limit)
            
            # Use the imported analyze_in_chunks via custom implementation
            chunks, has_structure = analyzer.text_chunker.chunk_text(text, safe_limit)
            
            # Create a mock legislation-like object for context
            mock_leg = type(
                'MockLegislation',
                (),
                {
                    'title': context.get("title") if context else "Untitled Bill",
                    'bill_number': "N/A",
                    'description': text[:200] + "..."
                }
            )()
            
            return analyze_in_chunks(analyzer, chunks, has_structure, mock_leg)
        else:
            # Analyze directly if within token limit
            text_with_context = f"{context_str}\n{text}" if context_str else text
            
            with analyzer.openai_client.transaction() as transaction_ctx:
                return call_structured_analysis(
                    analyzer, text_with_context, is_chunk=False, transaction_ctx=transaction_ctx
                )
    except (AIAnalysisError, TokenLimitError, ContentProcessingError) as e:
        logger.error("Error analyzing text bill: %s", e)
        return None
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Unexpected error analyzing text bill: %s", e)
        return None


async def _analyze_text_bill_async(analyzer, text: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Asynchronously analyze a bill from text content.
    
    Args:
        analyzer: AIAnalysis instance
        text: Text content of the bill
        context: Optional context information
        
    Returns:
        Analysis data as a dictionary or None if analysis fails
    """
    try:
        # Add context to prompt if available
        context_str = ""
        if context:
            if title := context.get("title"):
                context_str += f"Title: {title}\n"
            if state := context.get("state"):
                context_str += f"State: {state}\n"
                
        # Check token count
        token_count = analyzer.token_counter.count_tokens(text)
        safe_limit = analyzer.config.max_context_tokens - analyzer.config.safety_buffer
        
        # If token count is too high, use chunking
        if token_count > safe_limit:
            logger.info("Bill text exceeds safe token limit (%s > %s), using chunking async", 
                       token_count, safe_limit)
            
            # Use the imported analyze_in_chunks_async via wrapper
            chunks, has_structure = analyzer.text_chunker.chunk_text(text, safe_limit)
            
            # Create a mock legislation-like object for context
            mock_leg = type(
                'MockLegislation',
                (),
                {
                    'title': context.get("title") if context else "Untitled Bill",
                    'bill_number': "N/A",
                    'description': text[:200] + "..."
                }
            )()
            
            return await analyze_in_chunks_async(analyzer, chunks, has_structure, mock_leg)
        else:
            # Analyze directly if within token limit
            text_with_context = f"{context_str}\n{text}" if context_str else text
            
            return await call_structured_analysis_async(
                analyzer, text_with_context, is_chunk=False
            )
    except (AIAnalysisError, TokenLimitError, ContentProcessingError) as e:
        logger.error("Error analyzing text bill asynchronously: %s", e)
        return None
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error("Unexpected error analyzing text bill asynchronously: %s", e)
        return None 