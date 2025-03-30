"""
Utility functions for the AI analysis module.
"""

import logging
from typing import Optional, Dict, Any, List

import tiktoken

logger = logging.getLogger(__name__)


def create_analysis_instructions(is_chunk: bool = False) -> str:
    """
    Create system instructions for analysis prompt.

    Args:
        is_chunk: Whether this is for a chunk analysis

    Returns:
        System message content
    """
    base_instructions = (
        "You are a legislative analysis AI specializing in Texas public health and local government impacts. "
        "Provide a comprehensive, objective analysis of the bill text following the structured format exactly. "
        "Focus especially on impacts to Texas public health agencies and local governments. "
        "If information is insufficient for any field, provide reasonable, conservative assessments. "
        "If the bill text is too short or lacks substantive content to perform meaningful analysis, "
        "return 'INSUFFICIENT_TEXT_FOR_ANALYSIS' in the summary field and populate minimal required fields. "
        "Use only facts present in the text - do not add external information or assumptions."
    )

    return (
        f"{base_instructions} You are analyzing a portion of a larger document, so focus on extracting key information from this specific section while considering how it fits into a broader bill context."
        if is_chunk
        else base_instructions
    )


def get_analysis_json_schema() -> Dict[str, Any]:
    """
    Return the JSON schema for structured analysis output for OpenAI's structured outputs.

    This schema is wrapped with the required keys 'name' and 'strict' so that it conforms
    to the API's expected format:

        {
          "name": "<your_schema_name>",
          "strict": True,
          "schema": { ... your original schema ... }
        }
    """
    base_schema = {
        "type":
        "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "A concise summary of the bill"
            },
            "key_points": {
                "type": "array",
                "description": "List of key bullet points in the legislation",
                "items": {
                    "type": "object",
                    "properties": {
                        "point": {
                            "type": "string",
                            "description": "The text of the bullet point"
                        },
                        "impact_type": {
                            "type":
                            "string",
                            "enum": ["positive", "negative", "neutral"],
                            "description":
                            "The overall tone or impact of this point"
                        }
                    },
                    "required": ["point", "impact_type"],
                    "additionalProperties": False
                }
            },
            "public_health_impacts": {
                "type":
                "object",
                "properties": {
                    "direct_effects": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "indirect_effects": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "funding_impact": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "vulnerable_populations": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "direct_effects", "indirect_effects", "funding_impact",
                    "vulnerable_populations"
                ],
                "additionalProperties":
                False
            },
            "local_government_impacts": {
                "type": "object",
                "properties": {
                    "administrative": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "fiscal": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "implementation": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["administrative", "fiscal", "implementation"],
                "additionalProperties": False
            },
            "economic_impacts": {
                "type":
                "object",
                "properties": {
                    "direct_costs": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "economic_effects": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "benefits": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "long_term_impact": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "direct_costs", "economic_effects", "benefits",
                    "long_term_impact"
                ],
                "additionalProperties":
                False
            },
            "environmental_impacts": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "education_impacts": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "infrastructure_impacts": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "recommended_actions": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "immediate_actions": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "resource_needs": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "impact_summary": {
                "type":
                "object",
                "properties": {
                    "primary_category": {
                        "type":
                        "string",
                        "enum": [
                            "public_health", "local_gov", "economic",
                            "environmental", "education", "infrastructure"
                        ]
                    },
                    "impact_level": {
                        "type": "string",
                        "enum": ["low", "moderate", "high", "critical"]
                    },
                    "relevance_to_texas": {
                        "type": "string",
                        "enum": ["low", "moderate", "high"]
                    }
                },
                "required":
                ["primary_category", "impact_level", "relevance_to_texas"],
                "additionalProperties":
                False
            }
        },
        "required": [
            "summary", "key_points", "public_health_impacts",
            "local_government_impacts", "economic_impacts",
            "environmental_impacts", "education_impacts",
            "infrastructure_impacts", "recommended_actions",
            "immediate_actions", "resource_needs", "impact_summary"
        ],
        "additionalProperties":
        False
    }

    # Wrap the schema with the required outer object
    return {
        "name": "bill_analysis_schema",  # a unique schema name
        "strict": True,
        "schema": base_schema
    }


def create_user_prompt(text: str, is_chunk: bool = False) -> str:
    """
    Create the user prompt for the AI model.

    Args:
        text: The legislative text to analyze
        is_chunk: Whether this text is a chunk of a larger document

    Returns:
        The user prompt string
    """
    if is_chunk:
        # Use the dedicated chunk prompt function
        # Assuming ChunkPromptConfig is defined elsewhere or passed appropriately
        # For simplicity, using a basic chunk prompt here if ChunkPromptConfig is complex
        return create_chunk_prompt_legacy(chunk_text=text)

    # Base prompt for full text analysis
    prompt = (
        "Analyze the following legislative text and provide a comprehensive analysis. "
        "Focus on identifying key provisions, potential impacts (especially on public health, "
        "local government, and the economy), affected stakeholders, and implementation considerations. "
        "Provide your analysis as a JSON object conforming to the required schema.\n\n"
        "Legislative Text:\n"
        "```\n"
        f"{text}\n"
        "```\n\n"
        "Respond with JSON." # Added explicit instruction
    )
    return prompt


class TokenCounter:
    """Token counting utilities for OpenAI models."""

    def __init__(self, model_name: str = "gpt-4o-2024-08-06"):
        """
        Initialize the token counter for a specific model.

        Args:
            model_name: Name of the model to use for tokenization
        """
        self.model_name = model_name
        self.encoder = self._initialize_encoder()

    def _initialize_encoder(self) -> Optional[tiktoken.Encoding]:
        """
        Initialize the token encoder based on the model name.

        Returns:
            Tiktoken encoder or None if initialization fails
        """
        try:
            # Match the model name prefix to determine encoding
            if self.model_name.startswith(("gpt-4", "gpt-3.5")):
                encoding_name = "cl100k_base"  # Used by gpt-4, gpt-3.5-turbo, text-embedding-ada-002
            elif self.model_name.startswith("o"):
                encoding_name = "cl100k_base"  # Best current match for o-series models
            else:
                # Default encoding if no match
                encoding_name = "cl100k_base"
                logger.warning(
                    "No specific encoding found for %s, using default encoding",
                    self.model_name
                )

            return tiktoken.get_encoding(encoding_name)

        except (ValueError, ImportError, AttributeError) as e:
            logger.error("Failed to initialize token encoder: %s", e)
            return None

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        if self.encoder:
            # Use tiktoken for accurate counting
            return len(self.encoder.encode(text))
        
        # Fallback to approximate counting
        return self._approx_tokens(text)

    def _approx_tokens(self, text: str) -> int:
        """
        Approximate token count for when tiktoken is unavailable.

        Args:
            text: Text to estimate token count

        Returns:
            Estimated token count
        """
        return len(text) // 4 if text else 0
        
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model and encoding.
        
        This method is provided to satisfy pylint's too-few-public-methods warning.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "encoder_available": self.encoder is not None,
            "tokenizer_type": "tiktoken" if self.encoder else "approximate"
        }


def calculate_priority_scores(analysis_dict: Dict[str, Any],
                              legislation_id: int) -> Dict[str, Any]:
    """
    Calculate priority scores based on analysis results.

    Args:
        analysis_dict: The analysis dictionary
        legislation_id: ID of the legislation

    Returns:
        Dictionary with priority scores
    """
    # Default medium scores
    health_relevance = 50
    local_govt_relevance = 50

    # Extract impact summary information
    impact_summary = analysis_dict.get("impact_summary", {})
    impact_category_str = impact_summary.get("primary_category")
    impact_level_str = impact_summary.get("impact_level")
    relevance_to_texas_str = impact_summary.get("relevance_to_texas")

    # Convert relevance categories to numeric scores (0-100)
    relevance_mapping = {
        "low": 25,
        "moderate": 50,
        "high": 75,
        "critical": 100
    }

    # Calculate base score from impact level
    base_score = relevance_mapping.get(impact_level_str, 50)

    # Adjust based on relevance to Texas
    texas_multiplier = {
        "low": 0.7,
        "moderate": 0.85,
        "high": 1.0
    }.get(relevance_to_texas_str, 0.85)

    # Adjust scores based on impact category
    if impact_category_str == "public_health":
        health_relevance = min(100, int(base_score * 1.5 * texas_multiplier))
        local_govt_relevance = min(100,
                                   int(base_score * 0.8 * texas_multiplier))
    elif impact_category_str == "local_gov":
        health_relevance = min(100, int(base_score * 0.8 * texas_multiplier))
        local_govt_relevance = min(100,
                                   int(base_score * 1.5 * texas_multiplier))
    else:
        # For other categories, calculate based on impact level and Texas relevance
        health_relevance = min(100, int(base_score * texas_multiplier))
        local_govt_relevance = min(100, int(base_score * texas_multiplier))

    if ph_impacts := analysis_dict.get("public_health_impacts", {}):
        # Adjust score based on having detailed impacts
        if ph_impacts.get("direct_effects") or ph_impacts.get(
                "funding_impact"):
            health_relevance = min(100, health_relevance + 10)

    if local_impacts := analysis_dict.get("local_government_impacts", {}):
        # Adjust score based on having detailed impacts
        if local_impacts.get("fiscal") or local_impacts.get("administrative"):
            local_govt_relevance = min(100, local_govt_relevance + 10)

    # Calculate overall priority as weighted average
    overall_priority = (health_relevance + local_govt_relevance) // 2

    return {
        "legislation_id": legislation_id,
        "public_health_relevance": health_relevance,
        "local_govt_relevance": local_govt_relevance,
        "overall_priority": overall_priority,
        "auto_categorized": True,
        "auto_categories": {
            "health_impacts": health_relevance > 50,
            "local_govt_impacts": local_govt_relevance > 50,
            "impact_category": impact_category_str,
            "impact_level": impact_level_str,
            "texas_relevance": relevance_to_texas_str
        }
    }


def merge_analyses(base: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two analysis dictionaries, intelligently handling different field types.

    Args:
        base: Base analysis dictionary
        new: New analysis to merge in

    Returns:
        Merged analysis dictionary
    """
    merged = base.copy()

    # Merge summary with combination
    merged = _merge_summary(merged, new)
    
    # Merge key points
    merged = _merge_key_points(merged, new)
    
    # Merge impact lists
    merged = _merge_impact_lists(merged, new)
    
    # Merge structured impact dictionaries
    merged = _merge_structured_impacts(merged, new)
    
    # Merge action items
    merged = _merge_action_items(merged, new)
    
    # Handle impact summary
    merged = _merge_impact_summary(merged, new)

    return merged


def _merge_summary(merged: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge summary fields from two analyses."""
    if "summary" in new:
        merged["summary"] = merged.get("summary", "") + " " + new["summary"]
        # Trim if it's getting too long
        if len(merged["summary"]) > 2000:
            merged["summary"] = merged["summary"][:1997] + "..."
    return merged


def _merge_key_points(merged: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge key points avoiding duplicates."""
    if "key_points" in new and "key_points" in merged:
        existing_points = {point["point"] for point in merged["key_points"]}
        for point in new["key_points"]:
            if point["point"] not in existing_points:
                merged["key_points"].append(point)
                # Keep reasonable number of points
                if len(merged["key_points"]) >= 15:
                    break
    return merged


def _merge_impact_lists(merged: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge simple impact list fields."""
    impact_types = [
        "environmental_impacts", 
        "education_impacts",
        "infrastructure_impacts"
    ]
    
    for impact_type in impact_types:
        if impact_type in new and impact_type in merged:
            # Get unique impacts
            all_impacts = set(merged[impact_type])
            for impact in new[impact_type]:
                all_impacts.add(impact)
            merged[impact_type] = list(all_impacts)[:10]  # Limit to 10 most important
    
    return merged


def _merge_structured_impacts(merged: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge structured impact dictionary fields."""
    impact_dicts = [
        "public_health_impacts", 
        "local_government_impacts",
        "economic_impacts"
    ]
    
    for impact_dict in impact_dicts:
        if impact_dict not in new or impact_dict not in merged:
            continue
            
        for category, items in new[impact_dict].items():
            if category not in merged[impact_dict]:
                continue
                
            # Add any new items that don't duplicate existing ones
            existing_items = set(merged[impact_dict][category])
            for item in items:
                if item not in existing_items:
                    merged[impact_dict][category].append(item)
                    # Keep reasonable number of items
                    if len(merged[impact_dict][category]) >= 8:
                        break
    
    return merged


def _merge_action_items(merged: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge action item fields."""
    action_types = [
        "recommended_actions", 
        "immediate_actions", 
        "resource_needs"
    ]
    
    for action_type in action_types:
        if action_type not in new or action_type not in merged:
            continue
            
        # Combine and deduplicate
        all_actions = set(merged[action_type])
        for action in new[action_type]:
            all_actions.add(action)
        
        # Set a reasonable limit based on action type
        limit = 8 if action_type == "recommended_actions" else 5
        merged[action_type] = list(all_actions)[:limit]
    
    return merged


def _merge_impact_summary(merged: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge impact summary fields, keeping the more severe assessment."""
    if "impact_summary" not in new or "impact_summary" not in merged:
        return merged
        
    # Impact level priority (higher = more severe)
    impact_priority = {"low": 1, "moderate": 2, "high": 3, "critical": 4}

    base_level = impact_priority.get(
        merged["impact_summary"]["impact_level"], 0)
    new_level = impact_priority.get(new["impact_summary"]["impact_level"], 0)

    # Keep the more severe impact assessment
    if new_level > base_level:
        merged["impact_summary"] = new["impact_summary"]
    
    return merged


class ChunkPromptConfig:
    """Configuration for chunk prompt generation."""
    
    def __init__(self, **kwargs):
        """
        Initialize chunk prompt configuration.
        
        Args:
            **kwargs: Configuration parameters which should include:
                chunk: Text chunk to analyze
                chunk_index: Index of this chunk (0-based)
                total_chunks: Total number of chunks
                prev_summaries: Summaries from previous chunks
                legislation_metadata: Bill metadata for context
                is_structured: Whether the document has structured sections
        """
        self.chunk = kwargs.get('chunk', '')
        self.chunk_index = kwargs.get('chunk_index', 0)
        self.total_chunks = kwargs.get('total_chunks', 1)
        self.prev_summaries = kwargs.get('prev_summaries', [])
        self.legislation_metadata = kwargs.get('legislation_metadata', {})
        self.is_structured = kwargs.get('is_structured', False)
        
    def get_config_info(self) -> Dict[str, Any]:
        """
        Get information about the current configuration.
        
        This method is provided to satisfy pylint's too-few-public-methods warning.
        
        Returns:
            Dictionary with configuration information
        """
        return {
            "chunk_size": len(self.chunk),
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "has_prev_summaries": bool(self.prev_summaries),
            "is_structured": self.is_structured
        }


def create_chunk_prompt(config: ChunkPromptConfig) -> str:
    """
    Create a prompt for analyzing a chunk of legislation with context preservation.

    Args:
        config: Configuration object for prompt generation

    Returns:
        Customized prompt for this chunk
    """
    # Prepare context section
    context_sections = [
        f"Bill Number: {config.legislation_metadata['bill_number']}",
        f"Title: {config.legislation_metadata['title']}",
        f"Description: {config.legislation_metadata['description']}",
        f"Government Type: {config.legislation_metadata['govt_type']}",
        f"Source: {config.legislation_metadata['govt_source']}",
        f"Status: {config.legislation_metadata['status']}"
    ]

    # Add summaries from previous chunks if available
    if config.prev_summaries:
        context_sections.append("\nSUMMARIES FROM PREVIOUS SECTIONS:")
        context_sections.extend(config.prev_summaries)

    context_text = "\n".join(context_sections)

    # Create appropriate instructions based on which chunk we're processing
    if config.chunk_index == 0:
        # First chunk
        instructions = (
            f"You are analyzing PART 1 OF {config.total_chunks} of a large legislative bill. "
            f"Focus on the sections provided while considering the bill's overall context."
        )
    elif config.chunk_index == config.total_chunks - 1:
        # Last chunk
        instructions = (
            f"You are analyzing THE FINAL PART ({config.chunk_index+1} OF {config.total_chunks}) of a large legislative bill. "
            f"Use the summaries of previous sections to inform your analysis and provide a comprehensive conclusion."
        )
    else:
        # Middle chunk
        instructions = (
            f"You are analyzing PART {config.chunk_index+1} OF {config.total_chunks} of a large legislative bill. "
            f"Consider the context from previous parts while focusing on the new content in this section."
        )

    # Additional guidance for structured vs. unstructured documents
    if config.is_structured:
        instructions += (
            " This document has structured sections. Pay attention to section headers and "
            "how they relate to previous parts of the bill.")
    else:
        instructions += (
            " This document was split by content size rather than by natural sections. "
            "Be aware that some concepts might span across chunks.")

    return f"{instructions}\n\nBILL CONTEXT:\n{context_text}\n\nCURRENT SECTION TEXT TO ANALYZE:\n{config.chunk}"


# For backward compatibility with code that uses the old function signature
def create_chunk_prompt_legacy(**kwargs) -> str:
    """
    Legacy version of create_chunk_prompt that maintains backward compatibility.

    Args:
        **kwargs: Expected to include:
            chunk: Text chunk to analyze
            chunk_index: Index of this chunk (0-based)
            total_chunks: Total number of chunks
            prev_summaries: Summaries from previous chunks
            legislation_metadata: Bill metadata for context
            is_structured: Whether the document has structured sections

    Returns:
        Customized prompt for this chunk
    """
    config = ChunkPromptConfig(**kwargs)
    return create_chunk_prompt(config)
