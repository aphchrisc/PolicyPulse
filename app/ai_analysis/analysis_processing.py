"""
Core analysis processing functionality.

This module contains the methods for processing and analyzing content,
handling both text and binary content, and managing the analysis workflow.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

from .errors import AIAnalysisError, TokenLimitError, ContentProcessingError
from .text_preprocessing import preprocess_text, is_binary_pdf, ensure_plain_string

logger = logging.getLogger(__name__)


def extract_content_from_legislation(analyzer, leg_obj: Any) -> Tuple[Union[str, bytes], bool]:
    """
    Extract content from a legislation object and determine if it's binary.
    
    Args:
        analyzer: AIAnalysis instance
        leg_obj: Legislation object from database
        
    Returns:
        Tuple of (content, is_binary)
    """
    try:
        # Attempt to get full text from the latest_text or fallback to description
        text_rec = getattr(leg_obj, 'latest_text', None)
        if text_rec and getattr(text_rec, 'text_content', None) is not None:
            is_binary = getattr(text_rec, 'is_binary', False)
            content_type = getattr(text_rec, 'content_type', None)
            
            # Check if it's a PDF and we have vision capabilities
            if (is_binary and content_type == 'application/pdf' and 
                    analyzer.openai_client.vision_enabled and analyzer.openai_client.supports_vision):
                logger.info("Using vision-enabled analysis for PDF in LegislationText ID=%s", getattr(text_rec, 'id', 'unknown'))
                
                # Get the raw binary content
                if isinstance(text_rec.text_content, bytes):
                    content = text_rec.text_content
                else:
                    try:
                        content = text_rec.text_content.encode('utf-8')
                    except (AttributeError, UnicodeEncodeError) as e:
                        logger.error("Failed to get binary content from LegislationText ID=%s: %s", 
                                     getattr(text_rec, 'id', 'unknown'), e)
                        content = ensure_plain_string(leg_obj.description)
                        is_binary = False
            elif is_binary:
                # Binary but not PDF or no vision capabilities
                logger.warning("Binary content in LegislationText ID=%s, using description", 
                              getattr(text_rec, 'id', 'unknown'))
                content = ensure_plain_string(leg_obj.description)
                is_binary = False
            else:
                # Regular text content
                content = ensure_plain_string(text_rec.text_content)
        else:
            content = ensure_plain_string(
                leg_obj.description if hasattr(leg_obj, 'description') and leg_obj.description is not None else ""
            )
            is_binary = False
            
        return content, is_binary
    except Exception as e:
        logger.error("Error extracting content from legislation: %s", e)
        raise AIAnalysisError(f"Failed to extract content from legislation: {str(e)}") from e


def process_analysis(analyzer, content: Union[str, bytes], is_binary: bool, 
                     legislation_id: int, leg_obj: Any) -> Dict[str, Any]:
    """
    Process content for analysis based on its type.
    
    Args:
        analyzer: AIAnalysis instance
        content: Content to analyze (text or binary)
        is_binary: Whether the content is binary (used by callers in legislation_analyzer.py and async_analysis.py)
        legislation_id: ID of the legislation
        leg_obj: Legislation object
        
    Returns:
        Analysis data as a dictionary
    """
    try:
        # For binary PDF content
        if is_binary_pdf(content) and analyzer.openai_client.vision_enabled and analyzer.openai_client.supports_vision:
            logger.info("Processing binary PDF content for legislation ID=%d", legislation_id)
            
            # Use OpenAI to analyze the PDF directly
            with analyzer.openai_client.transaction() as transaction_ctx:
                json_schema = analyzer.utils["get_analysis_json_schema"]()
                user_prompt = analyzer.utils["create_user_prompt"]("", is_chunk=False)
                
                try:
                    analysis_data = analyzer.openai_client.call_structured_analysis_with_pdf(
                        content=content,
                        prompt=user_prompt,
                        json_schema=json_schema,
                        transaction_ctx=transaction_ctx
                    )
                    # pylint: disable=protected-access
                    if analysis_data is None:
                        return analyzer._create_insufficient_text_analysis()
                    return analysis_data
                except Exception as e:
                    logger.error("Error analyzing PDF content: %s", e)
                    raise AIAnalysisError(f"Error analyzing PDF content: {str(e)}") from e
        else:
            # For text content
            if isinstance(content, bytes):
                try:
                    text_content = content.decode('utf-8')
                except UnicodeDecodeError as e:
                    logger.error("Failed to decode binary content for legislation ID=%d: %s", 
                                legislation_id, e)
                    text_content = ensure_plain_string(leg_obj.description if hasattr(leg_obj, 'description') else "")
            else:
                text_content = ensure_plain_string(content)
            
            # Preprocess text and get token count
            text_for_analysis, token_count = preprocess_text(analyzer, text_content)
            
            # Check if we have enough text to analyze
            if token_count < 300:
                logger.info("Token count (%d) below threshold; marking as insufficient text.", token_count)
                # pylint: disable=protected-access
                return analyzer._create_insufficient_text_analysis()
            elif token_count > analyzer.config.max_context_tokens:
                logger.warning("Content exceeds token limit: %d tokens. Using chunking.", token_count)
                safe_limit = analyzer.config.max_context_tokens - analyzer.config.safety_buffer
                try:
                    chunks, has_structure = analyzer.text_chunker.chunk_text(text_for_analysis, safe_limit)
                    
                    # Common analysis code for both single and multiple chunks
                    analysis_data = None
                    if len(chunks) == 1:
                        text_for_analysis = chunks[0]
                        analysis_data = call_structured_analysis(analyzer, text_for_analysis)
                    else:
                        analysis_data = analyze_in_chunks(analyzer, chunks, has_structure, leg_obj)
                        
                    # pylint: disable=protected-access
                    if analysis_data is None:
                        return analyzer._create_insufficient_text_analysis()
                    return analysis_data
                except Exception as e:
                    logger.error("Error chunking content: %s", e)
                    raise ContentProcessingError(f"Error chunking content: {str(e)}") from e
            else:
                # Content is within token limits, analyze directly
                analysis_data = call_structured_analysis(analyzer, text_for_analysis)
                # pylint: disable=protected-access
                if analysis_data is None:
                    return analyzer._create_insufficient_text_analysis()
                return analysis_data
    except AIAnalysisError:
        # Re-raise existing AIAnalysisError instances
        raise
    except Exception as e:
        logger.error("Error processing analysis: %s", e)
        raise AIAnalysisError(f"Error processing analysis: {str(e)}") from e


def call_structured_analysis(analyzer, text: str, is_chunk: bool = False, transaction_ctx: Any = None) -> Optional[Dict[str, Any]]:
    """
    Call the OpenAI API to perform structured analysis on text.
    
    Args:
        analyzer: AIAnalysis instance
        text: Text to analyze
        is_chunk: Whether this is a chunk of a larger text
        transaction_ctx: Optional transaction context
        
    Returns:
        Analysis data as a dictionary or None if analysis fails
    """
    try:
        json_schema = analyzer.utils["get_analysis_json_schema"]()
        system_message = analyzer.utils["create_analysis_instructions"](is_chunk=is_chunk)
        
        if is_chunk:
            user_prompt = analyzer.utils["create_chunk_prompt"](text)
        else:
            user_prompt = analyzer.utils["create_user_prompt"](text, is_chunk=False)
        
        with analyzer.openai_client.transaction() as ctx:
            transaction_context = transaction_ctx or ctx
            
            # Prepare messages for the API
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
            
            # Call the API
            return analyzer.openai_client.call_structured_analysis(
                messages=messages,
                json_schema=json_schema,
                transaction_ctx=transaction_context
            )
    except Exception as e:
        logger.error("Error in structured analysis: %s", e)
        raise AIAnalysisError(f"Error in structured analysis: {str(e)}") from e


def analyze_in_chunks(analyzer, chunks: List[str], has_structure: bool, leg_obj: Any) -> Optional[Dict[str, Any]]:
    """
    Analyze text in chunks and merge the results.
    
    Args:
        analyzer: AIAnalysis instance
        chunks: List of text chunks to analyze
        has_structure: Whether the text has a discoverable structure
        leg_obj: Legislation object
        
    Returns:
        Merged analysis data or None if analysis fails
    """
    logger.info("Analyzing in %d chunks", len(chunks))
    chunk_analyses = []
    
    try:
        with analyzer.openai_client.transaction() as transaction_ctx:
            for i, chunk in enumerate(chunks):
                logger.info("Analyzing chunk %d/%d", i+1, len(chunks))
                try:
                    chunk_analysis = call_structured_analysis(
                        analyzer, chunk, is_chunk=True, transaction_ctx=transaction_ctx
                    )
                    if chunk_analysis:
                        chunk_analyses.append(chunk_analysis)
                except AIAnalysisError as e:
                    logger.error("Error analyzing chunk %d: %s", i+1, e)
                    # Continue with other chunks even if one fails
        
        # If we have no valid analyses, raise an error
        if not chunk_analyses:
            logger.warning("No valid chunk analyses generated")
            raise ContentProcessingError("Failed to generate any valid chunk analyses")
            
        # Merge chunk analyses into a single analysis
        metadata = {
            "legislation_title": getattr(leg_obj, 'title', None),
            "legislation_number": getattr(leg_obj, 'bill_number', None),
            "chunks_analyzed": len(chunks)
        }
        
        merged_analysis = analyzer.utils["merge_analyses"](chunk_analyses, metadata, has_structure)
        logger.info("Successfully merged %d chunk analyses", len(chunk_analyses))
        
        return merged_analysis
    except AIAnalysisError:
        # Re-raise existing AIAnalysisError instances
        raise
    except Exception as e:
        logger.error("Error analyzing in chunks: %s", e)
        raise ContentProcessingError(f"Error analyzing text in chunks: {str(e)}") from e


async def call_structured_analysis_async(analyzer, text: str, is_chunk: bool = False,
                                         transaction_ctx: Any = None) -> Optional[Dict[str, Any]]:
    """
    Asynchronously call the OpenAI API to perform structured analysis on text.
    
    Args:
        analyzer: AIAnalysis instance
        text: Text to analyze
        is_chunk: Whether this is a chunk of a larger text
        transaction_ctx: Optional transaction context
        
    Returns:
        Analysis data as a dictionary or None if analysis fails
    """
    try:
        json_schema = analyzer.utils["get_analysis_json_schema"]()
        system_message = analyzer.utils["create_analysis_instructions"](is_chunk=is_chunk)
        
        if is_chunk:
            user_prompt = analyzer.utils["create_chunk_prompt"](text)
        else:
            user_prompt = analyzer.utils["create_user_prompt"](text, is_chunk=False)
        
        async with analyzer.openai_client.async_transaction() as ctx:
            transaction_context = transaction_ctx or ctx
            
            # Prepare messages for the API
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
            
            # Call the API
            return await analyzer.openai_client.call_structured_analysis_async(
                messages=messages,
                json_schema=json_schema,
                transaction_ctx=transaction_context
            )
    except Exception as e:
        logger.error("Error in async structured analysis: %s", e)
        raise AIAnalysisError(f"Error in async structured analysis: {str(e)}") from e


async def analyze_in_chunks_async(analyzer, chunks: List[str], has_structure: bool, leg_obj: Any,
                                 transaction_ctx: Any = None) -> Optional[Dict[str, Any]]:
    """
    Asynchronously analyze text in chunks and merge the results.
    
    Args:
        analyzer: AIAnalysis instance
        chunks: List of text chunks to analyze
        has_structure: Whether the text has a discoverable structure
        leg_obj: Legislation object
        transaction_ctx: Optional transaction context
        
    Returns:
        Merged analysis data or None if analysis fails
    """
    logger.info("Analyzing in %d chunks asynchronously", len(chunks))
    
    try:
        # Define analysis function for a single chunk
        async def analyze_chunk(chunk_text, chunk_idx):
            logger.info("Analyzing chunk %d/%d", chunk_idx+1, len(chunks))
            try:
                return await call_structured_analysis_async(
                    analyzer, chunk_text, is_chunk=True, transaction_ctx=transaction_ctx
                )
            except AIAnalysisError as e:
                logger.error("Error in async chunk %d: %s", chunk_idx+1, e)
                return None
        
        # Create tasks for all chunks
        tasks = [analyze_chunk(chunk, i) for i, chunk in enumerate(chunks)]
        
        # Execute all tasks concurrently
        chunk_analyses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and None results
        valid_analyses = []
        for i, result in enumerate(chunk_analyses):
            if isinstance(result, Exception):
                logger.error("Error in chunk %d: %s", i+1, result)
            elif result is not None:
                valid_analyses.append(result)
                
        # If we have no valid analyses, raise an error
        if not valid_analyses:
            logger.warning("No valid chunk analyses generated")
            raise ContentProcessingError("Failed to generate any valid chunk analyses asynchronously")
        
        # Merge chunk analyses into a single analysis
        metadata = {
            "legislation_title": getattr(leg_obj, 'title', None),
            "legislation_number": getattr(leg_obj, 'bill_number', None),
            "chunks_analyzed": len(chunks)
        }
        
        merged_analysis = analyzer.utils["merge_analyses"](valid_analyses, metadata, has_structure)
        logger.info("Successfully merged %d chunk analyses asynchronously", len(valid_analyses))
        
        return merged_analysis
    except AIAnalysisError:
        # Re-raise existing AIAnalysisError instances
        raise
    except Exception as e:
        logger.error("Error in async chunked analysis: %s", e)
        raise ContentProcessingError(f"Error in async chunked analysis: {str(e)}") from e 