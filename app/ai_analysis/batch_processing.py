"""
Batch processing functionality for the OpenAI client.

This module extends the structured analysis client with batch processing capabilities,
allowing for efficient concurrent processing of multiple requests.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from contextlib import suppress

# Import OpenAI types
try:
    # Not used directly but kept for type checking in docstrings
    # pylint: disable=unused-import
    from openai.types.chat import ChatCompletionMessageParam
except ImportError:
    pass  # Will be handled by core client import error

from .structured_analysis import StructuredAnalysisClient

logger = logging.getLogger(__name__)


class BatchProcessingClient(StructuredAnalysisClient):
    """Client extension providing batch processing capabilities."""

    async def batch_structured_analysis_async(
            self,
            batch_messages: List[List[Dict[str, Any]]],  # Using Dict instead of ChatCompletionMessageParam for type safety
            json_schema: Dict[str, Any],
            temperature: float = 0.2,
            reasoning_effort: Optional[str] = None,
            max_completion_tokens: Optional[int] = None,
            store: bool = True,
            max_concurrent: int = 5,
            use_transaction: bool = True) -> List[Dict[str, Any]]:
        """
        Process multiple structured analysis requests concurrently.
        If use_transaction is True and a database session is available, all operations
        are wrapped in a single transaction.

        Args:
            batch_messages: List of message lists for each API call
            json_schema: JSON schema for structured output
            temperature: Controls randomness (0-1)
            reasoning_effort: For o-series models, control reasoning depth
            max_completion_tokens: Cap on total tokens
            store: Whether to store completions
            max_concurrent: Maximum number of concurrent requests
            use_transaction: Whether to use a database transaction for all operations

        Returns:
            List of structured analysis dictionaries in the same order as input messages

        Raises:
            ValueError: If async client is not available
        """
        # Check if async client is available - this is done in call_structured_analysis_async
        # so no need to duplicate here
        
        # Import SQLAlchemy related constants from the parent class
        # pylint: disable=invalid-name
        HAS_SQLALCHEMY = getattr(self, 'HAS_SQLALCHEMY', False)

        if not use_transaction or not HAS_SQLALCHEMY or not self.db_session:
            return await self._execute_batch_requests(
                batch_messages,
                json_schema,
                temperature,
                reasoning_effort,
                max_completion_tokens,
                store,
                max_concurrent,
                None,
            )
        with self.transaction() as transaction:
            return await self._execute_batch_requests(
                batch_messages,
                json_schema,
                temperature,
                reasoning_effort,
                max_completion_tokens,
                store,
                max_concurrent,
                transaction,
            )

    async def _execute_batch_requests(
            self, batch_messages: List[List[Dict[str, Any]]],
            json_schema: Dict[str, Any], temperature: float,
            reasoning_effort: Optional[str],
            max_completion_tokens: Optional[int], store: bool,
            max_concurrent: int,
            transaction: Optional[Any]) -> List[Dict[str, Any]]:
        """
        Execute a batch of requests with concurrency control.

        Args:
            batch_messages: List of message lists for each API call
            json_schema: JSON schema for structured output
            temperature: Controls randomness (0-1)
            reasoning_effort: For o-series models, control reasoning depth
            max_completion_tokens: Cap on total tokens
            store: Whether to store completions
            max_concurrent: Maximum number of concurrent requests
            transaction: Optional transaction context

        Returns:
            List of results in the same order as input messages
        """
        # Create a semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(messages):
            async with semaphore:
                return await self.call_structured_analysis_async(
                    messages=messages,
                    json_schema=json_schema,
                    temperature=temperature,
                    reasoning_effort=reasoning_effort,
                    max_completion_tokens=max_completion_tokens,
                    store=store,
                    transaction_ctx=transaction)

        # Create tasks for all message sets
        tasks = [
            process_with_semaphore(messages) for messages in batch_messages
        ]

        # Execute all tasks concurrently and gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results, converting exceptions to empty dictionaries with error info
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Error in batch request %d: %s", i, str(result))
                processed_results.append({
                    "error": str(result),
                    "error_type": type(result).__name__
                })
            else:
                processed_results.append(result)

        return processed_results 