"""
Custom exceptions for AI analysis error handling.
"""


class AIAnalysisError(Exception):
    """Base exception class for AI analysis errors."""


class TokenLimitError(AIAnalysisError):
    """Raised when content exceeds token limits."""


class APIError(AIAnalysisError):
    """Raised when OpenAI API returns an error."""


class RateLimitError(APIError):
    """Raised when OpenAI rate limits are hit."""


class ContentProcessingError(AIAnalysisError):
    """Raised when content processing (splitting, merging) fails."""


class DatabaseError(AIAnalysisError):
    """Raised when database operations fail."""
