"""
File: main.py

Main Streamlit application for the Congress Legislation Monitor. This version includes:
  - A minimal sidebar with only search functionality.
  - Four main tabs:
      1. Latest Legislation – shows either a list of bills (filtered by search if applicable)
         or, if a user clicks "View Details", displays the full detailed view for that bill.
      2. Search History – displays recent searches.
      3. Analysis Dashboard – includes a sample trend chart.
      4. Database Maintenance – options for flushing the database, performing a full refresh
         (renewing from Jan 1, 2025), and manual update.

Each function includes detailed documentation and inline explanations.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import logging
import base64

from ai_processor import AIProcessor
from congress_api import CongressAPI
from alert_system import AlertSystem
from data_store import DataStore
from utils import load_custom_css

# Set up application-level logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_session_state():
    """
    Initialize required session state variables.
    These include objects for database access, current bill data, search results, etc.
    """
    if 'data_store' not in st.session_state:
        st.session_state.data_store = DataStore()
    if 'user_email' not in st.session_state:
        st.session_state.user_email = "default@user.com"
    if 'current_analysis' not in st.session_state:
        st.session_state.current_analysis = None
    if 'current_bill_text' not in st.session_state:
        st.session_state.current_bill_text = None
    if 'current_bill_info' not in st.session_state:
        st.session_state.current_bill_info = None
    if 'bills' not in st.session_state:
        st.session_state.bills = []
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ""
    if 'show_raw' not in st.session_state:
        st.session_state.show_raw = False

def view_bill_details(bill):
    """
    Save the selected bill into session state to trigger the detailed view.

    Args:
        bill (dict): Bill information.

    Returns:
        dict: The same bill dictionary.
    """
    st.session_state.current_bill_info = bill
    return bill

def analyze_bill(congress_api, ai_processor, bill):
    """
    Fetch the full text (or fallback to summary) for a bill and run AI analysis.

    Args:
        congress_api (CongressAPI): For fetching bill text.
        ai_processor (AIProcessor): For performing AI analysis.
        bill (dict): Bill data.

    Returns:
        bool: True if analysis succeeds; otherwise False.
    """
    try:
        bill_text = congress_api.get_bill_text(
            bill['congress'],
            bill['type'],
            bill['number']
        )
        if not bill_text and bill.get('summary'):
            st.warning("Full bill text not available; falling back to summary for analysis.")
            bill_text = bill.get('summary')
        if bill_text:
            db_session = st.session_state.data_store.db_session
            success = ai_processor.analyze_legislation(
                text=bill_text,
                bill_number=str(bill['number']),
                db_session=db_session
            )
            if success:
                analysis = ai_processor.get_stored_analysis(
                    bill_number=str(bill['number']),
                    db_session=db_session
                )
                st.session_state.current_analysis = analysis
                st.session_state.current_bill_text = bill_text
                st.session_state.current_bill_info = bill
                return True
            else:
                st.error("Failed to analyze bill.")
                return False
        else:
            st.error("Bill text not available for analysis.")
            return False
    except Exception as e:
        logger.error(f"Error analyzing bill {bill.get('number', 'unknown')}: {e}")
        return False

def display_detailed_bill(bill, ai_processor):
    """
    Display the detailed view for a single bill.
    This view includes:
      - Basic bill information
      - The stored AI analysis (if available)
      - Download links for the analysis and full bill text
      - Buttons to trigger re-analysis or toggle raw details.

    Args:
        bill (dict): Bill details.
        ai_processor (AIProcessor): For generating quick summary if needed.
    """
    st.title(f"Bill {bill['number']}")
    st.header(bill['title'])
    st.markdown("---")

    # Display a card with basic bill information.
    st.markdown("""
        <style>
        .bill-info-card {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="bill-info-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Basic Information")
            st.write(f"**Congress:** {bill.get('congress', 'N/A')}")
            st.write(f"**Type:** {bill.get('type', 'N/A')}")
            st.write(f"**Introduced Date:** {bill.get('introduced_date', 'N/A')}")
            st.write("**Sponsors:**", ", ".join(bill.get('sponsors', [])))
        with col2:
            st.markdown("### Current Status")
            st.write(f"**Latest Action Date:** {bill.get('last_action_date', 'N/A')}")
            st.write(f"**Latest Action:** {bill.get('last_action_text', '')}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Attempt to load stored AI analysis from the database.
    stored_analysis = None
    try:
        stored_analysis = st.session_state.data_store.get_stored_analysis(str(bill['number']))
        if stored_analysis:
            st.session_state.current_analysis = stored_analysis
            st.session_state.current_bill_info = bill
            display_analysis()  # This function will render the AI analysis results.
    except Exception as e:
        logger.error(f"Error retrieving analysis from database: {e}")

    # Provide download links for the analysis (HTML) and bill text.
    st.markdown("### Downloads")
    col1, col2 = st.columns(2)
    with col1:
        if stored_analysis:
            analysis_html = get_analysis_html(bill, stored_analysis)
            download_link = generate_download_link(
                analysis_html,
                f"bill_{bill['number']}_analysis.html",
                "Download Analysis (HTML)"
            )
            st.markdown(download_link, unsafe_allow_html=True)
    with col2:
        if bill.get('bill_text'):
            download_link = generate_download_link(
                bill['bill_text'],
                f"bill_{bill['number']}.txt",
                "Download Bill Text"
            )
            st.markdown(download_link, unsafe_allow_html=True)

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        button_text = "Re-Analyze Bill" if stored_analysis else "Analyze Bill"
        if st.button(button_text, key=f"analyze_{bill['number']}", use_container_width=True):
            if analyze_bill(st.session_state.congress_api, ai_processor, bill):
                st.success("Analysis complete!")
                st.rerun()
            else:
                st.error("Failed to analyze bill")
    with col2:
        if st.button("View Raw Details", key=f"raw_{bill['number']}", use_container_width=True):
            st.session_state.show_raw = not st.session_state.get('show_raw', False)
    st.markdown("---")
    if bill.get('bill_text'):
        st.header("Full Bill Text")
        with st.expander("Show Full Text", expanded=False):
            st.text_area("", bill.get('bill_text', ''), height=400)
    if st.session_state.get('show_raw', False):
        st.header("Raw Bill Details")
        with st.expander("Show Raw Details", expanded=True):
            st.json(bill.get('raw_response', {}))

def display_analysis():
    """
    Render the stored AI analysis results, including executive summary,
    key points, and various impact sections.
    """
    if not st.session_state.current_analysis:
        st.info("No analysis available for this bill yet.")
        return
    analysis = st.session_state.current_analysis
    bill = st.session_state.current_bill_info

    st.write("## AI Analysis Results")

    # Executive Summary Section
    st.write("### Executive Summary")
    st.write(analysis.get('summary', 'No executive summary available.'))

    # Key Points Section with Enhanced Formatting
    st.write("### Key Points")
    key_points = analysis.get('key_points', [])
    if key_points:
        for point in key_points:
            impact_color = get_impact_color(point.get('impact_type', 'neutral'))
            st.markdown(
                f"""<div style="background-color: {impact_color}; padding: 10px; 
                border-radius: 5px; margin: 5px 0;">
                {point.get('point', '')}</div>""",
                unsafe_allow_html=True
            )
    else:
        st.write("No key points available.")

    # Public Health Impacts Section
    st.write("### Public Health Impact Analysis")

    ph_impacts = analysis.get('public_health_impacts', {})

    col1, col2 = st.columns(2)

    with col1:
        st.write("#### Direct Effects")
        for effect in ph_impacts.get('direct_effects', []):
            impact_color = get_impact_color(effect.get('impact_type', 'neutral'))
            st.markdown(
                f"""<div style="background-color: {impact_color}; padding: 10px; 
                border-radius: 5px; margin: 5px 0;">
                {effect.get('effect', '')}</div>""",
                unsafe_allow_html=True
            )

    with col2:
        st.write("#### Indirect Effects")
        for effect in ph_impacts.get('indirect_effects', []):
            impact_color = get_impact_color(effect.get('impact_type', 'neutral'))
            st.markdown(
                f"""<div style="background-color: {impact_color}; padding: 10px; 
                border-radius: 5px; margin: 5px 0;">
                {effect.get('effect', '')}</div>""",
                unsafe_allow_html=True
            )

    st.write("#### Funding Impact")
    for impact in ph_impacts.get('funding_impact', []):
        impact_color = get_impact_color(impact.get('impact_type', 'neutral'))
        st.markdown(
            f"""<div style="background-color: {impact_color}; padding: 10px; 
            border-radius: 5px; margin: 5px 0;">
            {impact.get('impact', '')}</div>""",
            unsafe_allow_html=True
        )

    st.write("#### Impact on Vulnerable Populations")
    for impact in ph_impacts.get('vulnerable_populations', []):
        impact_color = get_impact_color(impact.get('impact_type', 'neutral'))
        st.markdown(
            f"""<div style="background-color: {impact_color}; padding: 10px; 
            border-radius: 5px; margin: 5px 0;">
            {impact.get('impact', '')}</div>""",
            unsafe_allow_html=True
        )

    # Public Health Official Actions Section
    st.write("### Public Health Official Actions")
    ph_actions = analysis.get('public_health_official_actions', {})

    if ph_actions:
        tabs = st.tabs([
            "Immediate Considerations", 
            "Recommended Actions",
            "Resource Needs",
            "Stakeholder Engagement"
        ])

        with tabs[0]:
            for item in ph_actions.get('immediate_considerations', []):
                impact_color = get_impact_color(item.get('impact_type', 'neutral'))
                priority_badge = {
                    'high': '🔴', 
                    'medium': '🟡', 
                    'low': '🟢'
                }.get(item.get('priority', 'medium'), '⚪')

                st.markdown(
                    f"""<div style="background-color: {impact_color}; padding: 10px; 
                    border-radius: 5px; margin: 5px 0;">
                    {priority_badge} <strong>Priority:</strong> {item.get('priority', 'medium').title()}<br>
                    {item.get('consideration', '')}</div>""",
                    unsafe_allow_html=True
                )

        with tabs[1]:
            for item in ph_actions.get('recommended_actions', []):
                impact_color = get_impact_color(item.get('impact_type', 'neutral'))
                timeline_icon = {
                    'immediate': '⚡',
                    'short_term': '⏳',
                    'long_term': '📅'
                }.get(item.get('timeline', 'short_term'), '⏱️')

                st.markdown(
                    f"""<div style="background-color: {impact_color}; padding: 10px; 
                    border-radius: 5px; margin: 5px 0;">
                    {timeline_icon} <strong>Timeline:</strong> {item.get('timeline', '').replace('_', ' ').title()}<br>
                    {item.get('action', '')}</div>""",
                    unsafe_allow_html=True
                )

        with tabs[2]:
            for item in ph_actions.get('resource_needs', []):
                impact_color = get_impact_color(item.get('impact_type', 'neutral'))
                urgency_icon = {
                    'critical': '🚨',
                    'important': '⚠️',
                    'planned': '📋'
                }.get(item.get('urgency', 'important'), '📝')

                st.markdown(
                    f"""<div style="background-color: {impact_color}; padding: 10px; 
                    border-radius: 5px; margin: 5px 0;">
                    {urgency_icon} <strong>Urgency:</strong> {item.get('urgency', '').title()}<br>
                    {item.get('need', '')}</div>""",
                    unsafe_allow_html=True
                )

        with tabs[3]:
            for item in ph_actions.get('stakeholder_engagement', []):
                impact_color = get_impact_color(item.get('impact_type', 'neutral'))
                importance_icon = {
                    'essential': '⭐',
                    'recommended': '✨',
                    'optional': '📌'
                }.get(item.get('importance', 'recommended'), '📍')

                st.markdown(
                    f"""<div style="background-color: {impact_color}; padding: 10px; 
                    border-radius: 5px; margin: 5px 0;">
                    {importance_icon} <strong>Importance:</strong> {item.get('importance', '').title()}<br>
                    {item.get('stakeholder', '')}</div>""",
                    unsafe_allow_html=True
                )

    # Overall Assessment Section with Visual Indicators
    st.write("### Overall Assessment")
    overall = analysis.get('overall_assessment', {})
    if overall:
        st.markdown("""
            <style>
            .overall-assessment {
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
                font-weight: bold;
            }
            </style>
            """, unsafe_allow_html=True)

        for aspect, impact in overall.items():
            impact_color = get_impact_color(impact)
            icon = '✅' if impact == 'positive' else '❌' if impact == 'negative' else '⚠️'
            st.markdown(
                f"""<div class="overall-assessment" style="background-color: {impact_color};">
                {icon} <strong>{aspect.replace('_', ' ').title()}:</strong> {impact.title()}</div>""",
                unsafe_allow_html=True
            )

def get_impact_color(impact_type: str) -> str:
    """Return a hex color code based on the impact type."""
    colors = {
        'positive': '#dcfce7',  # Light green
        'negative': '#fecaca',  # Light red
        'neutral': '#e6f3ff'    # Light blue
    }
    return colors.get(impact_type.lower(), colors['neutral'])

def load_user_preferences():
    """
    Load user preferences from the database into session state.
    """
    try:
        prefs = st.session_state.data_store.get_user_preferences(st.session_state.user_email)
        st.session_state.user_keywords = prefs.get('keywords', [])
        logger.info(f"Loaded preferences for user: {st.session_state.user_email}")
    except Exception as e:
        logger.error(f"Error loading preferences: {e}")
        st.session_state.user_keywords = []

def display_bill_list(bills):
    """Display the bills list with impact level filtering"""
    # Add filter dropdowns
    col1, col2 = st.columns(2)
    with col1:
        ph_filter = st.selectbox(
            "Filter by Public Health Impact",
            ["All", "High", "Medium", "Low", "Unknown"],
            key="ph_filter"
        )
    with col2:
        lg_filter = st.selectbox(
            "Filter by Local Government Impact",
            ["All", "High", "Medium", "Low", "Unknown"],
            key="lg_filter"
        )

    # Apply filters
    filtered_bills = bills
    if ph_filter != "All":
        filtered_bills = [b for b in filtered_bills 
                        if b.get('public_health_impact', 'unknown').lower() == ph_filter.lower()]
    if lg_filter != "All":
        filtered_bills = [b for b in filtered_bills 
                        if b.get('local_gov_impact', 'unknown').lower() == lg_filter.lower()]

    if filtered_bills:
        st.write(f"Showing {len(filtered_bills)} bills")
        for bill in filtered_bills:
            display_bill(bill)
    else:
        st.info("No bills found matching the selected filters.")



def display_bill(bill):
    """Display a summary view of a bill with key fields and impact levels."""
    bill_header = f"#{bill['number']} ({bill.get('type', '').upper()}): {bill['title']}"
    with st.expander(bill_header, expanded=False):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"**Congress:** {bill.get('congress', 'N/A')}")
            if bill.get('introduced_date'):
                st.write(f"📅 **Introduced:** {bill['introduced_date']}")
        with col2:
            impact_level = bill.get('public_health_impact', 'unknown').lower()
            color = {
                'high': 'red',
                'medium': 'orange',
                'low': 'green',
                'unknown': 'gray'
            }.get(impact_level, 'gray')
            st.markdown(f"""
                <div style='padding: 10px; border-radius: 5px; text-align: center;
                background-color: {color}20; border: 1px solid {color}'>
                🏥 Public Health Impact:<br/>
                <strong>{impact_level.upper()}</strong>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            impact_level = bill.get('local_gov_impact', 'unknown').lower()
            color = {
                'high': 'red',
                'medium': 'orange',
                'low': 'green',
                'unknown': 'gray'
            }.get(impact_level, 'gray')
            st.markdown(f"""
                <div style='padding: 10px; border-radius: 5px; text-align: center;
                background-color: {color}20; border: 1px solid {color}'>
                🏛️ Local Gov Impact:<br/>
                <strong>{impact_level.upper()}</strong>
                </div>
            """, unsafe_allow_html=True)

        if bill.get('last_action_date') and bill.get('last_action_text'):
            st.write("📌 **Latest Action:**")
            st.write(f"*{bill['last_action_date']}*")
            st.write(bill['last_action_text'])

        # Display AI Analysis Summary if available
        try:
            if bill.get('analysis') and isinstance(bill['analysis'], dict):
                summary = bill['analysis'].get('summary')
                if summary:
                    st.write("---")
                    st.write("🤖 **AI Analysis Summary:**")
                    st.markdown(f"""
                        <div style='padding: 15px; border-radius: 5px; 
                        background-color: #f0f4f8; border-left: 4px solid #4299e1'>
                        {summary}
                        </div>
                    """, unsafe_allow_html=True)
        except Exception as e:
            logger.error(f"Error displaying AI summary: {e}")

        # Add Impact Summary section right after Latest Action
        try:
            # Get reasoning text directly from the bill data
            public_health_reasoning = bill.get('public_health_reasoning')
            local_gov_reasoning = bill.get('local_gov_reasoning')

            if public_health_reasoning or local_gov_reasoning:
                st.write("---")
                st.write("🎯 **Impact Summary:**")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                        <div style='padding: 15px; border-radius: 5px; 
                        background-color: #f0f4f8; border-left: 4px solid #4299e1'>
                        <strong>🏥 Public Health Assessment</strong><br/><br/>
                        {public_health_reasoning if public_health_reasoning else 'No assessment available'}
                        </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                        <div style='padding: 15px; border-radius: 5px;
                        background-color: #f0f4f8; border-left: 4px solid #4299e1'>
                        <strong>🏛️ Local Government Assessment</strong><br/><br/>
                        {local_gov_reasoning if local_gov_reasoning else 'No assessment available'}
                        </div>
                    """, unsafe_allow_html=True)

        except Exception as e:
            logger.error(f"Error displaying impact summary: {e}")

        if bill.get('sponsors'):
            st.write("---")
            st.write("👥 **Sponsors:**", ", ".join(bill['sponsors']))
        if bill.get('summary'):
            st.write("---")
            st.write("📖 **Summary:**")
            st.write(bill['summary'])
        st.write("---")

        # Changed from 4 columns to 3 columns, removing the Analyze Impact button
        status_col1, status_col2, button_col = st.columns([2, 2, 1])
        with status_col1:
            if bill.get('bill_text'):
                st.markdown("✅ **Full text available**")
            else:
                st.markdown("⚠️ **Full text not available**")
        with status_col2:
            if bill.get('analysis'):
                st.markdown("✅ **AI analysis available**")
            else:
                st.markdown("⚠️ **AI analysis not available**")
        with button_col:
            unique_key = f"view_{bill.get('congress', '')}_{bill.get('type', '')}_{bill['number']}"
            if st.button("View Details", key=unique_key, use_container_width=True):
                st.session_state.current_bill_info = bill
                st.rerun()

def generate_download_link(content: str, filename: str, button_text: str = "Download", button_class: str = "download-button") -> str:
    """
    Generate an HTML download link for the provided content.

    Args:
        content (str): Content to download.
        filename (str): File name for download.
        button_text (str): Text for the download button.
        button_class (str): CSS class for button styling.

    Returns:
        str: HTML anchor tag with the download link.
    """
    b64 = base64.b64encode(content.encode()).decode()
    return f'''
        <a href="data:text/html;base64,{b64}" 
           download="{filename}"
           style="text-decoration: none; width: 100%;">
            <button class="{button_class}">
                {button_text}
            </button>
        </a>
    '''

def get_analysis_html(bill: dict, analysis: dict) -> str:
    """
    Generate a comprehensive HTML document containing the full AI analysis.

    Args:
        bill (dict): Bill information
        analysis (dict): Analysis data

    Returns:
        str: Formatted HTML document
    """
    impact_colors = {
        'positive': '#dcfce7',
        'negative': '#fecaca',
        'neutral': '#e6f3ff'
    }

    html = f"""
    <html>
    <head>
        <title>Analysis of Bill {bill['number']}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 40px auto;
                padding: 20px;
            }}
            h1, h2, h3 {{
                color: #1a365d;
                margin-top: 30px;
            }}
            .impact-box {{
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
            }}
            .section {{
                margin: 30px 0;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
            }}
            .meta-info {{
                background: #f0f4f8;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .impact-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <h1>Analysis of Bill {bill['number']}</h1>

        <div class="meta-info">
            <h3>Bill Information</h3>
            <p><strong>Title:</strong> {bill['title']}</p>
            <p><strong>Congress:</strong> {bill.get('congress', 'N/A')}</p>
            <p><strong>Type:</strong> {bill.get('type', 'N/A').upper()}</p>
            <p><strong>Introduced:</strong> {bill.get('introduced_date', 'N/A')}</p>
            <p><strong>Sponsors:</strong> {', '.join(bill.get('sponsors', []))}</p>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <p>{analysis.get('summary', 'No executive summary available.')}</p>
        </div>

        <div class="section">
            <h2>Key Points</h2>
    """

    # Add Key Points - handle both string and dictionary formats
    key_points = analysis.get('key_points', [])
    if isinstance(key_points, list):
        for point in key_points:
            if isinstance(point, dict):
                impact_type = point.get('impact_type', 'neutral')
                point_text = point.get('point', '')
            else:
                impact_type = 'neutral'
                point_text = str(point)

            html += f"""
                <div class="impact-box" style="background-color: {impact_colors.get(impact_type, '#f8f9fa')}">
                    {point_text}
                </div>
            """
    elif isinstance(key_points, str):
        html += f"""
            <div class="impact-box" style="background-color: {impact_colors['neutral']}">
                {key_points}
            </div>
        """

    # Add Public Health Impacts
    ph_impacts = analysis.get('public_health_impacts', {})
    if ph_impacts:
        html += """
            <div class="section">
                <h2>Public Health Impact Analysis</h2>
                <div class="impact-grid">
        """

        # Direct Effects
        html += """
                    <div>
                        <h3>Direct Effects</h3>
        """
        direct_effects = ph_impacts.get('direct_effects', [])
        if isinstance(direct_effects, list):
            for effect in direct_effects:
                if isinstance(effect, dict):
                    impact_type = effect.get('impact_type', 'neutral')
                    effect_text = effect.get('effect', '')
                else:
                    impact_type = 'neutral'
                    effect_text = str(effect)

                html += f"""
                    <div class="impact-box" style="background-color: {impact_colors.get(impact_type, '#f8f9fa')}">
                        {effect_text}
                    </div>
                """
        elif isinstance(direct_effects, str):
            html += f"""
                <div class="impact-box" style="background-color: {impact_colors['neutral']}">
                    {direct_effects}
                </div            """

        # Indirect Effects
        html += """
                    </div></div>
                        <h3>Indirect Effects</h3>
        """
        indirect_effects= ph_impacts.get('indirect_effects', [])
        if isinstance(indirect_effects, list):
            for effect in indirect_effects:
                if isinstance(effect, dict):
                    impact_type = effect.get('impact_type', 'neutral')
                    effect_text = effect.get('effect', '')
                else:
                    impact_type = 'neutral'
                    effect_text= str(effect)

                html += f"""
                    <div class="impact-box" style="background-color: {impact_colors.get(impact_type, '#f8f9fa')}">
                        {effect_text}
                    </div>
                """
        elif isinstance(indirect_effects, str):
            html += f"""
                <div class="impact-box" style="background-color: {impact_colors['neutral']}">
                    {indirect_effects}
                </div>
            """

        html += """
                    </div>
                </div>
            </div>
        """

    # Overall Assessment
    overall = analysis.get('overall_assessment', {})
    if overall:
        html += """
            <div class="section">
                <h2>Overall Assessment</h2>
        """

        if isinstance(overall, dict):
            for aspect, impact in overall.items():
                impact_color = impact_colors.get(str(impact).lower(), '#f8f9fa')
                icon = '✅' if str(impact).lower() == 'positive' else '❌' if str(impact).lower() == 'negative' else '⚠️'
                html += f"""
                    <div class="impact-box" style="background-color: {impact_color}">
                        {icon} <strong>{str(aspect).replace('_', ' ').title()}:</strong> {str(impact).title()}
                    </div>
                """
        elif isinstance(overall, str):
            html += f"""
                <div class="impact-box" style="background-color: {impact_colors['neutral']}">
                    {overall}
                </div>
            """

        html += """
            </div>
        """

    html += f"""
        <div class="meta-info"><p><em>Analysis generated on {datetime.now().strftime("%B %d, %Y")}</em></p>
        </div>
    </body>
    </html>
    """

    return html

def load_user_preferences():
    """
    Load user preferences from the database into session state.
    """
    try:
        prefs = st.session_state.data_store.get_user_preferences(st.session_state.user_email)
        st.session_state.user_keywords = prefs.get('keywords', [])
        logger.info(f"Loaded preferences for user: {st.session_state.user_email}")
    except Exception as e:
        logger.error(f"Error loading preferences: {e}")
        st.session_state.user_keywords = []

def display_bill_list(bills):
    """Display the bills list with impact level filtering"""
    # Add filter dropdowns
    col1, col2 = st.columns(2)
    with col1:
        ph_filter = st.selectbox(
            "Filter by Public Health Impact",
            ["All", "High", "Medium", "Low", "Unknown"],
            key="ph_filter"
        )
    with col2:
        lg_filter = st.selectbox(
            "Filter by Local Government Impact",
            ["All", "High", "Medium", "Low", "Unknown"],
            key="lg_filter"
        )

    # Apply filters
    filtered_bills = bills
    if ph_filter != "All":
        filtered_bills = [b for b in filtered_bills 
                        if b.get('public_health_impact', 'unknown').lower() == ph_filter.lower()]
    if lg_filter != "All":
        filtered_bills = [b for b in filtered_bills 
                        if b.get('local_gov_impact', 'unknown').lower() == lg_filter.lower()]

    if filtered_bills:
        st.write(f"Showing {len(filtered_bills)} bills")
        for bill in filtered_bills:
            display_bill(bill)
    else:
        st.info("No bills found matching the selected filters.")



def display_bill(bill):
    """Display a summary view of a bill with key fields and impact levels."""
    bill_header = f"#{bill['number']} ({bill.get('type', '').upper()}): {bill['title']}"
    with st.expander(bill_header, expanded=False):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"**Congress:** {bill.get('congress', 'N/A')}")
            if bill.get('introduced_date'):
                st.write(f"📅 **Introduced:** {bill['introduced_date']}")
        with col2:
            impact_level = bill.get('public_health_impact', 'unknown').lower()
            color = {
                'high': 'red',
                'medium': 'orange',
                'low': 'green',
                'unknown': 'gray'
            }.get(impact_level, 'gray')
            st.markdown(f"""
                <div style='padding: 10px; border-radius: 5px; text-align: center;
                background-color: {color}20; border: 1px solid {color}'>
                🏥 Public Health Impact:<br/>
                <strong>{impact_level.upper()}</strong>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            impact_level = bill.get('local_gov_impact', 'unknown').lower()
            color = {
                'high': 'red',
                'medium': 'orange',
                'low': 'green',
                'unknown': 'gray'
            }.get(impact_level, 'gray')
            st.markdown(f"""
                <div style='padding: 10px; border-radius: 5px; text-align: center;
                background-color: {color}20; border: 1px solid {color}'>
                🏛️ Local Gov Impact:<br/>
                <strong>{impact_level.upper()}</strong>
                </div>
            """, unsafe_allow_html=True)

        if bill.get('last_action_date') and bill.get('last_action_text'):
            st.write("📌 **Latest Action:**")
            st.write(f"*{bill['last_action_date']}*")
            st.write(bill['last_action_text'])

        # Display AI Analysis Summary if available
        try:
            if bill.get('analysis') and isinstance(bill['analysis'], dict):
                summary = bill['analysis'].get('summary')
                if summary:
                    st.write("---")
                    st.write("🤖 **AI Analysis Summary:**")
                    st.markdown(f"""
                        <div style='padding: 15px; border-radius: 5px; 
                        background-color: #f0f4f8; border-left: 4px solid #4299e1'>
                        {summary}
                        </div>
                    """, unsafe_allow_html=True)
        except Exception as e:
            logger.error(f"Error displaying AI summary: {e}")

        # Add Impact Summary section right after Latest Action
        try:
            # Get reasoning text directly from the bill data
            public_health_reasoning = bill.get('public_health_reasoning')
            local_gov_reasoning = bill.get('local_gov_reasoning')

            if public_health_reasoning or local_gov_reasoning:
                st.write("---")
                st.write("🎯 **Impact Summary:**")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                        <div style='padding: 15px; border-radius: 5px; 
                        background-color: #f0f4f8; border-left: 4px solid #4299e1'>
                        <strong>🏥 Public Health Assessment</strong><br/><br/>
                        {public_health_reasoning if public_health_reasoning else 'No assessment available'}
                        </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                        <div style='padding: 15px; border-radius: 5px;
                        background-color: #f0f4f8; border-left: 4px solid #4299e1'>
                        <strong>🏛️ Local Government Assessment</strong><br/><br/>
                        {local_gov_reasoning if local_gov_reasoning else 'No assessment available'}
                        </div>
                    """, unsafe_allow_html=True)

        except Exception as e:
            logger.error(f"Error displaying impact summary: {e}")

        if bill.get('sponsors'):
            st.write("---")
            st.write("👥 **Sponsors:**", ", ".join(bill['sponsors']))
        if bill.get('summary'):
            st.write("---")
            st.write("📖 **Summary:**")
            st.write(bill['summary'])
        st.write("---")

        # Changed from 4 columns to 3 columns, removing the Analyze Impact button
        status_col1, status_col2, button_col = st.columns([2, 2, 1])
        with status_col1:
            if bill.get('bill_text'):
                st.markdown("✅ **Full text available**")
            else:
                st.markdown("⚠️ **Full text not available**")
        with status_col2:
            if bill.get('analysis'):
                st.markdown("✅ **AI analysis available**")
            else:
                st.markdown("⚠️ **AI analysis not available**")
        with button_col:
            unique_key = f"view_{bill.get('congress', '')}_{bill.get('type', '')}_{bill['number']}"
            if st.button("View Details", key=unique_key, use_container_width=True):
                st.session_state.current_bill_info = bill
                st.rerun()

def generate_download_link(content: str, filename: str, button_text: str = "Download", button_class: str = "download-button") -> str:
    """
    Generate an HTML download link for the provided content.

    Args:
        content (str): Content to download.
        filename (str): File name for download.
        button_text (str): Text for the download button.
        button_class (str): CSS class for button styling.

    Returns:
        str: HTML anchor tag with the download link.
    """
    b64 = base64.b64encode(content.encode()).decode()
    return f'''
        <a href="data:text/html;base64,{b64}" 
           download="{filename}"
           style="text-decoration: none; width: 100%;">
            <button class="{button_class}">
                {button_text}
            </button>
        </a>
    '''

def get_analysis_html(bill: dict, analysis: dict) -> str:
    """
    Generate a comprehensive HTML document containing the full AI analysis.

    Args:
        bill (dict): Bill information
        analysis (dict): Analysis data

    Returns:
        str: Formatted HTML document
    """
    impact_colors = {
        'positive': '#dcfce7',
        'negative': '#fecaca',
        'neutral': '#e6f3ff'
    }

    html = f"""
    <html>
    <head>
        <title>Analysis of Bill {bill['number']}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 40px auto;
                padding: 20px;
            }}
            h1, h2, h3 {{
                color: #1a365d;
                margin-top: 30px;
            }}
            .impact-box {{
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
            }}
            .section {{
                margin: 30px 0;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
            }}
            .meta-info {{
                background: #f0f4f8;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .impact-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <h1>Analysis of Bill {bill['number']}</h1>

        <div class="meta-info">
            <h3>Bill Information</h3>
            <p><strong>Title:</strong> {bill['title']}</p>
            <p><strong>Congress:</strong> {bill.get('congress', 'N/A')}</p>
            <p><strong>Type:</strong> {bill.get('type', 'N/A').upper()}</p>
            <p><strong>Introduced:</strong> {bill.get('introduced_date', 'N/A')}</p>
            <p><strong>Sponsors:</strong> {', '.join(bill.get('sponsors', []))}</p>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <p>{analysis.get('summary', 'No executive summary available.')}</p>
        </div>

        <div class="section">
            <h2>Key Points</h2>
    """

    # Add Key Points - handle both string and dictionary formats
    key_points = analysis.get('key_points', [])
    if isinstance(key_points, list):
        for point in key_points:
            if isinstance(point, dict):
                impact_type = point.get('impact_type', 'neutral')
                point_text = point.get('point', '')
            else:
                impact_type = 'neutral'
                point_text = str(point)

            html += f"""
                <div class="impact-box" style="background-color: {impact_colors.get(impact_type, '#f8f9fa')}">
                    {point_text}
                </div>
            """
    elif isinstance(key_points, str):
        html += f"""
            <div class="impact-box" style="background-color: {impact_colors['neutral']}">
                {key_points}
            </div>
        """

    # Add Public Health Impacts
    ph_impacts = analysis.get('public_health_impacts', {})
    if ph_impacts:
        html += """
            <div class="section">
                <h2>Public Health Impact Analysis</h2>
                <div class="impact-grid">
        """

        # Direct Effects
        html += """
                    <div>
                        <h3>Direct Effects</h3>
        """
        direct_effects = ph_impacts.get('direct_effects', [])
        if isinstance(direct_effects, list):
            for effect in direct_effects:
                if isinstance(effect, dict):
                    impact_type = effect.get('impact_type', 'neutral')
                    effect_text = effect.get('effect', '')
                else:
                    impact_type = 'neutral'
                    effect_text = str(effect)

                html += f"""
                    <div class="impact-box" style="background-color: {impact_colors.get(impact_type, '#f8f9fa')}">
                        {effect_text}
                    </div>
                """
        elif isinstance(direct_effects, str):
            html += f"""
                <div class="impact-box" style="background-color: {impact_colors['neutral']}">
                    {direct_effects}
                </div            """

        # Indirect Effects
        html += """
                    </div></div>
                        <h3>Indirect Effects</h3>
        """
        indirect_effects= ph_impacts.get('indirect_effects', [])
        if isinstance(indirect_effects, list):
            for effect in indirect_effects:
                if isinstance(effect, dict):
                    impact_type = effect.get('impact_type', 'neutral')
                    effect_text = effect.get('effect', '')
                else:
                    impact_type = 'neutral'
                    effect_text= str(effect)

                html += f"""
                    <div class="impact-box" style="background-color: {impact_colors.get(impact_type, '#f8f9fa')}">
                        {effect_text}
                    </div>
                """
        elif isinstance(indirect_effects, str):
            html += f"""
                <div class="impact-box" style="background-color: {impact_colors['neutral']}">
                    {indirect_effects}
                </div>
            """

        html += """
                    </div>
                </div>
            </div>
        """

    # Overall Assessment
    overall = analysis.get('overall_assessment', {})
    if overall:
        html += """
            <div class="section">
                <h2>Overall Assessment</h2>
        """

        if isinstance(overall, dict):
            for aspect, impact in overall.items():
                impact_color = impact_colors.get(str(impact).lower(), '#f8f9fa')
                icon = '✅' if str(impact).lower() == 'positive' else '❌' if str(impact).lower() == 'negative' else '⚠️'
                html += f"""
                    <div class="impact-box" style="background-color: {impact_color}">
                        {icon} <strong>{str(aspect).replace('_', ' ').title()}:</strong> {str(impact).title()}
                    </div>
                """
        elif isinstance(overall, str):
            html += f"""
                <div class="impact-box" style="background-color: {impact_colors['neutral']}">
                    {overall}
                </div>
            """

        html += """
            </div>
        """

    html += f"""
        <div class="meta-info"><p><em>Analysis generated on {datetime.now().strftime("%B %d, %Y")}</em></p>
        </div>
    </body>
    </html>
    """

    return html

def load_user_preferences():
    """
    Load user preferences from the database into session state.
    """
    try:
        prefs = st.session_state.data_store.get_user_preferences(st.session_state.user_email)
        st.session_state.user_keywords = prefs.get('keywords', [])
        logger.info(f"Loaded preferences for user: {st.session_state.user_email}")
    except Exception as e:
        logger.error(f"Error loading preferences: {e}")
        st.session_state.user_keywords = []

def display_bill_list(bills):
    """Display the bills list with impact level filtering"""
    # Add filter dropdowns
    col1, col2 = st.columns(2)
    with col1:
        ph_filter = st.selectbox(
            "Filter by Public Health Impact",
            ["All", "High", "Medium", "Low", "Unknown"],
            key="ph_filter"
        )
    with col2:
        lg_filter = st.selectbox(
            "Filter by Local Government Impact",
            ["All", "High", "Medium", "Low", "Unknown"],
            key="lg_filter"
        )

    # Apply filters
    filtered_bills = bills
    if ph_filter != "All":
        filtered_bills = [b for b in filtered_bills 
                        if b.get('public_health_impact', 'unknown').lower() == ph_filter.lower()]
    if lg_filter != "All":
        filtered_bills = [b for b in filtered_bills 
                        if b.get('local_gov_impact', 'unknown').lower() == lg_filter.lower()]

    if filtered_bills:
        st.write(f"Showing {len(filtered_bills)} bills")
        for bill in filtered_bills:
            display_bill(bill)
    else:
        st.info("No bills found matching the selected filters.")



def main():
    """Main function to run the Streamlit app."""
    load_custom_css()
    initialize_session_state()
    load_user_preferences()

    # Initialize core objects if not already in session state
    if "congress_api" not in st.session_state:
        st.session_state.congress_api = CongressAPI()
    if "ai_processor" not in st.session_state:
        st.session_state.ai_processor = AIProcessor()
    if "alert_system" not in st.session_state:
        st.session_state.alert_system = AlertSystem()
    ai_proc = st.session_state.get("ai_processor")
    if not ai_proc:
        ai_proc = AIProcessor()
        st.session_state.ai_processor = ai_proc

    st.title("🏛️ Congress Legislation Monitor")
    st.subheader("Public Health Policy Tracking Dashboard")

    # Sidebar: only search functionality
    with st.sidebar:
        st.header("Search Bills")
        search_query = st.text_input("Enter keyword(s)", value=st.session_state.search_query)
        if st.button("Search"):
            st.session_state.search_query = search_query
            results = st.session_state.data_store.get_bills_by_keywords([search_query])
            st.session_state.search_results = results
            st.success(f"Found {len(results)} matching bills.")

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Latest Legislation", "Search History", "Analysis", "Database Maintenance"])

    with tab1:
        st.title("🏛️ Latest Legislation")
        # If a detailed bill has been selected, display its detailed view
        if st.session_state.current_bill_info:
            display_detailed_bill(st.session_state.current_bill_info, ai_proc)
            st.markdown("---")
            if st.button("← Back to Bills List", key="back_to_list"):
                st.session_state.current_bill_info = None
                st.rerun()
        else:
            # Display search results or the full list with filtering
            if st.session_state.search_query and st.session_state.search_results:
                st.header(f"Search Results for '{st.session_state.search_query}'")
                display_bill_list(st.session_state.search_results)
            else:
                st.header("Bills List")
                bills = st.session_state.data_store.get_tracked_legislation()
                if bills:
                    display_bill_list(bills)
                else:
                    st.info("No bills found in the database.")

    with tab2:
        st.header("Search History")
        try:
            history = st.session_state.data_store.get_search_history(st.session_state.user_email)
            if history:
                df = pd.DataFrame(history)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No search history available")
        except Exception as e:
            logger.error(f"Error loading search history: {e}")
            st.error("Failed to load search history")

    with tab3:
        st.header("Analysis Dashboard")
        st.write("### Trend Analysis")
        try:
            df = pd.DataFrame(
                {'legislation_count': [4, 6, 8, 5, 7, 9]},
                index=pd.date_range(start='2024-01-01', periods=6, freq='ME')
            )
            st.line_chart(df)
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            st.error("Failed to load visualization")

    with tab4:
        st.header("Database Maintenance")
        col1, col2 = st.columns(2)
        with col1:
            # Flush Database option
            if st.button("Flush Database", type="secondary"):
                if st.checkbox("Confirm database flush - this cannot be undone"):
                    with st.spinner("Flushing database..."):
                        try:
                            st.session_state.data_store.flush_database()
                            st.success("Database flushed successfully")
                        except Exception as e:
                            logger.error(f"Error flushing database: {e}")
                            st.error("Failed to flush database")
            # Full Refresh: Renew Database (fetch all bills since Jan 1, 2025)
            if st.button("Renew Database (Full Refresh)", help="Fetch all bills since Jan 1, 2025"):
                with st.spinner("Preparing to renew database..."):
                    try:
                        days_since_2025 = (date.today() - date(2025, 1, 1)).days
                        total_count = st.session_state.congress_api.get_total_bill_count(days_since_2025)
                        batch_size = 20
                        estimated_batches = (total_count // batch_size) + (1 if total_count % batch_size else 0)
                        estimated_time_sec = estimated_batches * 1.5  # approximate per batch
                        estimated_time_min = estimated_time_sec / 60
                        st.info(f"Total bills to fetch: {total_count}. Estimated time: {estimated_time_min:.1f} minutes.")
                    except Exception as e:
                        st.error(f"Failed to get total bill count: {e}")
                        return
                with st.spinner("Fetching bills and analyzing as they arrive..."):
                    try:
                        progress_text = st.empty()
                        progress_bar = st.progress(0)
                        offset = 0
                        total_fetched = 0
                        all_bills = []
                        days_since_2025 = (date.today() - date(2025, 1, 1)).days
                        while True:
                            progress_text.text(f"Fetching batch {offset//batch_size + 1}...")
                            new_bills = st.session_state.congress_api.fetch_new_legislation(
                                days_back=days_since_2025,
                                limit=batch_size,
                                offset=offset
                            )
                            if not new_bills:
                                break
                            for bill in new_bills:
                                updated_bill = st.session_state.congress_api.fetch_and_save_full_bill_data(
                                    bill['congress'], bill['type'], bill['number']
                                )
                                all_bills.append(updated_bill)
                                total_fetched += 1
                                if updated_bill.get('bill_text') and not updated_bill.get('analysis'):
                                    analysis_success = st.session_state.ai_processor.analyze_legislation(
                                        text=updated_bill['bill_text'],
                                        bill_number=str(updated_bill['number']),
                                        db_session=st.session_state.data_store.db_session
                                    )
                                    if analysis_success:
                                        # Get the updated bill with analysis
                                        analyzed_bill = st.session_state.data_store.get_bill_by_number(str(updated_bill['number']))
                                        # If impact levels are still unknown, determine them
                                        if (analyzed_bill.get('public_health_impact') == 'unknown' or 
                                            analyzed_bill.get('local_gov_impact') == 'unknown'):
                                            st.session_state.ai_processor.determine_impact_levels(
                                                analyzed_bill.get('analysis', {}),
                                                str(updated_bill['number']),
                                                st.session_state.data_store.db_session
                                            )
                            offset += batch_size
                            progress = min(1.0, total_fetched / total_count) if total_count > 0 else 1.0
                            progress_bar.progress(progress)
                            time.sleep(1)
                        if all_bills:
                            st.session_state.bills = all_bills
                            st.success(f"Renewed database: Successfully fetched and processed {total_fetched} bills.")
                        else:
                            st.info("No bills found during renewal.")
                    except Exception as e:
                        logger.error(f"Error renewing database: {e}")
                        st.error(f"Failed to renew database: {str(e)}")
        with col2:
            # Manual update: fetch new bills (using a 1-day window)
            if st.button("Manual Fetch Updates", help="Fetch new bills (manual update)"):
                with st.spinner("Fetching manual updates..."):
                    try:
                        new_bills = st.session_state.congress_api.fetch_new_legislation(days_back=1, limit=50)
                        count_manual = 0
                        for bill in new_bills:
                            updated_bill = st.session_state.congress_api.fetch_and_save_full_bill_data(
                                bill['congress'], bill['type'], bill['number']
                            )
                            if updated_bill:
                                count_manual += 1
                                if updated_bill.get('bill_text') and not updated_bill.get('analysis'):
                                    analysis_success = st.session_state.ai_processor.analyze_legislation(
                                        text=updated_bill['bill_text'],
                                        bill_number=str(updated_bill['number']),
                                        db_session=st.session_state.data_store.db_session
                                    )
                                    if analysis_success:
                                        # Get the updated bill with analysis
                                        analyzed_bill = st.session_state.data_store.get_bill_by_number(str(updated_bill['number']))
                                        # If impact levels are still unknown, determine them
                                        if (analyzed_bill.get('public_health_impact') == 'unknown' or 
                                            analyzed_bill.get('local_gov_impact') == 'unknown'):
                                            st.session_state.ai_processor.determine_impact_levels(
                                                analyzed_bill.get('analysis', {}),
                                                str(updated_bill['number']),
                                                st.session_state.data_store.db_session
                                            )
                        if count_manual:
                            st.success(f"Manual update: Fetched and processed {count_manual} new bills.")
                        else:
                            st.info("No new bills found during manual update.")
                    except Exception as e:
                        logger.error(f"Error in manual fetch updates: {e}")
                        st.error(f"Failed to fetch manual updates: {str(e)}")

    st.write("Note: Legislation updates and analysis are automatically processed in the background if the scheduler is active.")

if __name__ == "__main__":
    main()