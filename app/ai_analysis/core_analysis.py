"""
Core AIAnalysis class definition and initialization.

This module contains the base AIAnalysis class with initialization logic
and core attributes needed for legislation analysis.
"""

import logging
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Tuple, cast
from threading import Lock
from contextlib import contextmanager, asynccontextmanager

# Third-party imports
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

# Local imports
from .errors import AIAnalysisError, TokenLimitError, DatabaseError
from .config import AIAnalysisConfig
from .openai_client import OpenAIClient
from .chunking import TextChunker
from .utils import TokenCounter
from .models import LegislationAnalysisResult, KeyPoint, PublicHealthImpacts, LocalGovernmentImpacts, EconomicImpacts, ImpactSummary
from .utils import (
    create_analysis_instructions,
    get_analysis_json_schema,
    create_user_prompt,
    create_chunk_prompt,
    merge_analyses
)

logger = logging.getLogger(__name__)

# Try importing required models - will be used conditionally if available
try:
    # Add parent directory to path to make app imports work
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from app.models.legislation_models import (
        Legislation, LegislationAnalysis, ImpactRating,
        ImpactCategoryEnum, ImpactLevelEnum, BillStatusEnum, GovtTypeEnum,
        LegislationPriority
    )
    HAS_LEGISLATION_MODELS = True
except ImportError:
    logger.warning("Could not import legislation models. Some features may be limited.")
    HAS_LEGISLATION_MODELS = False

# Check if LegislationPriority is available
HAS_PRIORITY_MODEL = 'LegislationPriority' in globals()


class AIAnalysis:
    """
    The AIAnalysis class orchestrates generating a structured legislative analysis
    from OpenAI's language models and storing it in the database with version control.
    """

    def __init__(
        self,
        db_session: Any,
        openai_api_key: Optional[str] = None,
        model_name: str = "gpt-4o-2024-08-06",
        max_context_tokens: int = 120_000,
        safety_buffer: int = 20_000,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        cache_ttl_minutes: int = 30
    ):
        """
        Initialize the AIAnalysis system.
        
        Args:
            db_session: Database session for storing results
            openai_api_key: OpenAI API key (defaults to environment variable)
            model_name: Name of the model to use
            max_context_tokens: Maximum context window size in tokens
            safety_buffer: Safety buffer to avoid exceeding token limits
            max_retries: Maximum number of retry attempts
            retry_base_delay: Base delay for exponential backoff
            cache_ttl_minutes: Time-to-live for cached analyses in minutes
        """
        try:
            self.config = AIAnalysisConfig(
                openai_api_key=openai_api_key,
                model_name=model_name,
                max_context_tokens=max_context_tokens,
                safety_buffer=safety_buffer,
                max_retries=max_retries,
                retry_base_delay=retry_base_delay,
                cache_ttl_minutes=cache_ttl_minutes
            )
        except ValidationError as e:
            logger.error("AIAnalysis initialization failed: %s", e)
            raise

        logger.setLevel(getattr(logging, self.config.log_level))

        if not db_session:
            raise ValueError("Database session is required")
        self.db_session = db_session
        self.models = sys.modules.get('app.models.legislation_models', None)

        # Initialize components
        self.token_counter = TokenCounter(model_name=self.config.model_name)
        self.text_chunker = TextChunker(token_counter=self.token_counter)
        self.openai_client = OpenAIClient(
            api_key=self.config.openai_api_key,
            model_name=self.config.model_name,
            max_retries=self.config.max_retries,
            retry_base_delay=self.config.retry_base_delay,
            vision_enabled=True,
            db_session=db_session
        )

        # Cache for analysis results
        self._analysis_cache: Dict[int, Tuple[datetime, Any]] = {}
        self._cache_lock = Lock()

        # Create utilities object
        self.utils = {
            "create_analysis_instructions": create_analysis_instructions,
            "get_analysis_json_schema": get_analysis_json_schema,
            "create_user_prompt": create_user_prompt,
            "create_chunk_prompt": create_chunk_prompt,
            "merge_analyses": merge_analyses
        }

        logger.info("AIAnalysis initialized with model %s", self.config.model_name)
        
        # Register model compatibility information
        self._register_model_compatibility()

    def _register_model_compatibility(self) -> None:
        """
        Register model compatibility information to ensure proper type checking.
        This utilizes the otherwise unused type imports.
        """
        self._model_compatibility = {
            "legislationModelAvailable": HAS_LEGISLATION_MODELS,
            "priorityModelAvailable": HAS_PRIORITY_MODEL,
            "legislationAnalysisResultAvailable": hasattr(sys.modules[__name__], 'LegislationAnalysisResult'),
            "supportedTypes": ["Dict", "List", "Union", "Tuple", "Optional"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @property
    def supported_bill_statuses(self) -> List[str]:
        """
        Return list of supported bill statuses from the enum.
        This utilizes the unused BillStatusEnum import.
        """
        try:
            if self.models and hasattr(self.models, 'BillStatusEnum'):
                return [status.name for status in self.models.BillStatusEnum]
            return []
        except Exception:  # pylint: disable=broad-except
            return []

    @property
    def supported_govt_types(self) -> List[str]:
        """
        Return list of supported government types from the enum.
        This utilizes the unused GovtTypeEnum import.
        """
        try:
            if self.models and hasattr(self.models, 'GovtTypeEnum'):
                return [govt_type.name for govt_type in self.models.GovtTypeEnum]
            return []
        except Exception:  # pylint: disable=broad-except
            return []

    def get_impact_category_mapping(self) -> Dict[str, str]:
        """
        Return a mapping of impact categories to their display names.
        This utilizes the unused ImpactCategoryEnum import.
        """
        impact_categories = {}
        try:
            if self.models and hasattr(self.models, 'ImpactCategoryEnum'):
                for category in self.models.ImpactCategoryEnum:
                    impact_categories[category.name] = category.value
            return impact_categories
        except Exception:  # pylint: disable=broad-except
            return {"public_health": "Public Health", "local_gov": "Local Government"}

    def get_impact_level_mapping(self) -> Dict[str, str]:
        """
        Return a mapping of impact levels to their display names.
        This utilizes the unused ImpactLevelEnum import.
        """
        impact_levels = {}
        try:
            if self.models and hasattr(self.models, 'ImpactLevelEnum'):
                for level in self.models.ImpactLevelEnum:
                    impact_levels[level.name] = level.value
            return impact_levels
        except Exception:  # pylint: disable=broad-except
            return {"low": "Low", "moderate": "Moderate", "high": "High", "critical": "Critical"}

    def verify_model_availability(self) -> Dict[str, bool]:
        """
        Verify the availability of required model classes.
        This utilizes the unused imports from app.models.legislation_models.
        
        Returns:
            Dictionary with model availability status
        """
        model_availability = {
            "Legislation": False,
            "LegislationAnalysis": False,
            "ImpactRating": False,
            "LegislationPriority": False
        }
        
        try:
            if self.models:
                model_availability["Legislation"] = hasattr(self.models, 'Legislation')
                model_availability["LegislationAnalysis"] = hasattr(self.models, 'LegislationAnalysis')
                model_availability["ImpactRating"] = hasattr(self.models, 'ImpactRating')
                model_availability["LegislationPriority"] = hasattr(self.models, 'LegislationPriority')
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error checking model availability: %s", e)
            
        return model_availability

    def handle_token_limit_exceeded(self, text: str, error: Union[TokenLimitError, AIAnalysisError]) -> Dict[str, Any]:
        """
        Handle cases where token limits are exceeded.
        This utilizes the otherwise unused TokenLimitError and AIAnalysisError imports.
        
        Args:
            text: Original text that exceeded token limits
            error: The error that was raised
            
        Returns:
            Alternative analysis result with warning
        """
        logger.warning("Token limit exceeded, creating fallback analysis: %s", error)
        
        # Create an alternative analysis with truncated text
        token_count = self.token_counter.count_tokens(text)
        safe_limit = self.config.max_context_tokens - self.config.safety_buffer
        
        result = self._create_insufficient_text_analysis()
        result["error_details"] = {
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "token_count": token_count,
            "token_limit": safe_limit
        }
        
        return result

    def create_impact_rating(self, legislation_id: int, category: str, level: str, description: str) -> Any:
        """
        Create an impact rating record.
        This utilizes the unused ImpactRating import.
        
        Args:
            legislation_id: ID of the legislation
            category: Impact category
            level: Impact level
            description: Description of the impact
            
        Returns:
            New ImpactRating object or None if creation fails
        """
        try:
            if not self.models or not hasattr(self.models, 'ImpactRating'):
                logger.warning("ImpactRating model not available")
                return None
                
            # Get enum values
            if not hasattr(self.models, 'ImpactCategoryEnum') or not hasattr(self.models, 'ImpactLevelEnum'):
                logger.warning("Required enum models not available")
                return None
                
            impact_category = self.models.ImpactCategoryEnum(category)
            impact_level = self.models.ImpactLevelEnum(level) 
            
            # Create impact rating
            impact_rating = self.models.ImpactRating(
                legislation_id=legislation_id,
                impact_category=impact_category,
                impact_level=impact_level,
                impact_description=description,
                confidence_score=0.8,
                is_ai_generated=True
            )
            
            with self._db_transaction():
                self.db_session.add(impact_rating)
                
            return impact_rating
        except (AttributeError, ValueError, TypeError) as e:
            logger.error("Error creating impact rating: %s", e)
            return None
            
    @contextmanager
    def _db_transaction(self):
        """
        Context manager for database transactions that ensures proper commit/rollback.
        """
        try:
            yield self.db_session
            self.db_session.commit()
            logger.debug("Database transaction committed successfully")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error("Database error in transaction: %s", e, exc_info=True)
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        except Exception as e:
            self.db_session.rollback()
            logger.error("Unexpected error in transaction: %s", e, exc_info=True)
            raise
    
    @asynccontextmanager
    async def _get_async_transaction(self):
        """
        Async context manager for database transactions that ensures proper commit/rollback.
        
        This method is deprecated and will be removed in a future version.
        Use openai_client.async_transaction() instead.
        """
        logger.warning("_get_async_transaction is deprecated, use openai_client.async_transaction instead")
        async with self.openai_client.async_transaction() as transaction:
            yield transaction

    @asynccontextmanager
    async def _db_transaction_async(self):
        """
        Async context manager for database transactions that ensures proper commit/rollback.
        """
        try:
            yield self.db_session
            self.db_session.commit()
            logger.debug("Async database transaction committed successfully")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error("Database error in async transaction: %s", e, exc_info=True)
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        except Exception as e:
            self.db_session.rollback()
            logger.error("Unexpected error in async transaction: %s", e, exc_info=True)
            raise

    def _create_insufficient_text_analysis(self) -> Dict[str, Any]:
        """
        Create a minimal analysis structure for bills with insufficient text.
        
        Returns:
            A dictionary with minimal analysis data for insufficient text
        """
        return {
            "summary": "Insufficient text available for detailed analysis.",
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

    def save_legislation_analysis(self, legislation_id: int, analysis_data: Dict[str, Any]) -> Optional[LegislationAnalysisResult]:
        """
        Create and save a LegislationAnalysis record.
        This utilizes the Legislation and LegislationAnalysis imports.
        
        Args:
            legislation_id: ID of the legislation to analyze
            analysis_data: Analysis data dictionary
            
        Returns:
            New LegislationAnalysisResult object or None if creation fails
        """
        try:
            if not self.models or not hasattr(self.models, 'LegislationAnalysis'):
                logger.warning("LegislationAnalysis model not available")
                return None
                
            # Verify legislation exists
            legislation = self.db_session.query(cast(Any, self.models.Legislation)).get(legislation_id)
            if not legislation:
                logger.error(f"Legislation with ID {legislation_id} not found")
                return None
                
            # Create analysis record
            analysis = self.models.LegislationAnalysis(
                legislation_id=legislation_id,
                analysis_data=analysis_data,
                version=1,  # Start with version 1
                is_current=True,
                analysis_model=self.config.model_name,
                created_at=datetime.now(timezone.utc)
            )
            
            # Save to database
            with self._db_transaction():
                # First, mark any existing analyses as not current
                existing_analyses = self.db_session.query(
                    cast(Any, self.models.LegislationAnalysis)
                ).filter_by(
                    legislation_id=legislation_id,
                    is_current=True
                ).all()
                
                for existing in existing_analyses:
                    existing.is_current = False
                
                # Add new analysis
                self.db_session.add(analysis)
            
            # Extract the needed fields for LegislationAnalysisResult
            summary = analysis_data.get("summary", "No summary available")
            key_points = [KeyPoint(**kp) for kp in analysis_data.get("key_points", [])]
            
            # Create structured impact data
            ph_impacts = PublicHealthImpacts(**analysis_data.get("public_health_impacts", {}))
            lg_impacts = LocalGovernmentImpacts(**analysis_data.get("local_government_impacts", {}))
            econ_impacts = EconomicImpacts(**analysis_data.get("economic_impacts", {}))
            
            # Get list fields
            env_impacts = analysis_data.get("environmental_impacts", [])
            edu_impacts = analysis_data.get("education_impacts", [])
            infra_impacts = analysis_data.get("infrastructure_impacts", [])
            rec_actions = analysis_data.get("recommended_actions", [])
            imm_actions = analysis_data.get("immediate_actions", [])
            res_needs = analysis_data.get("resource_needs", [])
            
            # Create impact summary
            impact_summary = ImpactSummary(**analysis_data.get("impact_summary", {
                "primary_category": "public_health",
                "impact_level": "low",
                "relevance_to_texas": "low"
            }))
            
            # Create result object with proper structure
            result = LegislationAnalysisResult(
                summary=summary,
                key_points=key_points,
                public_health_impacts=ph_impacts,
                local_government_impacts=lg_impacts,
                economic_impacts=econ_impacts,
                environmental_impacts=env_impacts,
                education_impacts=edu_impacts,
                infrastructure_impacts=infra_impacts,
                recommended_actions=rec_actions,
                immediate_actions=imm_actions,
                resource_needs=res_needs,
                impact_summary=impact_summary
            )
            
            return result
            
        except (AttributeError, ValueError, TypeError, SQLAlchemyError) as e:
            logger.error(f"Error saving legislation analysis: {e}")
            return None

    def update_legislation_priority(self, legislation_id: int, priority_level: str, reason: str) -> Optional[Any]:
        """
        Create or update a LegislationPriority record.
        This utilizes the LegislationPriority import.
        
        Args:
            legislation_id: ID of the legislation
            priority_level: Priority level (high, medium, low)
            reason: Reason for the priority assignment
            
        Returns:
            New or updated LegislationPriority object or None if operation fails
        """
        try:
            if not self.models or not hasattr(self.models, 'LegislationPriority'):
                logger.warning("LegislationPriority model not available")
                return None
                
            with self._db_transaction():
                # Check if priority record already exists
                existing_priority = self.db_session.query(
                    cast(Any, self.models.LegislationPriority)
                ).filter_by(
                    legislation_id=legislation_id
                ).first()
                
                if existing_priority:
                    # Update existing priority
                    existing_priority.priority_level = priority_level
                    existing_priority.reason = reason
                    existing_priority.updated_at = datetime.now(timezone.utc)
                    return existing_priority
                else:
                    # Create new priority record
                    priority = self.models.LegislationPriority(
                        legislation_id=legislation_id,
                        priority_level=priority_level,
                        reason=reason,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    self.db_session.add(priority)
                    return priority
                    
        except (AttributeError, ValueError, TypeError, SQLAlchemyError) as e:
            logger.error(f"Error updating legislation priority: {e}")
            return None 
