"""
Core API client for LegiScan interactions.

This module provides the LegiScanConfig class and low-level API request handling.
"""

import os
import time
import json
import logging
import requests
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple

from app.legiscan.exceptions import ApiError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class LegiScanConfig:
    """Configuration settings for LegiScan API."""
    api_key: str
    base_url: str = "https://api.legiscan.com/"
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    timeout: int = 30


class ApiClient:
    """
    Low-level client for interacting with the LegiScan API.
    Handles authentication, rate limiting, and error handling.
    """

    def __init__(self, config: LegiScanConfig):
        """
        Initialize the API client.
        
        Args:
            config: LegiScanConfig object with API settings
        """
        self.config = config
        self.last_request = datetime.now(timezone.utc)

    def _throttle_request(self) -> None:
        """
        Implements rate limiting to avoid overwhelming the LegiScan API.
        Ensures requests are spaced by at least rate_limit_delay seconds.
        """
        elapsed = (datetime.now(timezone.utc) - self.last_request).total_seconds()
        if elapsed < self.config.rate_limit_delay:
            time.sleep(self.config.rate_limit_delay - elapsed)

    def make_request(self, operation: str, params: Optional[Dict[str, Any]] = None, retries: Optional[int] = None) -> Dict[str, Any]:
        """
        Makes a request to the LegiScan API with rate limiting and retry logic.

        Args:
            operation: LegiScan API operation to perform
            params: Optional parameters for the API call
            retries: Number of retry attempts on failure (defaults to config value)

        Returns:
            JSON response data

        Raises:
            ApiError: If the API request fails after retries or returns an error
            RateLimitError: If rate limiting is encountered
        """
        self._throttle_request()

        # Prepare request parameters
        request_params = self._prepare_request_params(operation, params)
        max_retries = self.config.max_retries if retries is None else retries

        # Execute request with retry logic
        for attempt in range(max_retries):
            try:
                # Execute the HTTP request
                response = self._execute_request(request_params)
                
                # Parse the JSON response
                data = self._parse_json_response(response)
                
                # Check for API-level errors
                self._check_api_status(data, attempt, max_retries)
                
                # If we get here, request was successful
                return data
                
            except RateLimitError:
                # Re-raise rate limit errors after max retries
                if attempt == max_retries - 1:
                    raise
                # Otherwise, continue to next retry iteration
                continue
                
            except requests.exceptions.RequestException as e:
                # Handle request exceptions (network errors, timeouts, etc.)
                if not self._handle_request_exception(e, attempt, max_retries):
                    raise ApiError(f"API request failed: {e}") from e

        # This should never be reached due to the raise in the loop
        raise ApiError("API request failed: Maximum retries exceeded")

    def _prepare_request_params(self, operation: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Prepare the parameters for the API request.
        
        Args:
            operation: The API operation to perform
            params: Optional parameters for the API call
            
        Returns:
            Dictionary of parameters for the request
        """
        request_params = params.copy() if params else {}
        request_params["key"] = self.config.api_key
        request_params["op"] = operation
        return request_params

    def _execute_request(self, params: Dict[str, Any]) -> requests.Response:
        """
        Execute the HTTP request to the LegiScan API.
        
        Args:
            params: Parameters for the API call
            
        Returns:
            HTTP response from the API
            
        Raises:
            requests.exceptions.RequestException: For HTTP request errors
        """
        response = requests.get(
            self.config.base_url, 
            params=params, 
            timeout=self.config.timeout
        )
        self.last_request = datetime.now(timezone.utc)
        response.raise_for_status()
        return response

    def _parse_json_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Parse the JSON response from the API.
        
        Args:
            response: HTTP response from the API
            
        Returns:
            Parsed JSON data
            
        Raises:
            ApiError: If the response contains invalid JSON
        """
        try:
            return response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from LegiScan API: {response.text[:100]}...")
            raise ApiError("Invalid JSON response from LegiScan API") from e

    def _check_api_status(self, data: Dict[str, Any], attempt: int, max_retries: int) -> None:
        """
        Check the API response status and handle errors.
        
        Args:
            data: Parsed JSON data from the API
            attempt: Current retry attempt
            max_retries: Maximum number of retry attempts
            
        Raises:
            ApiError: If the API returns an error
            RateLimitError: If rate limiting is encountered
        """
        if data.get("status") != "OK":
            err_msg = data.get("alert", {}).get("message", "Unknown error from LegiScan")
            logger.warning(f"LegiScan API returned error: {err_msg}")

            # Check if we should retry based on error message
            if "rate limit" in err_msg.lower():
                self._handle_rate_limit(attempt, max_retries)
                raise RateLimitError(f"LegiScan API rate limit encountered (attempt {attempt + 1}/{max_retries})")

            raise ApiError(f"LegiScan API error: {err_msg}")

    def _handle_rate_limit(self, attempt: int, max_retries: int) -> None:
        """
        Handle rate limiting with exponential backoff.
        
        Args:
            attempt: Current retry attempt
            max_retries: Maximum number of retry attempts
        """
        wait_time = 5 * (2 ** attempt)  # Exponential backoff
        logger.info(f"Rate limited. Waiting {wait_time}s before retry {attempt+1}/{max_retries}")
        time.sleep(wait_time)

    def _handle_request_exception(self, exception: requests.exceptions.RequestException, attempt: int, max_retries: int) -> bool:
        """
        Handle request exceptions with retry logic.
        
        Args:
            exception: The request exception
            attempt: Current retry attempt
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if retry should continue, False if retries are exhausted
        """
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            logger.warning(f"API request failed (attempt {attempt+1}/{max_retries}): {exception}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            return True
        else:
            logger.error(f"API request failed after {max_retries} attempts: {exception}")
            return False

    def check_status(self) -> Dict[str, Any]:
        """
        Check the status of the LegiScan API connection.
        
        Returns:
            Dict with status information
            
        Raises:
            ApiError: If unable to connect to LegiScan API
        """
        try:
            # Perform a simple test request
            url = f"{self.config.base_url}/?key={self.config.api_key}&op=getSessionList&state=US"
            
            # Use requests with a timeout
            response = requests.get(url, timeout=self.config.timeout)
            
            # Check for API errors
            if response.status_code != 200:
                raise ApiError(f"LegiScan API returned status code {response.status_code}")
                
            # Parse the response
            data = response.json()
            
            # Check for API error in the response
            if data.get("status") == "ERROR":
                error_msg = data.get("alert", {}).get("message", "Unknown API error")
                raise ApiError(f"LegiScan API error: {error_msg}")
            
            # Return status information
            return {
                "status": "connected",
                "api_url": self.config.base_url,
                "rate_limit_delay": self.config.rate_limit_delay,
                "last_request": self.last_request.isoformat(),
            }
        except requests.exceptions.RequestException as e:
            raise ApiError(f"Error connecting to LegiScan API: {str(e)}")
        except Exception as e:
            raise ApiError(f"Unexpected error checking LegiScan API status: {str(e)}")


def create_api_client(api_key: Optional[str] = None) -> ApiClient:
    """
    Create an API client with the provided or environment key.
    
    Args:
        api_key: Optional API key (uses LEGISCAN_API_KEY env var if not provided)
        
    Returns:
        Configured ApiClient instance
        
    Raises:
        ValueError: If no API key is available
    """
    api_key = api_key or os.environ.get("LEGISCAN_API_KEY")
    if not api_key:
        raise ValueError("LEGISCAN_API_KEY not set. Please set the LEGISCAN_API_KEY environment variable.")
        
    config = LegiScanConfig(api_key=api_key)
    return ApiClient(config) 