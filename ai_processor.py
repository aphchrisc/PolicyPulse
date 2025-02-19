"""
File: ai_processor.py

Contains the AIProcessor class that interacts with OpenAI to generate summaries,
detailed analysis, and reports.
"""

import json
import os
import logging
import re
from datetime import datetime
from typing import Dict
from openai import OpenAI  # Using the new client-based call format
from models import LegislationTracker

logger = logging.getLogger(__name__)


class AIProcessor:
    def __init__(self):
        """Initialize the AI processor with an OpenAI client"""
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API key not found in environment variables")
        # Instantiate the client using the new call format
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"  # DO NOT MODIFY 

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON content from a string that may include markdown code fences.
        For example, converts:
        ```json
        { "key": "value" }
        ```
        to just: { "key": "value" }
        """
        pattern = r"```(?:json)?\s*(\{.*\})\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def determine_impact_levels(self, analysis: dict, bill_number: str, db_session) -> bool:
        """Determine impact levels for public health and local government officials."""
        try:
            if not self.api_key:
                logger.warning(f"Bill {bill_number}: OpenAI API key not found - impact level analysis unavailable")
                return False

            logger.info(f"Starting impact level determination for bill {bill_number}")

            # Prepare a condensed version of the analysis for the prompt
            analysis_summary = {
                "summary": analysis.get("summary", ""),
                "key_points": analysis.get("key_points", []),
                "public_health_impacts": analysis.get("public_health_impacts", {}),
                "overall_assessment": analysis.get("overall_assessment", {})
            }

            logger.info(f"Sending impact analysis request to OpenAI for bill {bill_number}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_impact_system_prompt()},
                    {"role": "user", "content": self._get_impact_analysis_prompt(analysis_summary)}
                ],
                temperature=0.3,
                max_completion_tokens=1000,
                response_format={"type": "json_object"}
            )
            logger.info(f"Received OpenAI response for bill {bill_number}")

            # Log the raw response content for debugging
            content = response.choices[0].message.content.strip()
            logger.info(f"Raw OpenAI response for bill {bill_number}: {content}")

            # Extract JSON from the content if it's wrapped in markdown code fences
            content = self._extract_json(content)
            logger.info(f"Extracted JSON content for bill {bill_number}: {content}")

            try:
                impact_levels = json.loads(content)
                logger.info(f"Successfully parsed impact levels for bill {bill_number}: {impact_levels}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response for bill {bill_number}: {e}\nRaw content: {content}")
                return False

            # Update the database with the determined impact levels
            try:
                bill = db_session.query(LegislationTracker).filter_by(bill_number=bill_number).first()
                if bill:
                    old_ph_impact = bill.public_health_impact
                    old_lg_impact = bill.local_gov_impact

                    # Update both impact levels and their reasoning
                    bill.public_health_impact = impact_levels.get('public_health_impact_level', 'unknown')
                    bill.local_gov_impact = impact_levels.get('local_gov_impact_level', 'unknown')
                    bill.public_health_reasoning = impact_levels.get('public_health_reasoning')
                    bill.local_gov_reasoning = impact_levels.get('local_gov_reasoning')
                    bill.last_updated = datetime.now()

                    logger.info(f"""Impact levels updated for bill {bill_number}:
                        Public Health: {old_ph_impact} -> {bill.public_health_impact}
                        Local Gov: {old_lg_impact} -> {bill.local_gov_impact}
                        Public Health Reasoning: {bill.public_health_reasoning}
                        Local Gov Reasoning: {bill.local_gov_reasoning}""")

                    db_session.commit()
                    return True
                else:
                    logger.warning(f"No bill found with number {bill_number}")
                    return False
            except Exception as db_error:
                logger.error(f"Database error updating impact levels for bill {bill_number}: {db_error}")
                db_session.rollback()
                return False

        except Exception as e:
            logger.error(f"Error determining impact levels for bill {bill_number}: {e}")
            return False

    def _get_impact_system_prompt(self) -> str:
        return (
            "You are an expert legislative analyst specializing in determining the urgency and importance "
            "of bills for public health and local government officials. Your task is to evaluate legislative analysis and "
            "determine how urgently officials should review the legislation. YOU MUST RETURN A VALID JSON OBJECT."
        )

    def _get_impact_analysis_prompt(self, analysis_summary: dict) -> str:
        return f"""Based on this legislative analysis, determine the impact level for both public health officials
and local government officials. Consider factors such as:

For Public Health Impact Level:
- Immediacy of health impacts
- Scope of affected population
- Changes to health system operations
- Resource requirements
- Regulatory compliance needs

For Local Government Impact Level:
- Operational changes required
- Budget implications
- Implementation timeline
- Staff training needs
- Community impact

Analysis to evaluate:
{json.dumps(analysis_summary, indent=2)}

YOU MUST RETURN A VALID JSON OBJECT USING THIS EXACT STRUCTURE - NO OTHER TEXT:
{{
    "public_health_impact_level": "high|medium|low",
    "public_health_reasoning": "Brief explanation of the impact level",
    "local_gov_impact_level": "high|medium|low",
    "local_gov_reasoning": "Brief explanation of the impact level"
}}

Use these criteria for levels:
HIGH: Immediate attention required, significant changes or impacts
MEDIUM: Review needed but not urgent, moderate changes or impacts
LOW: Minimal direct impact, routine review sufficient

IMPORTANT: Return only the JSON object - no other text, comments, or explanations.
"""

    def analyze_legislation(self, text: str, bill_number: str, db_session) -> bool:
        """
        Perform detailed analysis of bill text with focus on public health and local government impacts.
        Stores results in database.
        """
        try:
            if not self.api_key:
                logger.error("OpenAI API key not configured")
                return False

            logger.info(f"Starting AI analysis for bill {bill_number}")
            max_length = 40000
            if len(text) > max_length:
                text = text[:max_length] + "..."
                logger.info(f"Truncated bill text to {max_length} characters")

            system_prompt = (
                "You are an expert legislative analyst specializing in public health policy and local government impact assessment. "
                "Analyze bills to identify specific impacts on public health systems, local government operations, and financial implications "
                "for both institutions and residents. For each impact item, assess whether it represents a positive, negative, or neutral change. "
                "Use objective criteria based on public health outcomes, fiscal sustainability, and community wellbeing."
            )

            analysis_prompt = f"""Analyze this legislative text with special focus on public health, local government impacts, and financial implications. 
For each impact item, include an 'impact_type' field that must be exactly one of: 'positive', 'negative', or 'neutral'.
Base these assessments on objective criteria such as:
- Public health outcomes and accessibility
- Fiscal sustainability
- Community wellbeing
- Economic stability
- Implementation feasibility

Legislative Text:
{text}

Provide a detailed analysis in JSON format with the following structure:
{{
    "summary": "Brief overview of the legislation",
    "key_points": [
        {{
            "point": "Description of key point",
            "impact_type": "positive|negative|neutral"
        }}
    ],
    "public_health_impacts": {{
        "direct_effects": [
            {{
                "effect": "Description of health system impact",
                "impact_type": "positive|negative|neutral"
            }}
        ],
        "indirect_effects": [
            {{
                "effect": "Description of secondary health impact",
                "impact_type": "positive|negative|neutral"
            }}
        ],
        "funding_impact": [
            {{
                "impact": "Description of funding impact",
                "impact_type": "positive|negative|neutral"
            }}
        ],
        "vulnerable_populations": [
            {{
                "impact": "Description of population impact",
                "impact_type": "positive|negative|neutral"
            }}
        ]
    }},
    "public_health_official_actions": {{
        "immediate_considerations": [
            {{
                "consideration": "Description of immediate action needed",
                "priority": "high|medium|low",
                "impact_type": "positive|negative|neutral"
            }}
        ],
        "recommended_actions": [
            {{
                "action": "Description of recommended action",
                "timeline": "immediate|short_term|long_term",
                "impact_type": "positive|negative|neutral"
            }}
        ],
        "resource_needs": [
            {{
                "need": "Description of resource requirement",
                "urgency": "critical|important|planned",
                "impact_type": "positive|negative|neutral"
            }}
        ],
        "stakeholder_engagement": [
            {{
                "stakeholder": "Description of stakeholder engagement",
                "importance": "essential|recommended|optional",
                "impact_type": "positive|negative|neutral"
            }}
        ]
    }},
    "overall_assessment": {{
        "public_health": "positive|negative|neutral",
        "local_government": "positive|negative|neutral",
        "resident_financial": "positive|negative|neutral"
    }}
}}"""

            logger.info(f"Sending analysis request to OpenAI for bill {bill_number}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,
                max_completion_tokens=6000,
                response_format={"type": "json_object"}
            )
            logger.info(f"Received OpenAI response for bill {bill_number}")

            if not hasattr(response, "choices") or len(response.choices) == 0:
                logger.error(f"Bill {bill_number}: OpenAI API response contained no choices.")
                return False

            content = response.choices[0].message.content
            if not content:
                logger.error(f"Bill {bill_number}: OpenAI API returned empty content.")
                return False

            try:
                analysis = json.loads(content)
                logger.info(f"Successfully parsed analysis JSON for bill {bill_number}")

                # Perform second pass to determine impact levels
                logger.info(f"Starting impact level determination for bill {bill_number}")
                if not self.determine_impact_levels(analysis, bill_number, db_session):
                    logger.error(f"Failed to determine impact levels for bill {bill_number}")
                    return False
                logger.info(f"Successfully determined impact levels for bill {bill_number}")

                bill = db_session.query(LegislationTracker).filter(
                    LegislationTracker.bill_number == bill_number
                ).first()

                if bill:
                    bill.analysis = analysis
                    bill.last_updated = datetime.now()
                    logger.info(f"Updated analysis for bill {bill_number}")
                else:
                    logger.warning(f"No bill found with number {bill_number} to update analysis")
                    return False

                db_session.commit()
                logger.info(f"Successfully completed full analysis process for bill {bill_number}")
                return True

            except Exception as db_error:
                logger.error(f"Database error saving analysis for bill {bill_number}: {db_error}")
                db_session.rollback()
                return False

        except Exception as e:
            logger.error(f"Error analyzing legislation for bill {bill_number}: {e}")
            return False

    def get_stored_analysis(self, bill_number: str, db_session) -> Dict:
        """Retrieve stored analysis for a bill"""
        try:
            bill = db_session.query(LegislationTracker).filter_by(bill_number=bill_number).first()
            if bill and bill.analysis:
                return bill.analysis
            return {}
        except Exception as e:
            logger.error(f"Error retrieving analysis: {e}")
            return {}

    def generate_analysis_report(self, analysis: dict, bill: dict) -> str:
        """Generate an HTML report from the analysis"""
        try:
            html = f"""
            <html>
            <head>
                <title>Legislative Analysis Report - {bill.get('number', 'Unknown')}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h1, h2, h3, h4 {{ color: #2c3e50; }}
                    .impact-section {{ background: #f7f9fc; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                    .citation {{ border-left: 3px solid #3498db; padding-left: 15px; margin: 10px 0; }}
                    .action-item {{
                        background-color: #f8f9fa;
                        padding: 10px;
                        border-radius: 5px;
                        margin: 5px 0;
                    }}
                    .priority-high {{ border-left: 4px solid #dc3545; }}
                    .priority-medium {{ border-left: 4px solid #ffc107; }}
                    .priority-low {{ border-left: 4px solid #28a745; }}
                    .timeline-immediate {{ border-left: 4px solid #dc3545; }}
                    .timeline-short_term {{ border-left: 4px solid #ffc107; }}
                    .timeline-long_term {{ border-left: 4px solid #28a745; }}
                    .urgency-critical {{ border-left: 4px solid #dc3545; }}
                    .urgency-important {{ border-left: 4px solid #ffc107; }}
                    .urgency-planned {{ border-left: 4px solid #28a745; }}
                    .importance-essential {{ border-left: 4px solid #dc3545; }}
                    .importance-recommended {{ border-left: 4px solid #ffc107; }}
                    .importance-optional {{ border-left: 4px solid #28a745; }}
                </style>
            </head>
            <body>
                <h1>Legislative Analysis Report</h1>
                <h2>Bill {bill.get('number', 'Unknown')}: {bill.get('title', 'Unknown Title')}</h2>
                <div class="metadata">
                    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Congress:</strong> {bill.get('congress', 'Unknown')}</p>
                    <p><strong>Type:</strong> {bill.get('type', 'Unknown')}</p>
                </div>
                <h2>Executive Summary</h2>
                <p>{analysis.get('summary', 'No summary available')}</p>
                <h2>Key Points</h2>
                <ul>
                    {''.join([
                        f'<li class="action-item">{point.get("point", point) if isinstance(point, dict) else point}</li>'
                        for point in analysis.get('key_points', [])
                    ])}
                </ul>
                <h2>Impact Analysis</h2>
                <div class="impact-section">
                    <h3>Public Health Impacts</h3>
                    <h4>Direct Effects</h4>
                    <ul>{''.join([
                        f'<li class="action-item">{effect.get("effect", effect) if isinstance(effect, dict) else effect}</li>'
                        for effect in analysis.get('public_health_impacts', {}).get('direct_effects', [])
                    ])}</ul>
                    <h4>Indirect Effects</h4>
                    <ul>{''.join([
                        f'<li class="action-item">{effect.get("effect", effect) if isinstance(effect, dict) else effect}</li>'
                        for effect in analysis.get('public_health_impacts', {}).get('indirect_effects', [])
                    ])}</ul>
                    <h4>Funding Impact</h4>
                    <ul>{''.join([
                        f'<li class="action-item">{impact.get("impact", impact) if isinstance(impact, dict) else impact}</li>'
                        for impact in analysis.get('public_health_impacts', {}).get('funding_impact', [])
                    ])}</ul>
                    <h4>Vulnerable Populations</h4>
                    <ul>{''.join([
                        f'<li class="action-item">{impact.get("impact", impact) if isinstance(impact, dict) else impact}</li>'
                        for impact in analysis.get('public_health_impacts', {}).get('vulnerable_populations', [])
                    ])}</ul>
                </div>

                <div class="impact-section">
                    <h3>Public Health Official Actions</h3>

                    <h4>Immediate Considerations</h4>
                    {''.join([
                        f'''
                        <div class="action-item priority-{item.get('priority', 'medium')}">
                            <strong>Priority:</strong> {item.get('priority', 'medium').title()}<br>
                            {item.get('consideration', '')}
                        </div>
                        '''
                        for item in analysis.get('public_health_official_actions', {}).get('immediate_considerations', [])
                    ])}

                    <h4>Recommended Actions</h4>
                    {''.join([
                        f'''
                        <div class="action-item timeline-{item.get('timeline', 'short_term')}">
                            <strong>Timeline:</strong> {item.get('timeline', '').replace('_', ' ').title()}<br>
                            {item.get('action', '')}
                        </div>
                        '''
                        for item in analysis.get('public_health_official_actions', {}).get('recommended_actions', [])
                    ])}

                    <h4>Resource Needs</h4>
                    {''.join([
                        f'''
                        <div class="action-item urgency-{item.get('urgency', 'important')}">
                            <strong>Urgency:</strong> {item.get('urgency', '').title()}<br>
                            {item.get('need', '')}
                        </div>
                        '''
                        for item in analysis.get('public_health_official_actions', {}).get('resource_needs', [])
                    ])}

                    <h4>Stakeholder Engagement</h4>
                    {''.join([
                        f'''
                        <div class="action-item importance-{item.get('importance', 'recommended')}">
                            <strong>Importance:</strong> {item.get('importance', '').title()}<br>
                            {item.get('stakeholder', '')}
                        </div>
                        '''
                        for item in analysis.get('public_health_official_actions', {}).get('stakeholder_engagement', [])
                    ])}
                </div>

                <h2>Overall Assessment</h2>
                <div class="impact-section">
                    <p><strong>Public Health:</strong> {analysis.get('overall_assessment', {}).get('public_health', 'Not assessed')}</p>
                    <p><strong>Local Government:</strong> {analysis.get('overall_assessment', {}).get('local_government', 'Not assessed')}</p>
                    <p><strong>Resident Financial:</strong> {analysis.get('overall_assessment', {}).get('resident_financial', 'Not assessed')}</p>
                </div>
            </body>
            </html>
            """
            return html
        except Exception as e:
            logger.error(f"Error generating analysis report: {e}")
            return f"<html><body><h1>Error Generating Report</h1><p>{str(e)}</p></body></html>"

    def analyze_multiple_bills(self, bills: list, db_session) -> dict:
        """Analyze relationships between multiple bills using their stored analyses"""
        try:
            if not bills:
                return {}
            bill_analyses = []
            for bill in bills:
                analysis = self.get_stored_analysis(bill['number'], db_session)
                if analysis:
                    bill_analyses.append({
                        'number': bill['number'],
                        'title': bill.get('title', ''),
                        'analysis': analysis
                    })
            if not bill_analyses:
                return {}
            combined_text = "\n\n".join([
                f"Bill {bill['number']}: {bill['title']}\n{bill.get('summary', '')}"
                for bill in bill_analyses
            ])
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in legislative analysis and policy integration."
                    },
                    {
                        "role": "user",
                        "content": (
                            "Analyze these related bills and identify common themes and collective impacts:\n\n"
                            f"{combined_text}\n\n"
                            "Provide analysis in JSON format:\n"
                            "{\n"
                            '    "common_themes": ["List of shared themes across bills"],\n'
                            '    "collective_impacts": {\n'
                            '        "public_health": ["Combined public health effects"],\n'
                            '        "local_government": ["Aggregate effects on local governance"],\n'
                            '        "resource_requirements": ["Combined resource needs"]\n'
                            "    },\n"
                            '    "interactions": ["How these bills might interact/conflict"],\n'
                            '    "implementation_considerations": ["Collective implementation challenges"]\n'
                            "}"
                        )
                    }
                ],
                temperature=0.3,
                max_completion_tokens=4000,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            if content is not None:
                return json.loads(content)
            else:
                logger.error("Received None from OpenAI response content")
                return {}
        except Exception as e:
            logger.error(f"Error analyzing multiple bills: {e}")
            return {}
