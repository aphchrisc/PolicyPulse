"""
Core OpenAI client functionality for making API calls with appropriate error handling.

This module provides the base OpenAI client with:
- Error handling and retries
- Transaction support
- Basic API operations
"""

import os
import json
import time
import logging
import re
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple, Iterable, cast, TypeVar
from contextlib import contextmanager, suppress, asynccontextmanager

# Import OpenAI with version checking
try:
    import openai
    from openai import OpenAI, AsyncOpenAI
    from openai.types.chat import ChatCompletionMessageParam
    from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
    HAS_NEW_OPENAI = hasattr(openai, 'OpenAI')
    HAS_ASYNC_OPENAI = hasattr(openai, 'AsyncOpenAI')
except ImportError as e:
    raise ImportError(
        "Failed to import OpenAI package. Please install with: pip install openai"
    ) from e

try:
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import SQLAlchemyError
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

from .errors import APIError, RateLimitError, AIAnalysisError, DatabaseError

logger = logging.getLogger(__name__)


class OpenAIClient:
    """ Base wrapper for OpenAI API client with retry logic and error handling. """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4o-2024-08-06",
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        db_session: Optional[Any] = None,
        vision_enabled: bool = True,
    ):
        """
        Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key
            model_name: Name of the model to use
            max_retries: Maximum number of retry attempts
            retry_base_delay: Base delay for exponential backoff
            db_session: Optional SQLAlchemy session for transaction support
            vision_enabled: Whether to enable vision features when supported
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key must be provided or set as OPENAI_API_KEY environment variable"
            )

        self.model_name = model_name
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.db_session = db_session
        self.vision_enabled = vision_enabled
        
        # Check if model supports vision capabilities
        self.supports_vision = any(model in self.model_name for model in ["gpt-4o", "gpt-4-vision"])

        # Initialize client based on OpenAI SDK version
        if HAS_NEW_OPENAI:
            self.client = OpenAI(api_key=self.api_key)
            if HAS_ASYNC_OPENAI:
                self.async_client = AsyncOpenAI(api_key=self.api_key)
            else:
                self.async_client = None
        else:
            openai.api_key = self.api_key
            self.client = openai
            self.async_client = None

    def set_db_session(self, db_session: Any) -> None:
        """
        Set the database session for transaction support.

        Args:
            db_session: SQLAlchemy session
        """
        self.db_session = db_session

    @contextmanager
    def transaction(self):
        """
        Provides a transaction context if a database session is available.
        If no session is available, yields a null context.

        Usage:
            with client.transaction() as transaction:
                # operations inside a transaction

        Yields:
            SQLAlchemy transaction context or null context
        """
        if HAS_SQLALCHEMY and self.db_session:
            transaction = self.db_session.begin_nested()
            try:
                yield transaction
            except Exception as e:
                logger.error(f"Error in transaction: {e}")

                if transaction.is_active:  # Make sure transaction is active before rollback
                    transaction.rollback()

                raise
            finally:
                # Ensure transaction is closed properly if not committed
                if transaction.is_active:
                    transaction.commit()

        else:
            # Null context if no session available
            try:
                yield None
            except Exception as e:
                logger.error(f"Error in null transaction context: {e}")
                raise
    
    @asynccontextmanager
    async def async_transaction(self):
        """
        Provides an async transaction context if a database session is available.
        If no session is available, yields a null context.

        Usage:
            async with client.async_transaction() as transaction:
                # async operations inside a transaction

        Yields:
            SQLAlchemy transaction context or null context
        """
        if HAS_SQLALCHEMY and self.db_session:
            transaction = self.db_session.begin_nested()
            try:
                yield transaction
            except Exception as e:
                logger.error(f"Error in async transaction: {e}")

                if transaction.is_active:  # Make sure transaction is active before rollback
                    transaction.rollback()

                raise
            finally:
                # Ensure transaction is closed properly if not committed
                if transaction.is_active:
                    transaction.commit()
        else:
            # Null context if no session available
            try:
                yield None
            except Exception as e:
                logger.error(f"Error in null async transaction context: {e}")
                raise
    
    def _safe_json_load(self, content: str) -> Dict[str, Any]:
        """
        Safely loads JSON from a string, handling various formats.

        Args:
            content: String containing JSON data (possibly with markdown or other formatting)

        Returns:
            Parsed JSON as a dictionary, or empty dict on error
        """
        if not content or not isinstance(content, str):
            logger.warning(
                "Empty or non-string content provided to JSON parser")
            return {}

        with suppress(json.JSONDecodeError):
            # First, try direct JSON parsing
            return json.loads(content)
        # If that fails, try to extract JSON from markdown code blocks
        # Look for ```json ... ``` or just ``` ... ``` patterns
        json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(json_pattern, content)

        if matches:
            # Try each match until we find valid JSON
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        # Last-ditch effort: look for anything that resembles a JSON object
        object_pattern = r"(\{[\s\S]*\})"
        matches = re.findall(object_pattern, content)

        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        logger.error(f"Failed to parse JSON from content: {content[:100]}...")
        return {}
        
    def call_structured_analysis(
        self, 
        messages: List[Dict[str, str]], 
        json_schema: Dict[str, Any],
        transaction_ctx: Any = None
    ) -> Optional[Dict[str, Any]]:
        """
        Call OpenAI API for structured analysis with retry logic.
        
        Args:
            messages: List of message objects to send to the API
            json_schema: JSON schema for the response
            transaction_ctx: Optional transaction context
            
        Returns:
            Structured analysis result or None if all retries fail
            
        Raises:
            APIError: If the API fails after retries
            RateLimitError: If rate limit is hit
        """
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    # Calculate exponential backoff delay
                    delay = self.retry_base_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying API call (attempt {attempt+1}/{self.max_retries+1}) after {delay:.2f}s delay")
                    time.sleep(delay)
                
                # Call the OpenAI API with the new client
                if HAS_NEW_OPENAI:
                    # Convert messages to the required format
                    api_messages = []
                    for msg in messages:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        api_messages.append({"role": role, "content": content})
                    
                    # Create response format object
                    response_format = {"type": "json_object"}
                    if "schema" in json_schema:
                        response_format["schema"] = json_schema["schema"]
                    
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=api_messages,
                        response_format=response_format,
                        temperature=0.2,
                    )
                    
                    # Extract content from the response
                    content = response.choices[0].message.content
                    if content is None:
                        logger.error("Received empty response from OpenAI API")
                        continue
                        
                    # Parse JSON from the response
                    try:
                        result = json.loads(content)
                        return result
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON from response: {content[:100]}...")
                        result = self._safe_json_load(content)
                        if result:
                            return result
                        continue
                else:
                    # Legacy OpenAI API
                    response = openai.ChatCompletion.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=0.2,
                    )
                    
                    # Extract content from the response
                    content = response["choices"][0]["message"]["content"]
                    if content is None:
                        logger.error("Received empty response from OpenAI API")
                        continue
                        
                    # Parse JSON from the response
                    try:
                        result = json.loads(content)
                        return result
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON from response: {content[:100]}...")
                        result = self._safe_json_load(content)
                        if result:
                            return result
                        continue
                    
            except Exception as e:
                error_type = type(e).__name__
                # Handle common error types
                if "RateLimitError" in error_type:
                    logger.warning(f"OpenAI rate limit hit: {e}")
                    if attempt == self.max_retries:
                        raise RateLimitError(f"Rate limit exceeded after {self.max_retries} retries: {str(e)}") from e
                elif "APIError" in error_type:
                    logger.error(f"OpenAI API error: {e}")
                    if attempt == self.max_retries:
                        raise APIError(f"API error after {self.max_retries} retries: {str(e)}") from e
                else:
                    logger.error(f"Unexpected error in API call: {e}")
                    if attempt == self.max_retries:
                        raise AIAnalysisError(f"Failed to complete API call after {self.max_retries} retries: {str(e)}") from e
        
        # If we get here, all retries failed
        logger.error(f"All {self.max_retries+1} attempts to call OpenAI API failed")
        return None
        
    async def call_structured_analysis_async(
        self, 
        messages: List[Dict[str, str]], 
        json_schema: Dict[str, Any],
        transaction_ctx: Any = None
    ) -> Optional[Dict[str, Any]]:
        """
        Asynchronously call OpenAI API for structured analysis with retry logic.
        
        Args:
            messages: List of message objects to send to the API
            json_schema: JSON schema for the response
            transaction_ctx: Optional transaction context
            
        Returns:
            Structured analysis result or None if all retries fail
            
        Raises:
            APIError: If the API fails after retries
            RateLimitError: If rate limit is hit
        """
        if not self.async_client and HAS_NEW_OPENAI:
            # Create async client if not already initialized
            self.async_client = AsyncOpenAI(api_key=self.api_key)
        elif not HAS_ASYNC_OPENAI:
            # Fallback to sync client if async not available
            logger.warning("Async OpenAI client not available, using synchronous client")
            return self.call_structured_analysis(messages, json_schema, transaction_ctx)
            
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    # Calculate exponential backoff delay
                    delay = self.retry_base_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying async API call (attempt {attempt+1}/{self.max_retries+1}) after {delay:.2f}s delay")
                    await asyncio.sleep(delay)
                
                # Call the OpenAI API with the async client
                if HAS_NEW_OPENAI and self.async_client:
                    # Convert messages to the required format
                    api_messages = []
                    for msg in messages:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        api_messages.append({"role": role, "content": content})
                    
                    # Create response format object
                    response_format = {"type": "json_object"}
                    if "schema" in json_schema:
                        response_format["schema"] = json_schema["schema"]
                    
                    response = await self.async_client.chat.completions.create(
                        model=self.model_name,
                        messages=api_messages,
                        response_format=response_format,
                        temperature=0.2,
                    )
                    
                    # Extract content from the response
                    content = response.choices[0].message.content
                    if content is None:
                        logger.error("Received empty response from OpenAI API")
                        continue
                        
                    # Parse JSON from the response
                    try:
                        result = json.loads(content)
                        return result
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON from response: {content[:100]}...")
                        result = self._safe_json_load(content)
                        if result:
                            return result
                        continue
                else:
                    # Fallback to sync client
                    return self.call_structured_analysis(messages, json_schema, transaction_ctx)
                    
            except Exception as e:
                error_type = type(e).__name__
                # Handle common error types
                if "RateLimitError" in error_type:
                    logger.warning(f"OpenAI rate limit hit in async call: {e}")
                    if attempt == self.max_retries:
                        raise RateLimitError(f"Rate limit exceeded after {self.max_retries} retries: {str(e)}") from e
                elif "APIError" in error_type:
                    logger.error(f"OpenAI API error in async call: {e}")
                    if attempt == self.max_retries:
                        raise APIError(f"API error after {self.max_retries} retries: {str(e)}") from e
                else:
                    logger.error(f"Unexpected error in async API call: {e}")
                    if attempt == self.max_retries:
                        raise AIAnalysisError(f"Failed to complete async API call after {self.max_retries} retries: {str(e)}") from e
        
        # If we get here, all retries failed
        logger.error(f"All {self.max_retries+1} attempts to call OpenAI API asynchronously failed")
        return None


def check_openai_api(api_key: Optional[str] = None, model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    """
    Check if the OpenAI API is available and functioning.
    
    Args:
        api_key: Optional API key (uses OPENAI_API_KEY env var if not provided)
        model: Model to test with
        
    Returns:
        Dict with status information
        
    Raises:
        Exception: If API check fails
    """
    try:
        # Get API key from environment if not provided
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {
                "status": "unavailable",
                "error": "API key not provided and OPENAI_API_KEY not set in environment"
            }
            
        # Import here to avoid dependencies
        import openai
        from openai import OpenAI
        
        # Configure client
        client = OpenAI(api_key=api_key)
        
        # Try a simple test request with a timeout
        # Use a lightweight model call with minimal tokens
        from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
        
        system_msg: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": "You are a helpful assistant."
        }
        user_msg: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": "Hello, are you working? Respond with one word only: 'yes' or 'no'."
        }
        
        # Set a timeout
        import asyncio
        import threading
        result = {"status": "unknown", "response": None, "error": None}
        
        def run_request():
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[system_msg, user_msg],
                    temperature=0,
                    max_tokens=1
                )
                result["status"] = "connected"
                result["response"] = response
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
        
        # Run with timeout
        thread = threading.Thread(target=run_request)
        thread.start()
        thread.join(timeout=10)  # 10 second timeout
        
        if thread.is_alive():
            # Request is taking too long, consider it timed out
            return {
                "status": "timeout",
                "error": "API request timed out after 10 seconds"
            }
        
        if result["status"] == "error":
            return {
                "status": "error", 
                "error": result["error"]
            }
            
        # Return success
        return {
            "status": "connected",
            "model": model,
            "token_response": "Response received successfully"
        }
    
    except ImportError as e:
        return {
            "status": "unavailable",
            "error": f"OpenAI SDK not installed: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error checking OpenAI API: {str(e)}"
        } 