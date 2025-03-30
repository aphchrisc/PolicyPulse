"""
PDF processing functionality for the OpenAI client.

This module extends the structured analysis client with PDF handling capabilities,
allowing for analysis of PDF content using OpenAI's document understanding capabilities.
"""

import base64
import time
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple, cast

# BytesIO is imported directly as it's used frequently
from io import BytesIO

# Move relative imports to the top
from .pdf_handler import encode_pdf_for_vision, is_pdf_content, prepare_vision_message
from .structured_analysis import StructuredAnalysisClient
from .errors import AIAnalysisError, ContentProcessingError

# Import OpenAI types - use contextlib.suppress to silence ImportError
import contextlib
with contextlib.suppress(ImportError):
    import openai

# Define type aliases to handle OpenAI types properly when they're available
# These are safer than using the imported types directly in annotations
MessageDict = Dict[str, Any]  # Fallback type for message dictionaries
SystemMessageDict = Dict[str, str]  # Simple dict for system messages
UserMessageDict = Dict[str, str]  # Simple dict for user messages

logger = logging.getLogger(__name__)


class PDFProcessingClient(StructuredAnalysisClient):
    """Client extension providing PDF processing capabilities."""

    def prepare_vision_message(self, content: Union[str, bytes], prompt: str) -> List[MessageDict]:
        """
        Prepare a message for vision-enabled models that can handle PDFs.
        
        Args:
            content: Text content or binary PDF content
            prompt: The prompt to send with the content
            
        Returns:
            List of message objects for the API call
        """
        if not self.vision_enabled or not self.supports_vision:
            # If vision not enabled or model doesn't support it, return text-only message
            return [
                {"role": "user", "content": f"{prompt}\n\nDocument content:\n{content if isinstance(content, str) else '[Binary content not supported]'}"}
            ]

        if not isinstance(content, bytes):
            # It's text, use regular text prompt
            return [{"role": "user", "content": f"{prompt}\n\nDocument content:\n{content}"}]
        
        # Check if it's a PDF
        if is_pdf_content(content):
            # It's a PDF, use our PDF handler
            vision_message = prepare_vision_message(content, prompt)
            # Just cast to Dict[str, Any] to ensure consistent return type
            return [cast(MessageDict, vision_message)]
        else:
            # It's some other binary format, not supported
            logger.warning("Binary content is not a PDF, falling back to text-only prompt")
            return [{"role": "user", "content": f"{prompt}\n\n[Binary content not supported]"}]
    
    def encode_pdf_content(self, pdf_content: bytes) -> str:
        """
        Encode PDF content for use with vision-enabled models.
        
        Args:
            pdf_content: Binary PDF content
            
        Returns:
            Base64-encoded data URL for the PDF
            
        Raises:
            ContentProcessingError: If encoding fails
        """
        try:
            if not is_pdf_content(pdf_content):
                raise ValueError("Content is not a PDF")
            return encode_pdf_for_vision(pdf_content)
        except Exception as e:
            # This is a more specific error from our error hierarchy
            raise ContentProcessingError(f"Failed to encode PDF content: {e}") from e
    
    def call_structured_analysis_with_pdf(
            self, 
            content: Union[str, bytes], 
            prompt: str, 
            json_schema: Dict[str, Any], 
            **kwargs
        ) -> Dict[str, Any]:
        """
        Process PDF content with direct file API first, then text extraction fallback.
        
        This method prioritizes using the OpenAI Responses API with direct PDF input to
        leverage vision capabilities for richer document understanding. Only if that fails,
        it falls back to text extraction.
        
        Args:
            content: Text content or binary PDF content
            prompt: The prompt to analyze the content
            json_schema: JSON schema for structured output
            **kwargs: Additional arguments for the API call
            
        Returns:
            Structured analysis as a dictionary
            
        Raises:
            AIAnalysisError: If analysis fails completely
        """
        if isinstance(content, bytes) and is_pdf_content(content):
            logger.info("Processing PDF content of size %d bytes", len(content))

            # First try using the responses API with direct PDF input
            try:
                # Check if the OpenAI client is available and properly configured
                if not hasattr(openai, 'OpenAI'):
                    logger.warning("OpenAI client doesn't support direct PDF processing")
                    raise ImportError("Required OpenAI version not available")

                # Encode PDF as base64
                base64_pdf = base64.b64encode(content).decode('utf-8')
                filename = f"document_{int(time.time())}.pdf"

                # Format system prompt with instructions for structured output
                system_prompt = f"You are an AI assistant that analyzes legislation documents. Provide a structured analysis following this JSON schema: {json.dumps(json_schema)}"

                # Use responses API with file input
                logger.info("Using responses API with direct PDF input (vision-enabled analysis)")
                
                start_time = time.time()
                
                # Use new responses API structure
                response = self.client.responses.create(
                    model=self.model_name,
                    input=[
                        {
                            "role": "system",
                            "content": [{"type": "input_text", "text": system_prompt}]
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_file", "filename": filename, "file_data": f"data:application/pdf;base64,{base64_pdf}"},
                                {"type": "input_text", "text": prompt}
                            ]
                        }
                    ],
                    text={"format": {"type": "json_object"}},
                    temperature=kwargs.get('temperature', 0.2)
                )
                elapsed_time = time.time() - start_time
                logger.info("Responses API call with PDF vision analysis completed in %.2fs", elapsed_time)

                # Try to get output text safely
                try:
                    if hasattr(response, 'output_text'):
                        return self._safe_json_load(response.output_text)
                    else:
                        # Fallback for different response formats
                        logger.warning("Unexpected response format, trying to extract text")
                        response_text = str(response)
                        return self._safe_json_load(response_text)
                except Exception as e:
                    logger.error("Failed to extract content from response: %s", e)
                    raise
                
            except (ValueError, TypeError, AttributeError, ImportError) as e:
                logger.error("Error using responses API for PDF: %s", e)
                logger.info("Falling back to text extraction method (vision capabilities disabled)")
                
                # Fall back to text extraction
                if extracted_text := self._extract_text_from_pdf(content):
                    logger.info("Using extracted text for analysis")

                    # Create structured message tuple for type consistency and tracking
                    message_tuple = self._create_api_message_tuple(
                        system_content="You are an AI assistant that analyzes legislation documents.",
                        user_content=f"{prompt}\n\nDocument content:\n{extracted_text}"
                    )

                    # Unpack the tuple into messages for the API call
                    system_message, user_message = message_tuple
                    api_messages = [system_message, user_message]

                    return self.call_structured_analysis(
                        messages=api_messages,
                        json_schema=json_schema,
                        **kwargs
                    )

        # Fallback to standard text processing - handles both non-PDF and PDF fallback cases
        if isinstance(content, bytes):
            # Try to decode binary content as text
            try:
                content = content.decode('utf-8', errors='replace')
            except ValueError as e:
                logger.error("Failed to decode binary content: %s", e)
                content = "[Binary content could not be processed]"

        # Create unified message setup for all code paths
        message_tuple = self._create_api_message_tuple(
            system_content="You are an AI assistant that analyzes legislation documents.",
            user_content=f"{prompt}\n\nDocument content:\n{content}"
        )

        # Unpack the tuple into messages for the API call
        system_message, user_message = message_tuple
        api_messages = [system_message, user_message]

        # Call the API with the prepared messages
        try:
            return self.call_structured_analysis(
                messages=api_messages,
                json_schema=json_schema,
                **kwargs
            )
        except Exception as e:
            # Convert generic exceptions to our specific error type for better error handling
            raise AIAnalysisError(f"Failed to analyze document: {e}") from e
    
    def _create_api_message_tuple(
        self,
        system_content: str,
        user_content: str
    ) -> Tuple[SystemMessageDict, UserMessageDict]:
        """
        Create a tuple of system and user messages for the OpenAI API.

        Args:
            system_content: Content for the system message
            user_content: Content for the user message

        Returns:
            Tuple of (system_message, user_message) dictionaries
        """
        system_message: SystemMessageDict = {
            "role": "system",
            "content": system_content
        }
        user_message: UserMessageDict = {
            "role": "user",
            "content": user_content
        }
        return (system_message, user_message)
    
    def _extract_text_from_pdf(self, pdf_content: bytes) -> Optional[str]:
        """
        Extract text from PDF using pdfminer with PyPDF2 fallback.

        Args:
            pdf_content: Binary PDF content

        Returns:
            Extracted text or None if extraction fails

        Raises:
            ContentProcessingError: For critical PDF processing errors
        """
        try:
            # Common setup for PDF extraction
            pdf_file = BytesIO(pdf_content)

            # Try pdfminer first if available
            try:
                # Import is inside the method for lazy loading - this is intentional to handle
                # optional dependencies that might not be installed in all environments
                # pylint: disable=import-outside-toplevel # Optional dependency
                from pdfminer.high_level import extract_text as pdfminer_extract_text  # noqa: E501

                text = pdfminer_extract_text(pdf_file)

                if text.strip():
                    logger.info("Successfully extracted %d characters from PDF using pdfminer", len(text))
                    return text

            except ImportError:
                logger.warning("pdfminer not available, trying PyPDF2")
            except (ValueError, IOError, TypeError) as e:
                logger.warning("pdfminer extraction failed: %s", e)

            # Fall back to PyPDF2
            try:
                # Import is inside the method for lazy loading of optional dependency
                # pylint: disable=import-outside-toplevel # Optional dependency
                from PyPDF2 import PdfReader

                # Reset the file position for the new reader
                pdf_file.seek(0)
                reader = PdfReader(pdf_file)
                text = ""

                for page in reader.pages:
                    if page_text := page.extract_text():
                        text += page_text + "\n\n"

                if text.strip():
                    logger.info("Successfully extracted %d characters from PDF using PyPDF2", len(text))
                    return text
            except ImportError:
                logger.warning("PyPDF2 not available for text extraction")
            except (ValueError, IOError, TypeError) as e:
                logger.warning("PyPDF2 extraction failed: %s", e)

            return None
        except (ValueError, IOError, TypeError, AttributeError) as e:
            # More specific exception types for better error handling
            logger.error("Error in PDF text extraction: %s", e)
            return None
    
    async def call_structured_analysis_with_pdf_async(
            self,
            content: Union[str, bytes],
            prompt: str,
            json_schema: Dict[str, Any],
            temperature: float = 0.2,
            reasoning_effort: Optional[str] = None,
            max_completion_tokens: Optional[int] = None,
            store: bool = True,
            transaction_ctx: Optional[Any] = None) -> Dict[str, Any]:
        """
        Asynchronously call OpenAI API for structured analysis of PDF content.
        
        This method prioritizes using the OpenAI Responses API with direct PDF input to 
        leverage vision capabilities. If that fails, it falls back to text extraction.
        This approach enables better understanding of document formatting, tables, and 
        other visual elements in legislation.
        
        Args:
            content: PDF content (bytes) or text content (str)
            prompt: User prompt for the analysis
            json_schema: JSON schema for the response
            temperature: Controls randomness (0-1)
            reasoning_effort: For o-series models, control reasoning depth
            max_completion_tokens: Cap on total tokens
            store: Whether to store completions
            transaction_ctx: Optional transaction context

        Returns:
            Structured analysis result or raises AIAnalysisError
        """
        # Fix the content size logging to handle both str and bytes correctly
        if isinstance(content, str):
            content_size = len(content.encode())
        else:
            content_size = len(content)
            
        logger.info(
            "Processing PDF content of size %d bytes with model %s (async)",
            content_size,
            self.model_name
        )

        # Check if content is a PDF
        if isinstance(content, bytes) and is_pdf_content(content):
            logger.info("Processing PDF content of size %d bytes with model %s (async)",
                       len(content), self.model_name)

            # First try processing with responses API if available
            if result := await self._try_process_pdf_with_responses_api_async(
                content, prompt, json_schema, temperature, reasoning_effort,
                max_completion_tokens
            ):
                return result

            # Then fall back to text extraction if responses API fails
            if result := await self._try_process_pdf_with_text_extraction_async(
                content, prompt, json_schema, temperature, reasoning_effort,
                max_completion_tokens, store, transaction_ctx
            ):
                return result

        # Default text processing fallback
        return await self._process_text_content_async(
            content, prompt, json_schema, temperature, reasoning_effort,
            max_completion_tokens, store, transaction_ctx
        )
    
    async def _try_process_pdf_with_text_extraction_async(
            self,
            content: bytes,
            prompt: str,
            json_schema: Dict[str, Any],
            temperature: float = 0.2,
            reasoning_effort: Optional[str] = None,
            max_completion_tokens: Optional[int] = None,
            store: bool = True,
            transaction_ctx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """
        Try to process PDF content by extracting text first.
        
        Args:
            content: Binary PDF content
            prompt: The prompt to analyze the content
            json_schema: JSON schema for structured output
            temperature: Controls randomness (0-1)
            reasoning_effort: For o-series models, control reasoning depth
            max_completion_tokens: Cap on total tokens
            store: Whether to store completions
            transaction_ctx: Optional transaction context
            
        Returns:
            Structured analysis as a dictionary or None if extraction fails
        """
        if extracted_text := self._extract_text_from_pdf(content):
            logger.info("Successfully extracted text from PDF, using text-based analysis as fallback (async)")
            
            # Create structured message tuple for type consistency and tracking
            message_tuple = self._create_api_message_tuple(
                system_content="You are an AI assistant that analyzes legislation documents.",
                user_content=f"{prompt}\n\nDocument content:\n{extracted_text}"
            )
            
            # Unpack the tuple into messages for the API call
            system_message, user_message = message_tuple
            api_messages = [system_message, user_message]

            return await self.call_structured_analysis_async(
                messages=api_messages,
                json_schema=json_schema,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                max_completion_tokens=max_completion_tokens,
                store=store,
                transaction_ctx=transaction_ctx
            )
        return None
    
    async def _try_process_pdf_with_responses_api_async(
            self,
            content: bytes,
            prompt: str,
            json_schema: Dict[str, Any],
            temperature: float = 0.2,
            reasoning_effort: Optional[str] = None,
            max_completion_tokens: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Try to process PDF content using the responses API.
        
        Args:
            content: Binary PDF content
            prompt: The prompt to analyze the content
            json_schema: JSON schema for structured output
            temperature: Controls randomness (0-1)
            reasoning_effort: For o-series models, control reasoning depth
            max_completion_tokens: Cap on total tokens
            
        Returns:
            Structured analysis as a dictionary or None if API unavailable
            
        Raises:
            ContentProcessingError: If PDF processing fails
        """
        try:
            # Check if OpenAI client supports async
            if not hasattr(openai, 'AsyncOpenAI') or not self.async_client:
                logger.warning("OpenAI client doesn't support async PDF processing")
                raise ImportError("Required OpenAI AsyncOpenAI client not available")
            
            # Encode PDF to base64
            base64_pdf = base64.b64encode(content).decode('utf-8')
            filename = f"document_{int(time.time())}.pdf"

            # Format the system message with instructions for structured output
            system_prompt = f"You are an AI assistant that analyzes legislation documents. Provide a structured analysis following this JSON schema: {json.dumps(json_schema)}"

            # Create the request parameters for the new OpenAI API structure
            logger.info("Using responses API for direct PDF analysis with vision capabilities (async)")
            start_time = time.time()
            
            try:
                # New API structure uses the responses method directly on the AsyncOpenAI client
                response = await self.async_client.responses.create(
                    model=self.model_name,
                    input=[
                        {
                            "role": "system", 
                            "content": [{"type": "input_text", "text": system_prompt}]
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_file", "filename": filename, "file_data": f"data:application/pdf;base64,{base64_pdf}"},
                                {"type": "input_text", "text": prompt}
                            ]
                        }
                    ],
                    text={"format": {"type": "json_object"}},
                    temperature=temperature
                )
                
                elapsed_time = time.time() - start_time
                logger.info("Async responses API call with PDF vision analysis completed in %.2fs", elapsed_time)

                # Parse the JSON response
                try:
                    # The response format may have changed
                    if hasattr(response, 'output_text'):
                        return self._safe_json_load(response.output_text)
                    else:
                        # Use a more defensive approach with try/except
                        try:
                            # Try different ways to extract text content from the response
                            output_text = None
                            
                            # Try standard response.output_text first
                            output_text = getattr(response, 'output_text', None)
                            
                            # If that failed, try to navigate the response object safely
                            if not output_text:
                                logger.warning("Response has no output_text attribute, trying fallback methods")
                                
                                # Use str() as a last resort to get something we can parse
                                response_text = str(response)
                                logger.info("Using string representation of response: %s...", response_text[:100])
                                return self._safe_json_load(response_text)
                                
                            return self._safe_json_load(output_text)
                        except Exception as e:
                            logger.error("Failed to extract content from response: %s", e)
                            return None
                except (ValueError, TypeError, json.JSONDecodeError) as e:
                    logger.error("Error parsing response from async responses API: %s", e)
                    raise ContentProcessingError(f"Failed to parse API response: {e}") from e
            except AttributeError as e:
                logger.error("AsyncOpenAI client missing expected attributes: %s", e)
                return None
                
        except (ValueError, TypeError, AttributeError, ImportError) as e:
            logger.error("Error using async responses API for PDF: %s", e)
            return None
    
    async def _process_text_content_async(
            self,
            content: Union[str, bytes],
            prompt: str,
            json_schema: Dict[str, Any],
            temperature: float = 0.2,
            reasoning_effort: Optional[str] = None,
            max_completion_tokens: Optional[int] = None,
            store: bool = True,
            transaction_ctx: Optional[Any] = None) -> Dict[str, Any]:
        """
        Process text content with the async API.
        
        Args:
            content: Text content or binary content to decode
            prompt: The prompt to analyze the content
            json_schema: JSON schema for structured output
            temperature: Controls randomness (0-1)
            reasoning_effort: For o-series models, control reasoning depth
            max_completion_tokens: Cap on total tokens
            store: Whether to store completions
            transaction_ctx: Optional transaction context
            
        Returns:
            Structured analysis as a dictionary
            
        Raises:
            AIAnalysisError: If analysis fails
        """
        # If content is binary, try to decode it as text
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8', errors='replace')
            except ValueError as e:
                logger.error("Failed to decode binary content: %s", e)
                content = "[Binary content could not be processed]"

        # Create unified messages
        message_tuple = self._create_api_message_tuple(
            system_content="You are an AI assistant that analyzes legislation documents.",
            user_content=f"{prompt}\n\nDocument content:\n{content}"
        )

        # Unpack the tuple into messages for the API call
        system_message, user_message = message_tuple
        api_messages = [system_message, user_message]

        # Call the API with the prepared messages
        try:
            return await self.call_structured_analysis_async(
                messages=api_messages,
                json_schema=json_schema,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                max_completion_tokens=max_completion_tokens,
                store=store,
                transaction_ctx=transaction_ctx
            )
        except Exception as e:
            # Convert generic exceptions to our specific error type for better error handling
            raise AIAnalysisError(f"Failed to analyze document: {e}") from e
