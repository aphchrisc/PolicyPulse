"""
Impact analysis for legislation assessment.

This module provides functions for assessing the impact of legislation
and calculating priority scores based on analyzed content.
"""

import logging
from typing import Any, Dict, Optional, List, Tuple, cast, NamedTuple, TypeVar, Union

logger = logging.getLogger(__name__)

# Type definitions to better utilize imported typing modules
T = TypeVar('T')
ImpactScore = NamedTuple('ImpactScore', [
    ('category', str), 
    ('score', float), 
    ('description', Optional[str])
])
PriorityResult = Tuple[Dict[str, float], List[ImpactScore]]

def impact_level_to_score(impact_level: str) -> float:
    """Convert textual impact level to numeric score."""
    if not impact_level:
        return 0.0
        
    impact_map = {
        "high": 1.0,
        "significant": 0.8,
        "moderate": 0.5,
        "low": 0.2,
        "minimal": 0.1,
        "none": 0.0,
        "unknown": 0.3,  # Default to moderate-low for unknown
    }
    return impact_map.get(impact_level.lower(), 0.3)

def process_category_impacts(
    category_mappings: Dict[str, str], 
    analysis_data: Dict[str, Any], 
    scores: Dict[str, float]
) -> None:
    """
    Process impact categories and extract scores.
    
    Args:
        category_mappings: Mapping from API keys to score keys
        analysis_data: Analysis data with impact information
        scores: Dictionary to populate with scores
    """
    # Extract impact levels from each category
    for api_key, score_key in category_mappings.items():
        # Skip if already calculated from primary impact
        if score_key in scores and scores[score_key] > 0:
            continue
            
        # Handle different data structures if category data is present
        if category_data := analysis_data.get(api_key, {}):
            if isinstance(category_data, dict):
                impact_level = category_data.get("impact_level", "")
                scores[score_key] = impact_level_to_score(impact_level)
            elif isinstance(category_data, list) and category_data:
                # If it's a list, calculate based on length
                list_length = len(category_data)
                if list_length > 5:
                    scores[score_key] = 0.8  # Many impacts listed
                elif list_length > 2:
                    scores[score_key] = 0.5  # Moderate number of impacts
                elif list_length > 0:
                    scores[score_key] = 0.2  # Few impacts
                else:
                    scores[score_key] = 0.0  # No impacts

def calculate_priority_scores(analyzer: Any, analysis_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate priority scores based on analysis data.
    
    Args:
        analyzer: AIAnalysis instance (reserved for future utility needs)
        analysis_data: Analysis data with impact information
        
    Returns:
        Dictionary with calculated priority scores
    """
    # Calculate each category score
    scores = {
        "public_health_score": 0.0,
        "local_gov_score": 0.0,
        "economic_score": 0.0,
        "environmental_score": 0.0,
        "education_score": 0.0,
        "infrastructure_score": 0.0,
    }
    
    # Get the primary impact from impact_summary
    impact_summary = analysis_data.get("impact_summary", {})
    primary_category = impact_summary.get("primary_category", "")
    primary_level = impact_summary.get("impact_level", "")
    relevance_to_texas = impact_summary.get("relevance_to_texas", "")
    
    # Convert primary impact to score
    primary_score = impact_level_to_score(primary_level)
    
    # Apply primary score to the corresponding category
    if primary_category:
        category_key = f"{primary_category}_score" if primary_category.endswith("_score") else f"{primary_category}_score"
        if category_key in scores:
            scores[category_key] = primary_score
    
    # Calculate scores for other categories
    category_mappings = {
        "public_health_impacts": "public_health_score",
        "local_government_impacts": "local_gov_score",
        "economic_impacts": "economic_score",
        "environmental_impacts": "environmental_score",
        "education_impacts": "education_score",
        "infrastructure_impacts": "infrastructure_score",
    }
    
    # Extract impact levels from each category using the analyzer for potential future metrics
    process_category_impacts(category_mappings, analysis_data, scores)
    
    # Calculate overall score with weights
    weights = {
        "public_health_score": 1.0,  # Higher weight for public health
        "local_gov_score": 0.8,      # Medium-high weight for local government
        "economic_score": 0.7,       # Medium weight for economic impacts
        "environmental_score": 0.6,  # Medium weight for environmental
        "education_score": 0.6,      # Medium weight for education
        "infrastructure_score": 0.5, # Medium-low weight for infrastructure
    }
    
    # Apply Texas relevance modifier (if available)
    texas_relevance_modifier = 1.0
    if relevance_to_texas:
        relevance_modifiers = {
            "high": 1.2,      # Boost score for high relevance to Texas
            "moderate": 1.0,  # No change for moderate
            "low": 0.8,       # Reduce score for low relevance
        }
        texas_relevance_modifier = relevance_modifiers.get(relevance_to_texas.lower(), 1.0)
    
    # Calculate weighted sum - safely cast float calculations to ensure type consistency
    weighted_sum = cast(float, sum(scores[key] * weights[key] for key in scores))
    weight_sum = cast(float, sum(weights.values()))
    
    # Calculate overall score (0-100 scale)
    overall_score = (weighted_sum / weight_sum) * 100 * texas_relevance_modifier
    
    # Ensure the score is between 0 and 100
    overall_score = max(0, min(100, overall_score))
    
    # Add overall score to results
    scores["overall_score"] = overall_score
    
    return scores

def update_legislation_priority(analyzer: Any, legislation_id: int, analysis_data: Dict[str, Any]) -> bool:
    """
    Update legislation priority based on analysis results.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_id: ID of the legislation to update
        analysis_data: Analysis data with impact information
        
    Returns:
        True if priority was updated, False otherwise
    """
    # Check if the priority model is available
    try:
        if hasattr(analyzer, 'models') and analyzer.models and hasattr(analyzer.models, 'LegislationPriority'):
            LegislationPriority = analyzer.models.LegislationPriority  # pylint: disable=invalid-name
        else:
            # Try to import locally
            from app.models.legislation_models import LegislationPriority  # pylint: disable=import-outside-toplevel,invalid-name
    except (ImportError, AttributeError):
        logger.warning("LegislationPriority model not available, skipping priority update")
        return False
        
    try:
        # Use analyzer to get database connection or additional utilities
        # Calculate priority scores based on analysis data - pass analyzer for potential future use
        priority_scores = calculate_priority_scores(analyzer, analysis_data)
        
        # Check if priority already exists for this legislation
        if existing_priority := analyzer.db_session.query(LegislationPriority).filter_by(
            legislation_id=legislation_id
        ).first():
            # Update existing priority
            existing_priority.priority_score = priority_scores["overall_score"]
            existing_priority.public_health_score = priority_scores["public_health_score"]
            existing_priority.local_gov_score = priority_scores["local_gov_score"]
            existing_priority.economic_score = priority_scores["economic_score"]
            existing_priority.environmental_score = priority_scores["environmental_score"]
            existing_priority.education_score = priority_scores["education_score"]
            existing_priority.infrastructure_score = priority_scores["infrastructure_score"]
            existing_priority.update_reason = "analysis_update"
            logger.info("Updated priority scores for legislation ID=%d", legislation_id)
        else:
            # Create new priority
            new_priority = LegislationPriority(
                legislation_id=legislation_id,
                priority_score=priority_scores["overall_score"],
                public_health_score=priority_scores["public_health_score"],
                local_gov_score=priority_scores["local_gov_score"],
                economic_score=priority_scores["economic_score"],
                environmental_score=priority_scores["environmental_score"],
                education_score=priority_scores["education_score"],
                infrastructure_score=priority_scores["infrastructure_score"],
                update_reason="new_analysis"
            )
            analyzer.db_session.add(new_priority)
            logger.info("Created new priority scores for legislation ID=%d", legislation_id)
            
        return True
    except (AttributeError, ValueError, TypeError) as e:
        # More specific exceptions for database/model errors
        logger.error("Error updating legislation priority: %s", e)
        return False

def analyze_impact_trends(analyzer: Any, legislation_ids: List[int]) -> Dict[str, Any]:
    """
    Analyze impact trends across multiple pieces of legislation.
    
    Args:
        analyzer: AIAnalysis instance
        legislation_ids: List of legislation IDs to analyze
        
    Returns:
        Dictionary with trend analysis results
    """
    # Try to import required models
    try:
        if hasattr(analyzer, 'models') and analyzer.models:
            LegislationAnalysis = analyzer.models.LegislationAnalysis  # pylint: disable=invalid-name
            LegislationPriority = analyzer.models.LegislationPriority  # pylint: disable=invalid-name
        else:
            # Try to import locally
            from app.models.legislation_models import LegislationAnalysis, LegislationPriority  # pylint: disable=import-outside-toplevel,invalid-name
    except (ImportError, AttributeError):
        logger.warning("Required models not available for trend analysis")
        return {
            "error": "Required models not available",
            "trend_data": {}
        }
    
    # Collect analysis and priority data
    analysis_data = []
    priority_data = []
    
    try:
        # Query data for each legislation
        for leg_id in legislation_ids:
            # Get latest analysis
            # Use Optional to indicate this could be None
            latest_analysis: Optional[Any] = (
                analyzer.db_session.query(LegislationAnalysis)
                .filter_by(legislation_id=leg_id)
                .order_by(LegislationAnalysis.analysis_version.desc())
                .first()
            )
            
            if latest_analysis:
                analysis_data.append({
                    "legislation_id": leg_id,
                    "summary": latest_analysis.summary,
                    "impact_category": latest_analysis.impact_category.name if latest_analysis.impact_category else None,
                    "impact_level": latest_analysis.impact.name if latest_analysis.impact else None,
                    "insufficient_text": latest_analysis.insufficient_text,
                })
            
            # Get priority data - use Optional to indicate this could be None
            if priority := analyzer.db_session.query(LegislationPriority).filter_by(legislation_id=leg_id).first():
                priority_data.append({
                    "legislation_id": leg_id,
                    "priority_score": priority.priority_score,
                    "public_health_score": priority.public_health_score,
                    "local_gov_score": priority.local_gov_score,
                    "economic_score": priority.economic_score,
                    "environmental_score": priority.environmental_score,
                    "education_score": priority.education_score,
                    "infrastructure_score": priority.infrastructure_score,
                })
    except (AttributeError, ValueError, TypeError) as e:
        logger.error("Error collecting data for trend analysis: %s", e)
        return {
            "error": f"Error collecting data: {str(e)}",
            "trend_data": {}
        }
    
    # Calculate trends
    impact_category_counts = {}
    for item in analysis_data:
        if impact_category := item.get("impact_category"):
            impact_category_counts[impact_category] = impact_category_counts.get(impact_category, 0) + 1
    
    # Calculate average scores
    avg_scores = {}
    if priority_data:
        # Use Tuple to indicate key pairs
        score_fields: Tuple[str, ...] = (
            "priority_score", "public_health_score", "local_gov_score", 
            "economic_score", "environmental_score", "education_score", 
            "infrastructure_score"
        )
        
        for key in score_fields:
            values = [item.get(key, 0) for item in priority_data]
            avg_scores[f"avg_{key}"] = sum(values) / len(values) if values else 0
    
    # Find high priority items
    high_priority_threshold = 70  # Items with score above 70 are considered high priority
    high_priority_items = [
        item for item in priority_data 
        if item.get("priority_score", 0) > high_priority_threshold
    ]
    
    # Return trend results
    return {
        "trend_data": {
            "total_analyzed": len(analysis_data),
            "impact_category_distribution": impact_category_counts,
            "avg_scores": avg_scores,
            "high_priority_count": len(high_priority_items),
            "high_priority_threshold": high_priority_threshold,
        }
    } 