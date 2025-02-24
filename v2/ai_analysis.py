"""
ai_analysis.py

Provides a production-grade AIAnalysis class that:
  1) Retrieves the full bill text from Legislation + LegislationText in the database
  2) (Optionally) splits it if it exceeds ~100k tokens (for large ~120k context models)
  3) Calls OpenAI's ChatCompletion with a strict JSON schema
  4) Receives a fully structured JSON with summary, key points, multiple impacts, recommended actions, etc.
  5) Stores the results in a new LegislationAnalysis record, versioning them if needed.

Prerequisites:
 - The 'models.py' must define Legislation, LegislationText, LegislationAnalysis, etc.
 - pip install openai (and ensure OPENAI_API_KEY is set or passed to constructor)
 - A GPT-4o model that supports structured outputs is recommended (e.g. "gpt-4o-2024-08-06" or later).

Usage:
    from sqlalchemy.orm import Session
    from models import init_db
    from ai_analysis import AIAnalysis

    SessionFactory = init_db()
    db_session = SessionFactory()
    ai = AIAnalysis(db_session=db_session, model_name="gpt-4o-2024-08-06")
    analysis = ai.analyze_legislation(legislation_id=123)  # ID from Legislation table
    print("Analysis version:", analysis.analysis_version)
"""

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
    LegislationAnalysis
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AIAnalysis:
    """
    The AIAnalysis class orchestrates generating a structured legislative analysis
    (summary, key points, multiple impacts, recommended actions, etc.) from OpenAI
    and storing it in LegislationAnalysis with version control.
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
        :param db_session: SQLAlchemy Session for DB operations
        :param openai_api_key: Optionally pass in an OpenAI API key, else it uses OPENAI_API_KEY env var
        :param model_name: Name of the GPT-4o model to call
        :param max_context_tokens: The approximate max context size (default 120k)
        :param safety_buffer: A buffer to subtract from max_context_tokens to avoid going over
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
        Main method to produce or update an AI-based analysis for a Legislation record.
        
        Steps:
         1) Fetch the Legislation + LegislationText from DB.
         2) If extremely large (approx > 100k tokens), chunk and use the first chunk as a fallback.
         3) Call the single structured JSON schema completion.
         4) Parse and store in a new LegislationAnalysis row (versioned).

        Returns the newly created LegislationAnalysis object.
        """
        # 1) Load the legislation from DB
        leg_obj = self.db_session.query(Legislation).filter_by(id=legislation_id).first()
        if not leg_obj:
            raise ValueError(f"Legislation with ID={legislation_id} not found in the DB.")

        # 2) Get full text (or fallback to description)
        text_rec = leg_obj.latest_text
        if text_rec and text_rec.text_content:
            full_text = text_rec.text_content
        else:
            full_text = leg_obj.description or ""

        # 3) Check approximate tokens
        token_estimate = self._approx_tokens(full_text)
        safe_limit = self.max_context_tokens - self.safety_buffer
        if token_estimate > safe_limit:
            logger.warning(f"Legislation {legislation_id} is ~{token_estimate} tokens, chunking to ~{safe_limit}")
            chunks = self._split_text(full_text, chunk_size=safe_limit)
            text_for_analysis = chunks[0]
        else:
            text_for_analysis = full_text

        # 4) Make the single structured analysis call
        logger.info(f"[AIAnalysis] Calling structured analysis for Legislation {legislation_id} with model={self.model_name}")
        analysis_data = self._call_structured_analysis(text_for_analysis)

        # 5) Save the new LegislationAnalysis record
        result_analysis = self._store_legislation_analysis(legislation_id, analysis_data)
        return result_analysis

    # --------------------------------------------------------------------------
    # Internal: Call the ChatCompletion with a strict JSON schema
    # --------------------------------------------------------------------------
    def _call_structured_analysis(self, text: str) -> Dict[str, Any]:
        """
        Creates a single ChatCompletion request with a strict JSON schema that covers:
          - summary (string)
          - key_points (array of { point: string, impact_type: 'positive|negative|neutral'})
          - multiple impacts: public_health, local_government, economic, environmental, education, infrastructure
          - recommended_actions, immediate_actions, resource_needs (arrays of strings or objects)
        
        Returns a Python dict with all required fields, or fallback empty dict on error.
        """
        # 1) Build the schema
        # Note: All fields must be required. AdditionalProperties must be false. This ensures strictness.
        # Some fields are arrays with nested objects. Use "type": "object" with sub-props for each.
        # This is an example schema—modify or extend as needed for your actual data structure.
        schema_definition = {
            "strict": True,
            "schema": {
                "type": "object",
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
                                    "type": "string",
                                    "enum": ["positive", "negative", "neutral"],
                                    "description": "The overall tone or impact of this point"
                                }
                            },
                            "required": ["point", "impact_type"],
                            "additionalProperties": False
                        }
                    },
                    "public_health_impacts": {
                        "type": "object",
                        "properties": {
                            "direct_effects": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "indirect_effects": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "funding_impact": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "vulnerable_populations": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["direct_effects", "indirect_effects", "funding_impact", "vulnerable_populations"],
                        "additionalProperties": False
                    },
                    "local_government_impacts": {
                        "type": "object",
                        "properties": {
                            "administrative": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "fiscal": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "implementation": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["administrative", "fiscal", "implementation"],
                        "additionalProperties": False
                    },
                    "economic_impacts": {
                        "type": "object",
                        "properties": {
                            "direct_costs": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "economic_effects": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "benefits": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "long_term_impact": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["direct_costs", "economic_effects", "benefits", "long_term_impact"],
                        "additionalProperties": False
                    },
                    "environmental_impacts": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "education_impacts": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "infrastructure_impacts": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "recommended_actions": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "immediate_actions": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "resource_needs": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
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

        # 2) Construct the system message and user prompt
        # Be verbose with instructions to ensure the model knows how to fill each field.
        system_message = (
            "You are a legislative analysis AI. You must produce valid JSON ONLY that matches the schema. "
            "We have many required fields, each describing aspects of the bill's impacts and recommended actions. "
            "No extra commentary—only the JSON that fits the schema exactly. "
            "If you cannot comply or the text is insufficient, fill empty arrays or strings where needed."
        )

        user_message = (
            "Bill text:\n"
            f"{text}\n\n"
            "Please carefully analyze it and produce a structured JSON response with:\n"
            "summary, key_points, public_health_impacts, local_government_impacts, economic_impacts, "
            "environmental_impacts, education_impacts, infrastructure_impacts, recommended_actions, "
            "immediate_actions, and resource_needs. "
            "Each sub-field must follow the schema definitions provided. "
            "If uncertain, provide empty arrays or minimal placeholders that still match the schema."
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
                # You could set max_completion_tokens if desired:
                # "max_completion_tokens": 2048
            )
            # The structured response is guaranteed to be valid JSON matching the schema, or
            # the API will raise an error. The refusal scenario can appear as a "refusal" property.
            choice_content = response.choices[0]["message"]
            
            # Check for refusal
            if "refusal" in choice_content and choice_content["refusal"]:
                logger.error("OpenAI refused to provide analysis. Returning empty.")
                return {}

            # If no refusal, the parsed content is in `message.parsed` if using openai-python with .parse,
            # but in raw usage, the JSON body is in message["content"] for older styles. 
            # For new structured outputs (python openai >= 0.28.0), we can do:
            #   analysis_data = response.choices[0].message.parsed
            # If we do not have that attribute, we can do:
            #   analysis_data = json.loads(response.choices[0]["message"]["content"])
            # But structured outputs auto-parse for us with openai 0.28.0+:
            
            # Attempt to read the final result from the new attribute "parsed"
            if hasattr(choice_content, "parsed") and choice_content.parsed:
                analysis_data = choice_content.parsed
            else:
                # fallback approach if the library version doesn't parse for us:
                # message["content"] should be valid JSON
                raw_str = choice_content.get("content", "")
                analysis_data = self._safe_json_load(raw_str)

            return analysis_data if analysis_data else {}

        except openai.error.OpenAIError as e:
            logger.error(f"OpenAIError from structured analysis: {e}", exc_info=True)
            return {}
        except Exception as exc:
            logger.error(f"Unknown error from structured analysis: {exc}", exc_info=True)
            return {}

    # --------------------------------------------------------------------------
    # Internal: Store the final analysis in LegislationAnalysis with versioning
    # --------------------------------------------------------------------------
    def _store_legislation_analysis(
        self, legislation_id: int, analysis_dict: Dict[str, Any]
    ) -> LegislationAnalysis:
        """
        Creates a new LegislationAnalysis row or increments the version if existing ones exist.
        :param legislation_id: The ID of the legislation
        :param analysis_dict: The final structured analysis data
        :return: The newly created LegislationAnalysis object
        """
        # Check for existing analyses
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

        # Create the new analysis record
        analysis_obj = LegislationAnalysis(
            legislation_id=legislation_id,
            analysis_version=new_version,
            previous_version_id=prev_id,
            analysis_date=datetime.utcnow(),
            # Basic fields from the schema
            summary=analysis_dict.get("summary", ""),
            key_points=analysis_dict.get("key_points", []),
            # The next fields can be stored in JSONB columns. If you have
            # them as separate columns, adapt accordingly. 
            public_health_impacts=analysis_dict.get("public_health_impacts", {}),
            local_gov_impacts=analysis_dict.get("local_government_impacts", {}),
            economic_impacts=analysis_dict.get("economic_impacts", {}),
            stakeholder_impacts={},  # Not used in this schema example
            recommended_actions=analysis_dict.get("recommended_actions", []),
            immediate_actions=analysis_dict.get("immediate_actions", []),
            resource_needs=analysis_dict.get("resource_needs", []),

            # For environment, education, infrastructure, you might store them in raw_analysis
            # or add columns if you want. We'll store them in raw_analysis for now:
            raw_analysis=analysis_dict,
            # Or you might parse them out:
            # environment_impacts=analysis_dict.get("environmental_impacts", []),
            # education_impacts=analysis_dict.get("education_impacts", []),
            # infrastructure_impacts=analysis_dict.get("infrastructure_impacts", []),

            model_version=self.model_name,
            confidence_score=None,
            processing_time=None
        )
        self.db_session.add(analysis_obj)
        self.db_session.commit()

        logger.info(
            f"[AIAnalysis] Created new LegislationAnalysis (version={new_version}) for Legislation {legislation_id}"
        )
        return analysis_obj

    # --------------------------------------------------------------------------
    # Helper: approximate token count & naive chunking
    # --------------------------------------------------------------------------
    def _approx_tokens(self, text: str) -> int:
        """
        A naive approximation. In production, you might prefer 
        tiktoken or another real token counting approach. 
        """
        return len(text) // 4  # Roughly ~4 chars per token

    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """
        Splits the text on word boundaries so that each chunk is within chunk_size tokens (approx).
        Only the first chunk is used if multiple. 
        """
        words = text.split()
        chunks = []
        current_words = []
        current_count = 0

        for w in words:
            w_tokens = max(1, len(w) // 4)
            if current_count + w_tokens > chunk_size:
                chunks.append(" ".join(current_words))
                current_words = [w]
                current_count = w_tokens
            else:
                current_words.append(w)
                current_count += w_tokens

        if current_words:
            chunks.append(" ".join(current_words))

        logger.info(f"[AIAnalysis] Text was split into {len(chunks)} chunk(s).")
        return chunks

    # --------------------------------------------------------------------------
    # Helper: safe JSON load
    # --------------------------------------------------------------------------
    def _safe_json_load(self, raw_str: str) -> dict:
        """
        Attempt to parse raw JSON string. Return empty dict on failure.
        """
        try:
            return json.loads(raw_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error. raw_str={raw_str[:200]}..., error={e}")
            return {}

