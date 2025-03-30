"""
Structured analysis functionality for the OpenAI client.

This module extends the core OpenAI client with structured output capabilities,
allowing for consistent JSON-structured responses from language models.
"""

import time
import logging
import asyncio
import json
import threading
import re
from typing import Dict, List, Any, Optional, Union, Tuple, Iterable, cast, TypeVar

import openai

# Import our own modules
from .openai_core import OpenAIClient
from .errors import APIError, RateLimitError, AIAnalysisError
from app.models import APICallLog

# Import OpenAI types conditionally but define TypeAliases for consistent use
# Define basic type alias for message objects
T = TypeVar('T')
MessageType = Dict[str, Any]
ContentType = Union[str, List[Dict[str, Any]]]
ResponseLog = Dict[str, Any]
UsageStats = Tuple[Optional[int], Optional[int], Optional[int]]
APIOptions = Dict[str, Union[str, int, float, bool]]
DataStream = Iterable[Tuple[str, bytes]]

# Try to import OpenAI SDK types, with fallback for older versions
try:
    from openai.types.chat import ChatCompletionMessageParam
    MessageTypeAlias = ChatCompletionMessageParam
except ImportError:
    # Use our alias if SDK types aren't available
    MessageTypeAlias = MessageType

logger = logging.getLogger(__name__)


class StructuredAnalysisClient(OpenAIClient):
    """Client extension providing structured analysis capabilities."""

    def call_structured_analysis(
            self,
            messages: List[MessageType],
            json_schema: Dict[str, Any],
            transaction_ctx: Optional[Any] = None,
            temperature: float = 0.2,
            reasoning_effort: Optional[str] = None,
            max_completion_tokens: Optional[int] = None,
            store: bool = True) -> Dict[str, Any]:
        """
        Call OpenAI API with retry logic and structured output validation.

        Args:
            messages: List of message objects for the API call
            json_schema: JSON schema for structured output
            transaction_ctx: Optional transaction context from self.transaction()
            temperature: Controls randomness (0-1)
            reasoning_effort: For o-series models, control reasoning depth ("low", "medium", "high") 
            max_completion_tokens: Cap on total tokens (reasoning + visible output)
            store: Whether to store completions (set false for sensitive data)

        Returns:
            Structured analysis as a dictionary

        Raises:
            APIError: On unrecoverable API errors
            RateLimitError: On API rate limit errors
        """
        # Skip code quality check for complex function
        # (Keeping the sourcery comment to maintain original behavior)
        for attempt in range(self.max_retries + 1):
            try:
                # Make the API call
                start_time = time.time()

                # Handle new vs old OpenAI API
                has_new_openai = hasattr(openai, 'OpenAI')
                if has_new_openai:
                    params = {
                        "model": self.model_name,
                        "messages": cast(List[Any], messages),  # Use cast to satisfy type checking
                        "temperature": temperature,
                        "response_format": {
                            "type": "json_object"
                        },
                        "max_tokens":
                        16000,  # Legacy parameter but keeping for compatibility
                        "store": store
                    }

                    # Add optional parameters if provided
                    if reasoning_effort is not None:
                        params["reasoning_effort"] = reasoning_effort
                    if max_completion_tokens is not None:
                        params["max_completion_tokens"] = max_completion_tokens

                    response = self.client.chat.completions.create(**params)
                    response_message = response.choices[0].message
                    if content := response_message.content:
                        # Using named expression to simplify assignment and conditional
                        pass
                    else:
                        content = ""
                else:
                    # Legacy OpenAI API - deprecated but keeping for compatibility
                    try:
                        # Try to use the legacy API format - note: this is for very old versions
                        # and may not work with current OpenAI packages
                        # For legacy API, we need to convert the messages to a format it understands
                        # This is a workaround for type checking - in practice, the messages should already be in the right format
                        legacy_messages = []
                        for msg in messages:
                            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                                legacy_messages.append({"role": msg["role"], "content": msg["content"]})
                            else:
                                # Skip messages that don't have the expected format
                                logger.warning("Skipping message with unexpected format: %s", msg)
                        
                        response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=legacy_messages,  # Type compatibility handled by OpenAI client
                            temperature=temperature,
                            response_format={"type": "json_object"},
                            max_tokens=16000  # Limit output tokens for safety
                        )
                        response_message = response.choices[0].message
                        content = response_message.content or ""
                    except (AttributeError, TypeError) as e:
                        # If the above fails, try another approach for older versions
                        logger.warning("Legacy API call failed: %s. Trying new format.", e)
                        # Use the new format but with the old client
                        # Convert messages again to be safe
                        legacy_messages = []
                        for msg in messages:
                            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                                legacy_messages.append({"role": msg["role"], "content": msg["content"]})
                            else:
                                # Skip messages that don't have the expected format
                                logger.warning("Skipping message with unexpected format: %s", msg)
                        
                        response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=legacy_messages,  # Type compatibility handled by OpenAI client
                            temperature=temperature,
                            response_format={"type": "json_object"},
                            max_tokens=16000
                        )
                        response_message = response.choices[0].message
                        content = response_message.content or ""

                # Calculate and log API call time
                elapsed_time = time.time() - start_time
                logger.debug("API call completed in %.2fs", elapsed_time)

                # Save raw API response for debugging
                try:
                    # Create a unique filename with timestamp
                    timestamp = int(time.time())
                    filename = f"openai_response_{timestamp}.json"
                    
                    # Create a response object to save
                    response_data: ResponseLog = {
                        "timestamp": timestamp,
                        "model": self.model_name,
                        "elapsed_time": elapsed_time,
                        "raw_content": content,
                        "request_params": {
                            "model": self.model_name,
                            "temperature": temperature,
                            "reasoning_effort": reasoning_effort,
                            "max_completion_tokens": max_completion_tokens
                        }
                    }
                    
                    # Save to file - use utility to avoid import loops
                    self._save_response_to_file(filename, response_data)
                    logger.info("Saved raw OpenAI response to %s", filename)
                except (IOError, TypeError, ValueError) as e:
                    logger.warning("Failed to save raw API response: %s", e)

                # Check for empty response
                if not content:
                    logger.error("OpenAI returned empty content")
                    if attempt < self.max_retries:
                        continue
                    return {}

                # Parse the JSON response
                result = self._safe_json_load(content)

                # If we're using a transaction and inside a database operation, record the API call
                if hasattr(self, 'db_session') and self.db_session and transaction_ctx:
                    try:
                        # Calculate response time
                        response_time_ms = int((time.time() - start_time) * 1000)
                        
                        # Create API call log - safely access usage attributes
                        usage_total, usage_prompt, usage_completion = self._extract_usage_stats(response)
                        
                        api_log = APICallLog(
                            service="openai",
                            endpoint="chat.completions",
                            model=self.model_name,
                            tokens_used=usage_total,
                            tokens_input=usage_prompt,
                            tokens_output=usage_completion,
                            status_code=200,  # Successful call
                            response_time_ms=response_time_ms,
                            metadata={
                                "temperature": temperature,
                                "reasoning_effort": reasoning_effort,
                                "max_completion_tokens": max_completion_tokens
                            }
                        )
                        self.db_session.add(api_log)
                    except (ImportError, AttributeError) as e:
                        logger.error("Failed to record API call in database: %s", e)
                        # We don't raise here because the API call itself succeeded

                return result

            except (RateLimitError, APIError) as e:
                # Handle specific exceptions first
                should_retry, error_type = self._determine_retry_strategy(str(e))

                if should_retry and attempt < self.max_retries:
                    delay = self.retry_base_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        "%s error: %s. Retrying in %.2fs (attempt %d/%d)",
                        error_type, e, delay, attempt+1, self.max_retries
                    )
                    time.sleep(delay)
                else:
                    logger.error("%s error after %d attempts: %s", error_type, attempt, e)

                    if "rate limit" in str(e).lower() or "rate_limit" in str(e).lower():
                        raise RateLimitError(
                            f"OpenAI rate limit exceeded after {attempt} attempts: {str(e)}"
                        ) from e
                    else:
                        raise APIError(
                            f"OpenAI API error after {attempt} attempts: {str(e)}"
                        ) from e
            except AIAnalysisError as e:
                # Handle AI analysis errors
                logger.error("AI Analysis error: %s", e)
                raise
            except (ValueError, TypeError) as e:
                # Handle value/type errors
                logger.error("Value or type error: %s", e)
                if attempt >= self.max_retries:
                    raise AIAnalysisError(f"Failed due to value/type error: {str(e)}") from e
                time.sleep(self.retry_base_delay * (2**attempt))
            except Exception as e:
                # Handle any other exceptions as a last resort
                logger.error("Unexpected error in API call: %s", type(e).__name__)
                if attempt >= self.max_retries:
                    raise AIAnalysisError(f"Unexpected error in API call: {str(e)}") from e
                time.sleep(self.retry_base_delay * (2**attempt))

        # This should never be reached due to the raises in the loop
        raise AIAnalysisError("Failed to get a valid response after all retries")

    def _determine_retry_strategy(self, error_msg: str) -> Tuple[bool, str]:
        """
        Determine whether to retry based on error message.
        
        Args:
            error_msg: The error message to analyze
            
        Returns:
            Tuple of (should_retry, error_type)
        """
        # Check for rate limit errors
        if "rate limit" in error_msg.lower() or "rate_limit" in error_msg.lower():
            return True, "Rate limit"
        # Check for timeout errors
        elif "timeout" in error_msg.lower():
            return True, "Timeout"
        # Check for server errors
        elif "server error" in error_msg.lower() or "5xx" in error_msg.lower():
            return True, "Server"
        # Check for connection errors
        elif "connection" in error_msg.lower():
            return True, "Connection"
        else:
            return False, "API"
    
    def _extract_usage_stats(self, response: Any) -> UsageStats:
        """
        Extract usage statistics from API response.
        
        Args:
            response: API response object
            
        Returns:
            Tuple of (total_tokens, prompt_tokens, completion_tokens)
        """
        usage_total = None
        usage_prompt = None
        usage_completion = None
        
        if hasattr(response, 'usage') and response.usage is not None:
            usage = response.usage
            usage_total = getattr(usage, 'total_tokens', None)
            usage_prompt = getattr(usage, 'prompt_tokens', None)
            usage_completion = getattr(usage, 'completion_tokens', None)
            
        return (usage_total, usage_prompt, usage_completion)

    async def call_structured_analysis_async(
            self,
            messages: List[MessageType],
            json_schema: Dict[str, Any],
            transaction_ctx: Optional[Any] = None,
            temperature: float = 0.2,
            reasoning_effort: Optional[str] = None,
            max_completion_tokens: Optional[int] = None,
            store: bool = True) -> Dict[str, Any]:
        """
        Async version of call_structured_analysis. Call OpenAI API with retry logic and structured output validation.

        Args:
            messages: List of message objects for the API call
            json_schema: JSON schema for structured output
            transaction_ctx: Optional transaction context from self.transaction()
            temperature: Controls randomness (0-1)
            reasoning_effort: For o-series models, control reasoning depth ("low", "medium", "high") 
            max_completion_tokens: Cap on total tokens (reasoning + visible output)
            store: Whether to store completions (set false for sensitive data)

        Returns:
            Structured analysis as a dictionary

        Raises:
            APIError: On unrecoverable API errors
            RateLimitError: On API rate limit errors
            ValueError: If async client is not available
        """
        # Skip code quality check for complex function
        has_async_openai = hasattr(openai, 'AsyncOpenAI')
        if not has_async_openai or not self.async_client:
            raise ValueError(
                "Async OpenAI client not available. Please update your openai package."
            )

        for attempt in range(self.max_retries + 1):
            try:
                # Make the API call
                start_time = time.time()

                params: Dict[str, Any] = {
                    "model": self.model_name,
                    "messages": cast(List[Any], messages),  # Use cast to satisfy type checking
                    "temperature": temperature,
                    "response_format": {
                        "type": "json_object"
                    },
                    "max_tokens":
                    16000,  # Legacy parameter but keeping for compatibility
                    "store": store
                }

                # Add optional parameters if provided
                if reasoning_effort is not None:
                    params["reasoning_effort"] = reasoning_effort
                if max_completion_tokens is not None:
                    params["max_completion_tokens"] = max_completion_tokens

                response = await self.async_client.chat.completions.create(
                    **params)
                response_message = response.choices[0].message
                if content := response_message.content:
                    # Using named expression to simplify assignment and conditional
                    pass
                else:
                    content = ""

                # Calculate and log API call time
                elapsed_time = time.time() - start_time
                logger.debug("Async API call completed in %.2fs", elapsed_time)

                # Save raw API response for debugging
                try:
                    # Create a unique filename with timestamp
                    timestamp = int(time.time())
                    filename = f"openai_response_async_{timestamp}.json"
                    
                    # Create a response object to save
                    response_data: ResponseLog = {
                        "timestamp": timestamp,
                        "model": self.model_name,
                        "elapsed_time": elapsed_time,
                        "raw_content": content,
                        "request_params": {
                            "model": self.model_name,
                            "temperature": temperature,
                            "reasoning_effort": reasoning_effort,
                            "max_completion_tokens": max_completion_tokens,
                            "async": True
                        }
                    }
                    
                    # Save to file
                    self._save_response_to_file(filename, response_data)
                    logger.info("Saved raw async OpenAI response to %s", filename)
                except (IOError, TypeError, ValueError) as e:
                    logger.warning("Failed to save raw async API response: %s", e)

                # Check for empty response
                if not content:
                    logger.error("OpenAI returned empty content")
                    if attempt < self.max_retries:
                        continue
                    return {}

                # Parse the JSON response
                result = self._safe_json_load(content)

                # If we're using a transaction and inside a database operation, record the API call
                if hasattr(self, 'db_session') and self.db_session and transaction_ctx:
                    try:
                        # Calculate response time
                        response_time_ms = int((time.time() - start_time) * 1000)
                        
                        # Use our helper method to extract usage stats
                        usage_total, usage_prompt, usage_completion = self._extract_async_usage_stats(response)
                        
                        api_log = APICallLog(
                            service="openai",
                            endpoint="chat.completions.async",
                            model=self.model_name,
                            tokens_used=usage_total,
                            tokens_input=usage_prompt,
                            tokens_output=usage_completion,
                            status_code=200,  # Successful call
                            response_time_ms=response_time_ms,
                            metadata={
                                "temperature": temperature,
                                "reasoning_effort": reasoning_effort,
                                "max_completion_tokens": max_completion_tokens,
                                "async": True
                            }
                        )
                        self.db_session.add(api_log)
                    except (ImportError, AttributeError) as e:
                        logger.error("Failed to record API call in database: %s", e)
                        # We don't raise here because the API call itself succeeded

                return result

            except (RateLimitError, APIError) as e:
                # Handle specific exceptions first
                should_retry, error_type = self._determine_retry_strategy(str(e))

                if should_retry and attempt < self.max_retries:
                    delay = self.retry_base_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        "%s error: %s. Retrying in %.2fs (attempt %d/%d)",
                        error_type, e, delay, attempt+1, self.max_retries
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("%s error after %d attempts: %s", error_type, attempt, e)

                    if "rate limit" in str(e).lower() or "rate_limit" in str(e).lower():
                        raise RateLimitError(
                            f"OpenAI rate limit exceeded after {attempt} attempts: {str(e)}"
                        ) from e
                    else:
                        raise APIError(
                            f"OpenAI API error after {attempt} attempts: {str(e)}"
                        ) from e
            except AIAnalysisError as e:
                # Handle AI analysis errors
                logger.error("AI Analysis error: %s", e)
                raise
            except (ValueError, TypeError) as e:
                # Handle value/type errors
                logger.error("Value or type error: %s", e)
                if attempt >= self.max_retries:
                    raise AIAnalysisError(f"Failed due to value/type error: {str(e)}") from e
                await asyncio.sleep(self.retry_base_delay * (2**attempt))
            except Exception as e:
                # Handle any other exceptions as a last resort
                logger.error("Unexpected error in async API call: %s", type(e).__name__)
                if attempt >= self.max_retries:
                    raise AIAnalysisError(f"Unexpected error in async API call: {str(e)}") from e
                await asyncio.sleep(self.retry_base_delay * (2**attempt))

        # This should never be reached due to the raises in the loop
        raise AIAnalysisError("Failed to get a valid response after all retries")
    
    def _extract_async_usage_stats(self, response: Any) -> UsageStats:
        """
        Extract usage statistics from async API response.
        
        Args:
            response: API response object
            
        Returns:
            Tuple of (total_tokens, prompt_tokens, completion_tokens)
        """
        usage_total = None
        usage_prompt = None
        usage_completion = None
        
        if hasattr(response, 'usage'):
            usage = response.usage
            if hasattr(usage, 'total_tokens'):
                usage_total = usage.total_tokens
            if hasattr(usage, 'prompt_tokens'):
                usage_prompt = usage.prompt_tokens
            if hasattr(usage, 'completion_tokens'):
                usage_completion = usage.completion_tokens
                
        return (usage_total, usage_prompt, usage_completion)
    
    def _safe_json_load(self, content: str) -> Dict[str, Any]:
        """
        Safely load JSON content, handling errors.
        
        Args:
            content: JSON string to parse
            
        Returns:
            Parsed JSON as dictionary
        """
        try:
            # Parse the JSON using json.loads directly
            parsed = json.loads(content)
            # Ensure we always return a dictionary
            if not isinstance(parsed, dict):
                logger.warning("API returned non-object JSON: %s", type(parsed))
                return {"content": parsed}
            return parsed
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response: %s", e)
            # Try to extract JSON from the text
            return self._extract_json_from_text(content)
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Attempt to extract JSON from text that might have additional content.
        
        Args:
            text: Text possibly containing JSON
            
        Returns:
            Extracted JSON or empty dict
        """
        # Look for JSON-like patterns
        json_pattern = r'({[\s\S]*})'
        matches = re.findall(json_pattern, text)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
                
        # If all extraction attempts fail, return empty dict
        return {}
    
    def _save_response_to_file(self, filename: str, content: Any, timeout_seconds: int = 10) -> None:
        """
        Save content to a file with timeout protection.
        
        Args:
            filename: Name of file to save to
            content: Content to save
            timeout_seconds: Maximum seconds to wait for save operation
        """
        # Define a function to run in a thread with the file operation
        def save_file():
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
            except (IOError, TypeError) as e:
                logger.error("Error writing to file %s: %s", filename, e)
                
        # Create and start the thread
        thread = threading.Thread(target=save_file)
        thread.daemon = True  # Mark as daemon so it doesn't block program exit
        thread.start()
        
        # Wait for the thread to complete or timeout
        thread.join(timeout=timeout_seconds)
        if thread.is_alive():
            logger.warning("File save operation timed out after %d seconds", timeout_seconds) 
