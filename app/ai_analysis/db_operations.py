"""
Database operations for AI analysis.

This module provides functions for interacting with the database,
including storing and retrieving analysis results.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast

logger = logging.getLogger(__name__)

def get_cached_analysis(analyzer: Any, legislation_id: int) -> Optional[Any]:
    """
    Check if analysis is available in cache and not expired.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation to check
        
    Returns:
        Cached analysis if available and not expired, None otherwise
    """
    # pylint: disable=protected-access
    with analyzer._cache_lock:
        if legislation_id in analyzer._analysis_cache:
            cache_time, cached_analysis = analyzer._analysis_cache[legislation_id]
            cache_age_minutes = (datetime.now(timezone.utc) - cache_time).total_seconds() / 60
            if cache_age_minutes < analyzer.config.cache_ttl_minutes:
                logger.info("Using cached analysis for legislation ID=%d", legislation_id)
                return cached_analysis
            else:
                del analyzer._analysis_cache[legislation_id]
    return None

def update_analysis_cache(analyzer: Any, legislation_id: int, analysis: Any) -> None:
    """
    Update the analysis cache with a new analysis result.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation
        analysis: Analysis result to cache
    """
    # pylint: disable=protected-access
    with analyzer._cache_lock:
        analyzer._analysis_cache[legislation_id] = (datetime.now(timezone.utc), analysis)
    logger.debug("Updated cache for legislation ID=%d", legislation_id)

def get_legislation_object(analyzer: Any, legislation_id: int) -> Optional[Any]:
    """
    Retrieve legislation object from database.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation to retrieve
        
    Returns:
        Legislation object if found, None otherwise
    """
    # Check if we have access to the legislation model
    try:
        if hasattr(analyzer, 'models') and analyzer.models:
            leg_obj = analyzer.db_session.query(analyzer.models.Legislation).filter_by(id=legislation_id).first()
        else:
            # Try to import locally
            # pylint: disable=import-outside-toplevel
            from app.models.legislation_models import Legislation
            leg_obj = analyzer.db_session.query(Legislation).filter_by(id=legislation_id).first()
    except (ImportError, AttributeError):
        # If model not available, log and return None
        logger.error("Could not access Legislation model for ID=%d", legislation_id)
        return None
        
    if leg_obj is None:
        logger.error("Legislation with ID=%d not found in the database", legislation_id)
        
    return leg_obj

def store_legislation_analysis(analyzer: Any, legislation_id: int, analysis_dict: Dict[str, Any]) -> Any:
    """
    Store the analysis results in the database.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation
        analysis_dict: Analysis data dictionary
        
    Returns:
        LegislationAnalysis object
    """
    if not analysis_dict:
        # pylint: disable=import-outside-toplevel
        from pydantic import ValidationError
        raise ValidationError("Cannot store empty analysis data")

    # pylint: disable=protected-access
    with analyzer._db_transaction():
        # Get previous analyses for this legislation to find the latest version
        try:
            legislation_analysis_obj = _get_legislation_analysis_model(analyzer)
            existing_analyses = (
                analyzer.db_session.query(legislation_analysis_obj)
                .filter_by(legislation_id=legislation_id)
                .all()
            )
        except (ImportError, AttributeError) as exc:
            logger.error("Could not access LegislationAnalysis model")
            raise ValueError("LegislationAnalysis model not available") from exc

        # Determine version number and previous analysis ID
        if existing_analyses:
            versions = [
                cast(int, x.analysis_version) if hasattr(x, 'analysis_version') and x.analysis_version is not None else 0
                for x in existing_analyses
            ]
            max_version = max(versions, default=0)
            new_version = max_version + 1
            prev = next(
                (
                    x for x in existing_analyses
                    if hasattr(x, 'analysis_version') and cast(int, x.analysis_version) == max_version
                ),
                None
            )
            prev_id = prev.id if prev is not None else None
        else:
            new_version = 1
            prev_id = None

        # Process impact data
        impact_summary = analysis_dict.get("impact_summary", {})
        impact_category_str = impact_summary.get("primary_category")
        impact_level_str = impact_summary.get("impact_level")

        impact_category_enum = None
        impact_level_enum = None

        # Try to convert strings to enum values
        try:
            impact_enums = _get_impact_enum_models(analyzer)
            impact_category_enum_cls, impact_level_enum_cls = impact_enums
                
            if impact_category_str is not None:
                try:
                    impact_category_enum = impact_category_enum_cls(impact_category_str)
                except (ValueError, TypeError) as e:
                    logger.warning("Invalid impact_category value: %s: %s", impact_category_str, e)

            if impact_level_str is not None:
                try:
                    impact_level_enum = impact_level_enum_cls(impact_level_str)
                except (ValueError, TypeError) as e:
                    logger.warning("Invalid impact_level value: %s: %s", impact_level_str, e)
                    
        except (ImportError, AttributeError):
            logger.warning("Could not access enum models for impact categorization")

        # Create the analysis object
        try:
            analysis_obj = _create_legislation_analysis_object(
                analyzer, 
                legislation_id,
                new_version,
                prev_id,
                analysis_dict,
                impact_category_enum,
                impact_level_enum
            )
        except (ImportError, AttributeError) as e:
            logger.error("Could not create LegislationAnalysis: %s", e)
            raise ValueError(f"Could not create LegislationAnalysis: {e}") from e

        # Add optional metadata if supported
        if hasattr(analysis_obj, "processing_metadata"):
            analysis_obj.processing_metadata = {
                "date_processed": datetime.now(timezone.utc).isoformat(),
                "model_name": analyzer.config.model_name,
                "software_version": "2.0.0"
            }

        # Add to session and flush to get ID
        analyzer.db_session.add(analysis_obj)
        analyzer.db_session.flush()
            
        # Create impact ratings if applicable
        create_impact_ratings(analyzer, legislation_id, analysis_dict)
            
        logger.info("Created new LegislationAnalysis for legislation_id=%d, version=%d", 
                   legislation_id, new_version)

        return analysis_obj

def _get_legislation_analysis_model(analyzer: Any) -> Any:
    """
    Get the LegislationAnalysis model class.
    
    Args:
        analyzer: AIAnalysis instance
        
    Returns:
        LegislationAnalysis model class
    """
    # pylint: disable=import-outside-toplevel,invalid-name
    if hasattr(analyzer, 'models') and analyzer.models:
        LegislationAnalysis = analyzer.models.LegislationAnalysis
    else:
        # Try to import locally
        from app.models.legislation_models import LegislationAnalysis
    return LegislationAnalysis

def _get_impact_enum_models(analyzer: Any) -> tuple:
    """
    Get the impact enum model classes.
    
    Args:
        analyzer: AIAnalysis instance
        
    Returns:
        Tuple of (ImpactCategoryEnum, ImpactLevelEnum) model classes
    """
    # pylint: disable=import-outside-toplevel,invalid-name
    if hasattr(analyzer, 'models') and analyzer.models:
        ImpactCategoryEnum = analyzer.models.ImpactCategoryEnum
        ImpactLevelEnum = analyzer.models.ImpactLevelEnum
    else:
        # Try to import locally
        from app.models.legislation_models import ImpactCategoryEnum, ImpactLevelEnum
    return (ImpactCategoryEnum, ImpactLevelEnum)

def _create_legislation_analysis_object(analyzer: Any, legislation_id: int, new_version: int, 
                                       prev_id: Optional[int], analysis_dict: Dict[str, Any],
                                       impact_category_enum: Any, impact_level_enum: Any) -> Any:
    """
    Create a LegislationAnalysis object.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation
        new_version: New version number
        prev_id: Previous version ID
        analysis_dict: Analysis data dictionary
        impact_category_enum: Impact category enum value
        impact_level_enum: Impact level enum value
        
    Returns:
        LegislationAnalysis object
    """
    # pylint: disable=import-outside-toplevel,invalid-name
    if hasattr(analyzer, 'models') and analyzer.models:
        LegislationAnalysis = analyzer.models.LegislationAnalysis
    else:
        # Try to import locally
        from app.models.legislation_models import LegislationAnalysis
    
    return LegislationAnalysis(
        legislation_id=legislation_id,
        analysis_version=new_version,
        previous_version_id=prev_id,
        analysis_date=datetime.now(timezone.utc),
        summary=analysis_dict.get("summary", ""),
        key_points=analysis_dict.get("key_points", []),
        insufficient_text=analysis_dict.get("insufficient_text", False),
        public_health_impacts=analysis_dict.get("public_health_impacts", {}),
        local_gov_impacts=analysis_dict.get("local_government_impacts", {}),
        economic_impacts=analysis_dict.get("economic_impacts", {}),
        environmental_impacts=analysis_dict.get("environmental_impacts", []),
        education_impacts=analysis_dict.get("education_impacts", []),
        infrastructure_impacts=analysis_dict.get("infrastructure_impacts", []),
        recommended_actions=analysis_dict.get("recommended_actions", []),
        immediate_actions=analysis_dict.get("immediate_actions", []),
        resource_needs=analysis_dict.get("resource_needs", []),
        raw_analysis=None,
        model_version=analyzer.config.model_name,
        impact_category=impact_category_enum,
        impact=impact_level_enum
    )

async def store_legislation_analysis_async(analyzer: Any, legislation_id: int, analysis_dict: Dict[str, Any]) -> Any:
    """
    Asynchronously store the analysis results in the database.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation
        analysis_dict: Analysis data dictionary
        
    Returns:
        LegislationAnalysis object
    """
    # Most database operations are synchronous even in async context,
    # so we use the synchronous version for now
    return store_legislation_analysis(analyzer, legislation_id, analysis_dict)

def create_impact_ratings(analyzer: Any, legislation_id: int, analysis_dict: Dict[str, Any]) -> None:
    """
    Create impact ratings from analysis data and save them to the database.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation
        analysis_dict: Analysis data dictionary
    """
    # Try to import the ImpactRating model
    try:
        # pylint: disable=import-outside-toplevel,invalid-name
        if hasattr(analyzer, 'models') and analyzer.models:
            ImpactRating = analyzer.models.ImpactRating
            ImpactCategoryEnum = analyzer.models.ImpactCategoryEnum
            ImpactLevelEnum = analyzer.models.ImpactLevelEnum
        else:
            # Try to import locally
            from app.models.legislation_models import ImpactRating, ImpactCategoryEnum, ImpactLevelEnum
    except (ImportError, AttributeError):
        logger.warning("Could not access ImpactRating model, skipping impact rating creation")
        return

    # Delete any existing impact ratings for this legislation
    try:
        existing_ratings = analyzer.db_session.query(ImpactRating).filter_by(
            legislation_id=legislation_id
        ).all()
        
        for rating in existing_ratings:
            analyzer.db_session.delete(rating)
    except (ImportError, AttributeError, ValueError, TypeError) as e:
        logger.error("Error deleting existing impact ratings: %s", e)
        return
        
    # Extract impact data from different categories
    impact_categories = {
        "public_health": analysis_dict.get("public_health_impacts", {}),
        "local_government": analysis_dict.get("local_government_impacts", {}),
        "economic": analysis_dict.get("economic_impacts", {}),
        "environmental": analysis_dict.get("environmental_impacts", []),
        "education": analysis_dict.get("education_impacts", []),
        "infrastructure": analysis_dict.get("infrastructure_impacts", {})
    }
    
    # Main impact from impact_summary
    impact_summary = analysis_dict.get("impact_summary", {})
    primary_impact_creation(analyzer, legislation_id, impact_summary, ImpactCategoryEnum, ImpactLevelEnum, ImpactRating)
    
    # Process each impact category
    for category_name, impact_data in impact_categories.items():
        # Skip empty categories
        if not impact_data:
            continue
        
        process_impact_category(analyzer, legislation_id, category_name, impact_data, 
                               ImpactCategoryEnum, ImpactLevelEnum, ImpactRating)

def primary_impact_creation(analyzer: Any, legislation_id: int, impact_summary: Dict[str, Any],
                           impact_category_enum_cls: Any, impact_level_enum_cls: Any, impact_rating_cls: Any) -> None:
    """
    Create the primary impact rating from the impact summary.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation
        impact_summary: Impact summary data
        impact_category_enum_cls: ImpactCategoryEnum class
        impact_level_enum_cls: ImpactLevelEnum class
        impact_rating_cls: ImpactRating class
    """
    if impact_category_str := impact_summary.get("primary_category"):
        if impact_level_str := impact_summary.get("impact_level"):
            try:
                category_enum = impact_category_enum_cls(impact_category_str)
                level_enum = impact_level_enum_cls(impact_level_str)
                
                # Create the primary impact rating
                primary_rating = impact_rating_cls(
                    legislation_id=legislation_id,
                    impact_category=category_enum,
                    impact_level=level_enum,
                    impact_description=impact_summary.get("description", ""),
                    affected_entities=impact_summary.get("affected_entities", []),
                    confidence_score=0.9,  # High confidence for primary impact
                    is_ai_generated=True
                )
                analyzer.db_session.add(primary_rating)
                logger.info("Created primary impact rating for legislation_id=%d", legislation_id)
            except (ValueError, TypeError) as e:
                logger.warning("Could not create primary impact rating: %s", e)

def process_impact_category(analyzer: Any, legislation_id: int, category_name: str, impact_data: Any,
                           impact_category_enum_cls: Any, impact_level_enum_cls: Any, impact_rating_cls: Any) -> None:
    """
    Process a single impact category and create the corresponding impact rating.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation
        category_name: Name of the impact category
        impact_data: Impact data
        impact_category_enum_cls: ImpactCategoryEnum class
        impact_level_enum_cls: ImpactLevelEnum class
        impact_rating_cls: ImpactRating class
    """
    # Extract impact level and description
    impact_level = None
    impact_description = ""
    affected_entities = []
    
    # Handle different formats of impact data
    if isinstance(impact_data, dict):
        impact_level = impact_data.get("impact_level")
        impact_description = impact_data.get("description", "")
        affected_entities = impact_data.get("affected_entities", [])
    elif isinstance(impact_data, list) and impact_data:
        # If it's a list, use the first item's description
        impact_description = "\n".join([str(item) for item in impact_data])
        # Default to moderate impact if not specified
        impact_level = "moderate"
    
    if impact_level:
        try:
            # Convert category name to enum
            category_enum = None
            for e in impact_category_enum_cls:
                if e.name.lower() == category_name.lower():
                    category_enum = e
                    break
            
            # Convert impact level to enum
            level_enum = None
            for e in impact_level_enum_cls:
                if e.name.lower() == impact_level.lower():
                    level_enum = e
                    break
            
            # Skip if we couldn't map the category or level
            if not category_enum or not level_enum:
                return
            
            # Create the impact rating
            rating = impact_rating_cls(
                legislation_id=legislation_id,
                impact_category=category_enum,
                impact_level=level_enum,
                impact_description=impact_description,
                affected_entities=affected_entities,
                confidence_score=0.8,  # Slightly lower confidence for secondary impacts
                is_ai_generated=True
            )
            analyzer.db_session.add(rating)
            logger.debug("Created impact rating for category %s for legislation_id=%d", 
                        category_name, legislation_id)
        except (ValueError, TypeError) as e:
            logger.warning("Could not create impact rating for category %s: %s", 
                          category_name, e) 