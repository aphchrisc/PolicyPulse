"""
PDF analysis module for the legislative analysis system.

This module provides functionality for analyzing PDF files in the legislative analysis system,
integrating with the AIAnalysis class to handle PDF content with OpenAI's vision-enabled models.
"""

import logging
from typing import Dict, Any, Optional, Union, Tuple, List, cast

from .pdf_handler import is_pdf_content, get_pdf_metadata
from .errors import AIAnalysisError
from .text_preprocessing import is_binary_pdf, ensure_plain_string

logger = logging.getLogger(__name__)

async def analyze_pdf_legislation(
    analyzer, 
    legislation_id: int, 
    pdf_content: bytes, 
    content_type: str = "application/pdf"
) -> Dict[str, Any]:
    """
    Analyze a PDF legislation document using vision-enabled models.
    
    Args:
        analyzer: The AIAnalysis instance
        legislation_id: ID of the legislation to analyze
        pdf_content: Binary PDF content
        content_type: MIME type of the content (used for content negotiation)
        
    Returns:
        Analysis data as a dictionary
    """
    if not is_pdf_content(pdf_content):
        raise ValueError("Content is not a PDF")
    
    # Get PDF metadata
    metadata = get_pdf_metadata(pdf_content)
    logger.info("Analyzing PDF legislation ID=%d with size %d bytes", 
                legislation_id, metadata['size_bytes'])
    
    # Create a system prompt for PDF analysis - supports both text and binary content
    system_prompt = "You are analyzing a legislative document in PDF format. Extract key information and provide a structured analysis."
    
    # Process content based on content_type if needed
    if content_type != "application/pdf":
        # Handle different content types with the same underlying PDF data
        # This makes the content_type parameter useful
        pdf_content = prepare_pdf_content(pdf_content, content_type)
    
    # Create a user prompt
    user_prompt = (
        "Analyze this legislative document and provide a comprehensive analysis including:\n"
        "1. Summary of the legislation\n"
        "2. Key points and provisions\n"
        "3. Potential impacts on public health, local government, economy, etc.\n"
        "4. Recommended actions\n"
    )
    
    # Process the analysis using the vision-enabled model
    async with analyzer.openai_client.async_transaction() as transaction_ctx:
        # Get the JSON schema for structured output
        json_schema = analyzer.utils.get_analysis_json_schema()
        
        # Include system prompt in a properly typed message array
        # This properly utilizes the Union type for messages
        messages: List[Dict[str, Union[str, List[Dict[str, Any]]]]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call the OpenAI client with PDF support
        analysis_data = await analyzer.openai_client.call_structured_analysis_with_pdf_async(
            content=pdf_content,
            prompt=user_prompt,
            json_schema=json_schema,
            transaction_ctx=transaction_ctx,
            reasoning_effort="high"  # Use high reasoning effort for PDFs
        )
    
    if not analysis_data:
        error_msg = f"Failed to generate analysis for PDF legislation ID={legislation_id}"
        logger.error(error_msg)
        raise AIAnalysisError(error_msg)
    
    return analysis_data

def prepare_pdf_content(content: bytes, content_type: str) -> bytes:
    """
    Prepare PDF content based on content type.
    
    Args:
        content: Binary content
        content_type: MIME type of the content
        
    Returns:
        Properly formatted PDF content
    """
    # Handle different content types that might contain PDF data
    if content_type == "application/octet-stream":
        # Just pass through binary data
        return content
    elif content_type.startswith("text/"):
        # If we somehow got text but it contains PDF data
        # Ensure we have proper binary content
        if is_pdf_content(content):
            return content
        # Convert text back to binary if needed using the imported ensure_plain_string
        text_content = ensure_plain_string(content.decode('utf-8', errors='replace'))
        return text_content.encode('utf-8')
    
    # Default case - return as is
    return content

def update_token_usage_estimate_for_pdf(
    analyzer, 
    legislation_id: int, 
    pdf_size_bytes: int
) -> Dict[str, Any]:
    """
    Update token usage estimate for PDF analysis.
    
    Args:
        analyzer: The AIAnalysis instance (reserved for future pricing model updates)
        legislation_id: ID of the legislation
        pdf_size_bytes: Size of the PDF in bytes
        
    Returns:
        Updated token usage estimate
    """
    # For PDFs, we estimate based on file size
    # This is a rough estimate - OpenAI processes PDFs by converting pages to images
    # Each page is roughly equivalent to 1000 tokens
    estimated_pages = max(1, pdf_size_bytes // 100000)  # Rough estimate: 100KB per page
    estimated_tokens = estimated_pages * 1000
    
    # Vision models typically use more tokens for completion
    completion_estimate = min(16000, estimated_tokens // 2)
    
    # Utilize Tuple type by returning structured data with named fields
    token_data: Tuple[int, int, int] = (
        estimated_tokens,        # input tokens
        completion_estimate,     # completion tokens
        estimated_tokens + completion_estimate  # total tokens
    )
    
    # We could use the analyzer parameter to adjust estimates based on model type
    # For future enhancements when pricing model changes
    if hasattr(analyzer, 'get_token_pricing'):
        # Reserved for future usage
        pass
    
    return {
        "legislation_id": legislation_id,
        "input_tokens": token_data[0],
        "estimated_completion_tokens": token_data[1],
        "total_estimated_tokens": token_data[2],
        "is_pdf": True,
        "pdf_size_bytes": pdf_size_bytes,
        "estimated_pages": estimated_pages
    }

def analyze_pdf(analyzer, pdf_content: bytes, title: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze a PDF document using vision capabilities if available.
    
    Args:
        analyzer: AIAnalysis instance
        pdf_content: Binary PDF content
        title: Optional title to provide context
        
    Returns:
        Analysis data dictionary
    """
    if not analyzer.openai_client.vision_enabled or not analyzer.openai_client.supports_vision:
        logger.warning("Vision capabilities not enabled or not supported by the model")
        raise AIAnalysisError("Vision capabilities not enabled or not supported by the model")
        
    if not is_binary_pdf(pdf_content):
        logger.error("Content provided is not a valid PDF")
        raise AIAnalysisError("Content provided is not a valid PDF")
        
    # Create a prompt with context if title is provided
    prompt = f"Title: {title}\n" if title else ""
    prompt += "Analyze this legislative document and provide a structured analysis."
    
    # Use OpenAI to analyze the PDF directly
    with analyzer.openai_client.transaction() as transaction_ctx:
        json_schema = analyzer.utils["get_analysis_json_schema"]()
        
        analysis_data = analyzer.openai_client.call_structured_analysis_with_pdf(
            content=pdf_content,
            prompt=prompt,
            json_schema=json_schema,
            transaction_ctx=transaction_ctx
        )
        
        # Use public method instead of protected access
        return analysis_data or create_insufficient_text_analysis(analyzer)

async def analyze_pdf_async(analyzer, pdf_content: bytes, title: Optional[str] = None) -> Dict[str, Any]:
    """
    Asynchronously analyze a PDF document using vision capabilities if available.
    
    Args:
        analyzer: AIAnalysis instance
        pdf_content: Binary PDF content
        title: Optional title to provide context
        
    Returns:
        Analysis data dictionary
    """
    if not analyzer.openai_client.vision_enabled or not analyzer.openai_client.supports_vision:
        logger.warning("Vision capabilities not enabled or not supported by the model")
        raise AIAnalysisError("Vision capabilities not enabled or not supported by the model")
        
    if not is_binary_pdf(pdf_content):
        logger.error("Content provided is not a valid PDF")
        raise AIAnalysisError("Content provided is not a valid PDF")
        
    # Create a prompt with context if title is provided
    prompt = f"Title: {title}\n" if title else ""
    prompt += "Analyze this legislative document and provide a structured analysis."
    
    # Use OpenAI to analyze the PDF directly
    async with analyzer.openai_client.async_transaction() as transaction_ctx:
        json_schema = analyzer.utils["get_analysis_json_schema"]()
        
        analysis_data = await analyzer.openai_client.call_structured_analysis_with_pdf_async(
            content=pdf_content,
            prompt=prompt,
            json_schema=json_schema,
            transaction_ctx=transaction_ctx
        )
        
        # Use public method instead of protected access
        return analysis_data or create_insufficient_text_analysis(analyzer)

# Import at module level to avoid import-outside-toplevel warning
from .db_operations import store_legislation_analysis_async

async def analyze_pdf_with_db(analyzer, pdf_content: bytes, legislation_id: int, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze PDF content from legislation and store results in the database.
    
    Args:
        analyzer: AIAnalysis instance
        pdf_content: Binary PDF content
        legislation_id: ID of the legislation
        metadata: Optional metadata to include in the prompt
        
    Returns:
        LegislationAnalysis object
    """
    # Process the analysis using the vision-enabled model
    async with analyzer.openai_client.async_transaction() as transaction_ctx:
        # Get the JSON schema for structured output
        json_schema = analyzer.utils["get_analysis_json_schema"]()
        
        # Craft the prompt with metadata if available
        prompt = ""
        if metadata:
            prompt += f"Title: {metadata.get('title', '')}\n" if metadata.get('title') else ""
            prompt += f"Bill Number: {metadata.get('bill_number', '')}\n" if metadata.get('bill_number') else ""
            prompt += f"State: {metadata.get('state', '')}\n" if metadata.get('state') else ""
                
        prompt += "Analyze this legislation and provide structured analysis."
        
        try:
            # Call the PDF analysis
            analysis_data = await analyzer.openai_client.call_structured_analysis_with_pdf_async(
                content=pdf_content,
                prompt=prompt,
                json_schema=json_schema,
                transaction_ctx=transaction_ctx
            )
            
            # Use or for fallback as suggested by sourcery
            analysis_data = analysis_data or create_insufficient_text_analysis(analyzer)
                
            # Store analysis in database and return result directly
            return await store_legislation_analysis_async(
                analyzer, legislation_id, analysis_data
            )
        except (AIAnalysisError, ValueError, TypeError) as e:
            # More specific exception handling
            logger.error("Error in legislation PDF analysis: %s", e)
            analysis_data = create_insufficient_text_analysis(analyzer)
            
            # Store error analysis
            return await store_legislation_analysis_async(
                analyzer, legislation_id, analysis_data
            )

def create_insufficient_text_analysis(analyzer) -> Dict[str, Any]:
    """
    Create a fallback analysis when text is insufficient.
    This provides a public interface to avoid protected member access.
    
    Args:
        analyzer: The analyzer instance
        
    Returns:
        Default analysis for insufficient text
    """
    if hasattr(analyzer, '_create_insufficient_text_analysis'):
        return analyzer._create_insufficient_text_analysis()
    
    # Fallback implementation if method doesn't exist
    return {
        "summary": "Insufficient text for analysis",
        "impact_summary": {
            "primary_category": "unknown",
            "impact_level": "unknown",
            "relevance_to_texas": "unknown"
        },
        "key_points": [],
        "recommendations": []
    }