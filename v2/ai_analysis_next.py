import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

import openai
from sqlalchemy.orm import Session

from models import (
    Legislation,
    LegislationText,
    LegislationAnalysis,
    ImpactCategoryEnum,
    ImpactLevelEnum
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AIAnalysis:
    """
    The AIAnalysis class orchestrates generating a structured legislative analysis
    (including summary, key points, detailed impacts, and recommended actions) using
    OpenAI's ChatCompletion API. The analysis is stored in the LegislationAnalysis model
    with versioning. This class uses a strict JSON schema for its response.
    """

    def __init__(
        self,
        db_session: Session,
        openai_api_key: Optional[str] = None,
        model_name: str = "gpt-4o-2024-08-06",
        max_context_tokens: int = 120_000,
        safety_buffer: int = 20_000
    ):
        """
        Initialize the AIAnalysis instance.

        Args:
            db_session (Session): SQLAlchemy Session for DB operations.
            openai_api_key (Optional[str]): API key for OpenAI; uses OPENAI_API_KEY env var if not provided.
            model_name (str): The name of the GPT-4o model to use.
            max_context_tokens (int): Approximate maximum context size (default 120k tokens).
            safety_buffer (int): Token buffer to avoid exceeding the model's limit.
        """
        self.db_session = db_session

        self.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is missing; set OPENAI_API_KEY or pass in openai_api_key.")
        openai.api_key = self.api_key

        self.model_name = model_name
        self.max_context_tokens = max_context_tokens
        self.safety_buffer = safety_buffer

    def analyze_legislation(self, legislation_id: int) -> LegislationAnalysis:
        """
        Produce or update an AI-based analysis for a Legislation record.

        The method follows these steps:
          1. Retrieve the Legislation record and its latest text.
          2. Estimate token count; if text exceeds safe limits, split and use the first chunk.
          3. Call OpenAI's ChatCompletion API using a strict JSON schema.
          4. Parse the response and store it in a new LegislationAnalysis record, with versioning.

        Args:
            legislation_id (int): The ID of the Legislation record to analyze.

        Returns:
            LegislationAnalysis: The newly created analysis record.
        """
        # 1) Load the legislation record.
        leg_obj = self.db_session.query(Legislation).filter_by(id=legislation_id).first()
        if not leg_obj:
            raise ValueError(f"Legislation with ID={legislation_id} not found in the DB.")

        # 2) Retrieve full text from the latest text record or use the description.
        text_rec = leg_obj.latest_text
        if text_rec and text_rec.text_content:
            full_text = text_rec.text_content
        else:
            full_text = leg_obj.description or ""

        # 3) Estimate token count; if over safe limit, split the text.
        token_estimate = self._approx_tokens(full_text)
        safe_limit = self.max_context_tokens - self.safety_buffer
        if token_estimate > safe_limit:
            logger.warning(f"Legislation {legislation_id} is ~{token_estimate} tokens, chunking to ~{safe_limit}")
            chunks = self._split_text(full_text, chunk_size=safe_limit)
            text_for_analysis = chunks[0]
        else:
            text_for_analysis = full_text

        # 4) Call OpenAI API for structured analysis.
        logger.info(f"[AIAnalysis] Calling structured analysis for Legislation {legislation_id} with model={self.model_name}")
        analysis_data = self._call_structured_analysis(text_for_analysis)

        # 5) Store the analysis in the database and return it.
        result_analysis = self._store_legislation_analysis(legislation_id, analysis_data)
        return result_analysis

    def _call_structured_analysis(self, text: str) -> Dict[str, Any]:
        """
        Calls OpenAI's ChatCompletion API with a strict JSON schema to analyze the provided text.

        The schema includes:
          - summary: A concise summary of the bill.
          - key_points: An array of bullet points with an associated impact type.
          - Detailed impacts for public health, local government, economic effects,
            environmental, education, and infrastructure.
          - Recommended actions, immediate actions, and resource needs.

        Returns:
            Dict[str, Any]: The parsed JSON analysis or an empty dictionary on error.
        """
        schema_definition = {
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A concise summary of the bill."
                    },
                    "key_points": {
                        "type": "array",
                        "description": "List of key bullet points in the legislation.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "point": {
                                    "type": "string",
                                    "description": "The text of the bullet point."
                                },
                                "impact_type": {
                                    "type": "string",
                                    "enum": ["positive", "negative", "neutral"],
                                    "description": "The overall tone or impact of this point."
                                }
                            },
                            "required": ["point", "impact_type"],
                            "additionalProperties": False
                        }
                    },
                    "public_health_impacts": {
                        "type": "object",
                        "properties": {
                            "direct_effects": {"type": "array", "items": {"type": "string"}},
                            "indirect_effects": {"type": "array", "items": {"type": "string"}},
                            "funding_impact": {"type": "array", "items": {"type": "string"}},
                            "vulnerable_populations": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["direct_effects", "indirect_effects", "funding_impact", "vulnerable_populations"],
                        "additionalProperties": False
                    },
                    "local_government_impacts": {
                        "type": "object",
                        "properties": {
                            "administrative": {"type": "array", "items": {"type": "string"}},
                            "fiscal": {"type": "array", "items": {"type": "string"}},
                            "implementation": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["administrative", "fiscal", "implementation"],
                        "additionalProperties": False
                    },
                    "economic_impacts": {
                        "type": "object",
                        "properties": {
                            "direct_costs": {"type": "array", "items": {"type": "string"}},
                            "economic_effects": {"type": "array", "items": {"type": "string"}},
                            "benefits": {"type": "array", "items": {"type": "string"}},
                            "long_term_impact": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["direct_costs", "economic_effects", "benefits", "long_term_impact"],
                        "additionalProperties": False
                    },
                    "environmental_impacts": {"type": "array", "items": {"type": "string"}},
                    "education_impacts": {"type": "array", "items": {"type": "string"}},
                    "infrastructure_impacts": {"type": "array", "items": {"type": "string"}},
                    "recommended_actions": {"type": "array", "items": {"type": "string"}},
                    "immediate_actions": {"type": "array", "items": {"type": "string"}},
                    "resource_needs": {"type": "array", "items": {"type": "string"}}
                },
                "required": [
                    "summary", "key_points",
                    "public_health_impacts", "local_government_impacts", "economic_impacts",
                    "environmental_impacts", "education_impacts", "infrastructure_impacts",
                    "recommended_actions", "immediate_actions", "resource_needs"
                ],
                "additionalProperties": False
            }
        }

        system_message = (
            "You are a legislative analysis AI. Produce valid JSON only that matches the provided schema. "
            "Do not include any additional commentary. If information is missing, use empty arrays or placeholders."
        )

        user_message = (
            "Bill text:\n"
            f"{text}\n\n"
            "Analyze the bill text and return a JSON response that includes: summary, key_points, "
            "public_health_impacts, local_government_impacts, economic_impacts, environmental_impacts, "
            "education_impacts, infrastructure_impacts, recommended_actions, immediate_actions, and resource_needs. "
            "Ensure the JSON strictly adheres to the provided schema."
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]

        try:
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=messages,
                temperature=0.25,
                response_format={
                    "type": "json_schema",
                    "json_schema": schema_definition
                },
            )
            choice_content = response.choices[0]["message"]
            if "refusal" in choice_content and choice_content["refusal"]:
                logger.error("OpenAI refused to provide analysis. Returning empty result.")
                return {}
            if hasattr(choice_content, "parsed") and choice_content.parsed:
                analysis_data = choice_content.parsed
            else:
                raw_str = choice_content.get("content", "")
                analysis_data = self._safe_json_load(raw_str)
            return analysis_data if analysis_data else {}
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAIError from structured analysis: {e}", exc_info=True)
            return {}
        except Exception as exc:
            logger.error(f"Unknown error from structured analysis: {exc}", exc_info=True)
            return {}

    def _store_legislation_analysis(self, legislation_id: int, analysis_dict: Dict[str, Any]) -> LegislationAnalysis:
        """
        Stores the analysis data as a new LegislationAnalysis record. If previous analyses exist,
        it increments the analysis version and links to the previous version.

        Args:
            legislation_id (int): The ID of the legislation record.
            analysis_dict (Dict[str, Any]): The structured analysis data from OpenAI.

        Returns:
            LegislationAnalysis: The newly created analysis record.
        """
        existing_analyses = self.db_session.query(LegislationAnalysis).filter_by(
            legislation_id=legislation_id
        ).all()
        if existing_analyses:
            prev = max(existing_analyses, key=lambda x: x.analysis_version)
            new_version = prev.analysis_version + 1
            prev_id = prev.id
        else:
            new_version = 1
            prev_id = None

        analysis_obj = LegislationAnalysis(
            legislation_id=legislation_id,
            analysis_version=new_version,
            previous_version_id=prev_id,
            analysis_date=datetime.utcnow(),
            summary=analysis_dict.get("summary", ""),
            key_points=analysis_dict.get("key_points", []),
            public_health_impacts=analysis_dict.get("public_health_impacts", {}),
            local_gov_impacts=analysis_dict.get("local_government_impacts", {}),
            economic_impacts=analysis_dict.get("economic_impacts", {}),
            stakeholder_impacts={},  # Not provided in this schema example.
            recommended_actions=analysis_dict.get("recommended_actions", []),
            immediate_actions=analysis_dict.get("immediate_actions", []),
            resource_needs=analysis_dict.get("resource_needs", []),
            raw_analysis=analysis_dict,
            model_version=self.model_name,
            confidence_score=None,
            processing_time=None,
            impact_category=analysis_dict.get("impact_category"),  # Simplified impact category (if provided)
            impact=analysis_dict.get("impact")  # Simplified overall impact level (if provided)
        )
        self.db_session.add(analysis_obj)
        self.db_session.commit()
        logger.info(f"[AIAnalysis] Created new LegislationAnalysis (version={new_version}) for Legislation {legislation_id}")
        return analysis_obj

    def _approx_tokens(self, text: str) -> int:
        """
        Approximates the token count for the provided text.
        
        Returns:
            int: Estimated token count (rough approximation using ~4 characters per token).
        """
        return len(text) // 4

    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """
        Splits the input text into chunks based on an approximate token limit.

        Args:
            text (str): The text to split.
            chunk_size (int): The approximate maximum token count per chunk.

        Returns:
            List[str]: A list of text chunks.
        """
        words = text.split()
        chunks = []
        current_words = []
        current_count = 0
        for word in words:
            word_tokens = max(1, len(word) // 4)
            if current_count + word_tokens > chunk_size:
                chunks.append(" ".join(current_words))
                current_words = [word]
                current_count = word_tokens
            else:
                current_words.append(word)
                current_count += word_tokens
        if current_words:
            chunks.append(" ".join(current_words))
        logger.info(f"[AIAnalysis] Text split into {len(chunks)} chunk(s).")
        return chunks

    def _safe_json_load(self, raw_str: str) -> dict:
        """
        Safely loads a JSON string.

        Args:
            raw_str (str): The raw JSON string to parse.

        Returns:
            dict: The parsed JSON object, or an empty dict if parsing fails.
        """
        try:
            return json.loads(raw_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error. Raw content (first 200 chars): {raw_str[:200]}..., error: {e}")
            return {}
