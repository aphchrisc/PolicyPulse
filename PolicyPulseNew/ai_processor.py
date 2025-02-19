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
from typing import Dict, Optional, List
from openai import OpenAI
from models import LegislationTracker

# Set up module-level logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class AIProcessor:
    def __init__(self):
        """Initialize the AI processor with an OpenAI client"""
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API key not found in environment variables")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4"

    def analyze_legislation(self, text: str, bill_number: str, db_session, law_number: Optional[str] = None) -> bool:
        """
        Perform detailed analysis of bill text with focus on public health and local government impacts.
        Stores results in database using both bill_number and law_number if available.
        """
        try:
            if not self.api_key:
                logger.error("OpenAI API key not configured")
                return False

            logger.info(f"Starting AI analysis for bill {bill_number} {f'(Law {law_number})' if law_number else ''}")
            max_length = 40000
            if len(text) > max_length:
                text = text[:max_length] + "..."
                logger.info(f"Truncated text to {max_length} characters")

            # Get the analysis from OpenAI
            response = self._get_openai_analysis(text)
            if not response:
                return False

            # Store the analysis in the database
            bill = db_session.query(LegislationTracker).filter_by(bill_number=bill_number).first()
            if not bill and law_number:
                bill = db_session.query(LegislationTracker).filter_by(law_number=law_number).first()

            if bill:
                bill.analysis = response
                bill.last_updated = datetime.now()
                if law_number and not bill.law_number:
                    bill.law_number = law_number
                db_session.commit()
                logger.info(f"Stored analysis for bill {bill_number} {f'(Law {law_number})' if law_number else ''}")
                return True
            else:
                logger.warning(f"No record found for bill {bill_number} {f'(Law {law_number})' if law_number else ''}")
                return False

        except Exception as e:
            logger.error(f"Error analyzing legislation: {e}")
            return False

    def get_stored_analysis(self, bill_number: str, db_session, law_number: Optional[str] = None) -> Dict:
        """Retrieve stored analysis for a bill or law"""
        try:
            bill = db_session.query(LegislationTracker).filter_by(bill_number=bill_number).first()
            if not bill and law_number:
                bill = db_session.query(LegislationTracker).filter_by(law_number=law_number).first()

            if bill and bill.analysis:
                return bill.analysis
            return {}
        except Exception as e:
            logger.error(f"Error retrieving analysis: {e}")
            return {}

    def determine_impact_levels(self, analysis: dict, bill_number: str, db_session, law_number: Optional[str] = None) -> bool:
        """Determine impact levels for public health and local government officials."""
        try:
            # Get OpenAI to analyze impact levels
            impact_response = self._get_openai_impact_analysis(analysis)
            if not impact_response:
                return False

            # Update the database with impact levels
            bill = db_session.query(LegislationTracker).filter_by(bill_number=bill_number).first()
            if not bill and law_number:
                bill = db_session.query(LegislationTracker).filter_by(law_number=law_number).first()

            if bill:
                bill.public_health_impact = impact_response.get('public_health_impact_level', 'unknown')
                bill.local_gov_impact = impact_response.get('local_gov_impact_level', 'unknown')
                bill.public_health_reasoning = impact_response.get('public_health_reasoning')
                bill.local_gov_reasoning = impact_response.get('local_gov_reasoning')
                bill.last_updated = datetime.now()
                db_session.commit()
                return True
            else:
                logger.warning(f"No record found for bill {bill_number} {f'(Law {law_number})' if law_number else ''}")
                return False

        except Exception as e:
            logger.error(f"Error determining impact levels: {e}")
            return False

    def generate_analysis_report(self, analysis: dict, bill: dict) -> str:
        """Generate an HTML report from the analysis"""
        try:
            # Build the HTML template with proper escaping and string formatting
            html_template = """
            <html>
            <head>
                <title>Legislative Analysis Report - {bill_number}</title>
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
                </style>
            </head>
            <body>
                <h1>Legislative Analysis Report</h1>
                <h2>Bill {bill_number}: {bill_title}</h2>

                <div class="metadata">
                    <p><strong>Generated:</strong> {generated_date}</p>
                    <p><strong>Congress:</strong> {congress}</p>
                    <p><strong>Type:</strong> {bill_type}</p>
                    {law_number_html}
                </div>

                <h2>Executive Summary</h2>
                <p>{summary}</p>

                <h2>Key Points</h2>
                <div class="impact-section">
                    {key_points}
                </div>

                <h2>Public Health Impacts</h2>
                <div class="impact-section">
                    <h3>Direct Effects</h3>
                    {direct_effects}

                    <h3>Indirect Effects</h3>
                    {indirect_effects}

                    <h3>Funding Impact</h3>
                    {funding_impact}

                    <h3>Vulnerable Populations</h3>
                    {vulnerable_populations}
                </div>

                <h2>Public Health Official Actions</h2>
                <div class="impact-section">
                    <h3>Immediate Considerations</h3>
                    {immediate_considerations}

                    <h3>Recommended Actions</h3>
                    {recommended_actions}

                    <h3>Resource Needs</h3>
                    {resource_needs}

                    <h3>Stakeholder Engagement</h3>
                    {stakeholder_engagement}
                </div>

                <h2>Overall Assessment</h2>
                <div class="impact-section">
                    <p><strong>Public Health Impact:</strong> {public_health_impact}</p>
                    <p><strong>Local Government Impact:</strong> {local_gov_impact}</p>
                </div>
            </body>
            </html>
            """

            # Helper function to generate action items
            def generate_action_items(items, template):
                return ''.join(template.format(**item) if isinstance(item, dict) else template.format(item=item)
                             for item in items)

            # Format all the components
            key_points = generate_action_items(
                analysis.get('key_points', []),
                '<div class="action-item"><strong>{point}</strong></div>' if isinstance(item, dict) else
                '<div class="action-item"><strong>{item}</strong></div>'
            )

            direct_effects = generate_action_items(
                analysis.get('public_health_impacts', {}).get('direct_effects', []),
                '<div class="action-item">{effect}</div>'
            )

            indirect_effects = generate_action_items(
                analysis.get('public_health_impacts', {}).get('indirect_effects', []),
                '<div class="action-item">{effect}</div>'
            )

            funding_impact = generate_action_items(
                analysis.get('public_health_impacts', {}).get('funding_impact', []),
                '<div class="action-item">{impact}</div>'
            )

            vulnerable_populations = generate_action_items(
                analysis.get('public_health_impacts', {}).get('vulnerable_populations', []),
                '<div class="action-item">{impact}</div>'
            )

            immediate_considerations = generate_action_items(
                analysis.get('public_health_official_actions', {}).get('immediate_considerations', []),
                '<div class="action-item priority-{priority}"><strong>Priority:</strong> {priority}<br>{consideration}</div>'
            )

            recommended_actions = generate_action_items(
                analysis.get('public_health_official_actions', {}).get('recommended_actions', []),
                '<div class="action-item timeline-{timeline}"><strong>Timeline:</strong> {timeline}<br>{action}</div>'
            )

            resource_needs = generate_action_items(
                analysis.get('public_health_official_actions', {}).get('resource_needs', []),
                '<div class="action-item"><strong>Urgency:</strong> {urgency}<br>{need}</div>'
            )

            stakeholder_engagement = generate_action_items(
                analysis.get('public_health_official_actions', {}).get('stakeholder_engagement', []),
                '<div class="action-item"><strong>Importance:</strong> {importance}<br>{stakeholder}</div>'
            )

            # Format the complete HTML
            html = html_template.format(
                bill_number=bill.get('number', 'Unknown'),
                bill_title=bill.get('title', 'Unknown Title'),
                generated_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                congress=bill.get('congress', 'Unknown'),
                bill_type=bill.get('type', 'Unknown'),
                law_number_html=f'<p><strong>Law Number:</strong> {bill.get("law_number", "Unknown")}</p>' if bill.get('law_number') else '',
                summary=analysis.get('summary', 'No summary available'),
                key_points=key_points,
                direct_effects=direct_effects,
                indirect_effects=indirect_effects,
                funding_impact=funding_impact,
                vulnerable_populations=vulnerable_populations,
                immediate_considerations=immediate_considerations,
                recommended_actions=recommended_actions,
                resource_needs=resource_needs,
                stakeholder_engagement=stakeholder_engagement,
                public_health_impact=analysis.get('overall_assessment', {}).get('public_health', 'Not assessed'),
                local_gov_impact=analysis.get('overall_assessment', {}).get('local_government', 'Not assessed')
            )

            return html
        except Exception as e:
            logger.error(f"Error generating analysis report: {e}")
            return f"<html><body><h1>Error Generating Report</h1><p>{str(e)}</p></body></html>"

    def analyze_multiple_bills(self, bills: List[dict], db_session) -> dict:
        """Analyze relationships between multiple bills using their stored analyses"""
        try:
            if not bills:
                return {}

            # Collect analyses for all bills
            bill_analyses = []
            for bill in bills:
                analysis = self.get_stored_analysis(
                    bill_number=str(bill.get('number')),
                    law_number=str(bill.get('law_number')) if bill.get('law_number') else None,
                    db_session=db_session
                )
                if analysis:
                    bill_analyses.append({
                        'number': bill.get('number'),
                        'title': bill.get('title', ''),
                        'analysis': analysis
                    })

            if not bill_analyses:
                return {}

            # Prepare the comparative analysis prompt
            combined_text = "\n\n".join([
                f"Bill {bill['number']}: {bill['title']}\n{json.dumps(bill['analysis'].get('summary', ''))}"
                for bill in bill_analyses
            ])

            # Get comparative analysis from OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in legislative analysis and policy integration."
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze these related bills and identify common themes and collective impacts:

{combined_text}

Provide analysis in JSON format:
{{
    "common_themes": ["List of shared themes across bills"],
    "collective_impacts": {{
        "public_health": ["Combined public health effects"],
        "local_government": ["Aggregate effects on local governance"]
    }},
    "interactions": ["How these bills might interact/conflict"],
    "implementation_considerations": ["Collective implementation challenges"]
}}"""
                    }
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            if response.choices and response.choices[0].message.content:
                return json.loads(response.choices[0].message.content)
            return {}

        except Exception as e:
            logger.error(f"Error analyzing multiple bills: {e}")
            return {}

    def _get_openai_analysis(self, text: str) -> Optional[Dict]:
        """Get analysis from OpenAI"""
        try:
            system_prompt = """You are an expert legislative analyst specializing in public health policy and local government impact assessment. 
            Analyze bills to identify specific impacts on public health systems, local government operations, and financial implications."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self._get_analysis_prompt(text)}
                ],
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )

            if response.choices and response.choices[0].message.content:
                return json.loads(response.choices[0].message.content)
            return None

        except Exception as e:
            logger.error(f"Error getting OpenAI analysis: {e}")
            return None

    def _get_openai_impact_analysis(self, analysis: Dict) -> Optional[Dict]:
        """Get impact analysis from OpenAI"""
        try:
            system_prompt = """You are an expert in determining the urgency and importance of bills for public health and local government officials."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self._get_impact_prompt(analysis)}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            if response.choices and response.choices[0].message.content:
                return json.loads(response.choices[0].message.content)
            return None

        except Exception as e:
            logger.error(f"Error getting OpenAI impact analysis: {e}")
            return None

    def _get_analysis_prompt(self, text: str) -> str:
        """Get the analysis prompt template"""
        return """Analyze this legislative text with special focus on public health and local government impacts.
        Provide a JSON response with the following structure:
        {
            "summary": "Brief overview",
            "key_points": [
                {"point": "Key point", "impact_type": "positive|negative|neutral"}
            ],
            "public_health_impacts": {
                "direct_effects": [
                    {"effect": "Effect description", "impact_type": "positive|negative|neutral"}
                ],
                "indirect_effects": [
                    {"effect": "Effect description", "impact_type": "positive|negative|neutral"}
                ],
                "funding_impact": [
                    {"impact": "Description", "impact_type": "positive|negative|neutral"}
                ],
                "vulnerable_populations": [
                    {"impact": "Description", "impact_type": "positive|negative|neutral"}
                ]
            },
            "public_health_official_actions": {
                "immediate_considerations": [
                    {"consideration": "Action description", "priority": "high|medium|low", "impact_type": "positive|negative|neutral"}
                ],
                "recommended_actions": [
                    {"action": "Description", "timeline": "immediate|short_term|long_term", "impact_type": "positive|negative|neutral"}
                ],
                "resource_needs": [
                    {"need": "Description", "urgency": "critical|important|planned", "impact_type": "positive|negative|neutral"}
                ],
                "stakeholder_engagement": [
                    {"stakeholder": "Description", "importance": "essential|recommended|optional", "impact_type": "positive|negative|neutral"}
                ]
            },
            "overall_assessment": {
                "public_health": "positive|negative|neutral",
                "local_government": "positive|negative|neutral"
            }
        }

        Legislative Text:
        """ + text

    def _get_impact_prompt(self, analysis: Dict) -> str:
        """Get the impact analysis prompt template"""
        return f"""Based on this legislative analysis, determine the impact level for both public health officials
        and local government officials. Return a JSON object with exactly this structure:
        {{
            "public_health_impact_level": "high|medium|low",
            "public_health_reasoning": "Brief explanation",
            "local_gov_impact_level": "high|medium|low",
            "local_gov_reasoning": "Brief explanation"
        }}

        Analysis to evaluate:
        {json.dumps(analysis, indent=2)}
        """