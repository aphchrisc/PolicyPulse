# File: analysis.py

import streamlit as st
import pandas as pd
import json
import logging
from datetime import datetime

# Set up module-level logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def analyze_bill(congress_api, ai_processor, bill):
    """
    Perform detailed analysis on the given bill.

    This function fetches the bill text (or uses a summary if the full text is not available),
    calls the provided ai_processor to analyze the legislation, and then stores the resulting
    analysis in session state.

    Args:
        congress_api: An instance used to fetch bill text.
        ai_processor: An instance with methods to perform AI analysis.
        bill (dict): A dictionary containing bill data.

    Returns:
        bool: True if analysis succeeded, False otherwise.
    """
    try:
        bill_text = congress_api.get_bill_text(
            bill['congress'],
            bill['type'],
            bill['number']
        )
        if not bill_text and bill.get('summary'):
            st.warning("Full bill text not available; using summary for analysis.")
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
        logger.error(f"Error in analyze_bill for bill {bill.get('number', 'unknown')}: {e}")
        st.error(f"Error analyzing bill: {e}")
        return False

def display_analysis(analysis):
    """
    Render the stored AI analysis results for the current bill.

    Args:
        analysis (dict): The analysis data to display
    """
    try:
        if not analysis:
            st.info("No analysis available.")
            return

        # Executive Summary Section
        st.write("### Executive Summary")
        st.write(analysis.get('summary', 'No executive summary available.'))

        # Key Points Section with Impact Types
        st.write("### Key Points")
        key_points = analysis.get('key_points', [])
        if key_points:
            for point in key_points:
                if isinstance(point, dict):
                    impact_type = point.get('impact_type', 'neutral')
                    text = point.get('point', '')
                else:
                    impact_type = 'neutral'
                    text = str(point)

                color = get_impact_color(impact_type)
                st.markdown(
                    f"""<div style="background-color: {color}; padding: 10px; 
                    border-radius: 5px; margin: 5px 0;">{text}</div>""",
                    unsafe_allow_html=True
                )

        # Public Health Impact Analysis Section
        st.write("### Public Health Impact Analysis")
        ph_impacts = analysis.get('public_health_impacts', {})

        tabs = st.tabs(["Direct Effects", "Indirect Effects", "Funding Impact", "Vulnerable Populations"])

        with tabs[0]:
            st.write("#### Direct Effects")
            for effect in ph_impacts.get('direct_effects', []):
                if isinstance(effect, dict):
                    impact_type = effect.get('impact_type', 'neutral')
                    text = effect.get('effect', '')
                else:
                    impact_type = 'neutral'
                    text = str(effect)
                color = get_impact_color(impact_type)
                st.markdown(
                    f"""<div style="background-color: {color}; padding: 10px; 
                    border-radius: 5px; margin: 5px 0;">{text}</div>""",
                    unsafe_allow_html=True
                )

        with tabs[1]:
            st.write("#### Indirect Effects")
            for effect in ph_impacts.get('indirect_effects', []):
                if isinstance(effect, dict):
                    impact_type = effect.get('impact_type', 'neutral')
                    text = effect.get('effect', '')
                else:
                    impact_type = 'neutral'
                    text = str(effect)
                color = get_impact_color(impact_type)
                st.markdown(
                    f"""<div style="background-color: {color}; padding: 10px; 
                    border-radius: 5px; margin: 5px 0;">{text}</div>""",
                    unsafe_allow_html=True
                )

        with tabs[2]:
            st.write("#### Funding Impact")
            for impact in ph_impacts.get('funding_impact', []):
                if isinstance(impact, dict):
                    impact_type = impact.get('impact_type', 'neutral')
                    text = impact.get('impact', '')
                else:
                    impact_type = 'neutral'
                    text = str(impact)
                color = get_impact_color(impact_type)
                st.markdown(
                    f"""<div style="background-color: {color}; padding: 10px; 
                    border-radius: 5px; margin: 5px 0;">{text}</div>""",
                    unsafe_allow_html=True
                )

        with tabs[3]:
            st.write("#### Vulnerable Populations")
            for impact in ph_impacts.get('vulnerable_populations', []):
                if isinstance(impact, dict):
                    impact_type = impact.get('impact_type', 'neutral')
                    text = impact.get('impact', '')
                else:
                    impact_type = 'neutral'
                    text = str(impact)
                color = get_impact_color(impact_type)
                st.markdown(
                    f"""<div style="background-color: {color}; padding: 10px; 
                    border-radius: 5px; margin: 5px 0;">{text}</div>""",
                    unsafe_allow_html=True
                )

        # Public Health Official Actions Section
        st.write("### Public Health Official Actions")
        ph_actions = analysis.get('public_health_official_actions', {})
        if ph_actions:
            actions_tabs = st.tabs([
                "Immediate Considerations",
                "Recommended Actions",
                "Resource Needs",
                "Stakeholder Engagement"
            ])

            with actions_tabs[0]:
                st.write("#### Immediate Considerations")
                for item in ph_actions.get('immediate_considerations', []):
                    if isinstance(item, dict):
                        impact_type = item.get('impact_type', 'neutral')
                        text = item.get('consideration', '')
                        priority = item.get('priority', 'medium')
                    else:
                        impact_type = 'neutral'
                        text = str(item)
                        priority = 'medium'
                    color = get_impact_color(impact_type)
                    st.markdown(
                        f"""<div style="background-color: {color}; padding: 10px; 
                        border-radius: 5px; margin: 5px 0;">
                        <strong>Priority:</strong> {priority.title()}<br>{text}</div>""",
                        unsafe_allow_html=True
                    )

            with actions_tabs[1]:
                st.write("#### Recommended Actions")
                for item in ph_actions.get('recommended_actions', []):
                    if isinstance(item, dict):
                        impact_type = item.get('impact_type', 'neutral')
                        text = item.get('action', '')
                        timeline = item.get('timeline', 'short_term')
                    else:
                        impact_type = 'neutral'
                        text = str(item)
                        timeline = 'short_term'
                    color = get_impact_color(impact_type)
                    st.markdown(
                        f"""<div style="background-color: {color}; padding: 10px; 
                        border-radius: 5px; margin: 5px 0;">
                        <strong>Timeline:</strong> {timeline.replace('_', ' ').title()}<br>{text}</div>""",
                        unsafe_allow_html=True
                    )

            with actions_tabs[2]:
                st.write("#### Resource Needs")
                for item in ph_actions.get('resource_needs', []):
                    if isinstance(item, dict):
                        impact_type = item.get('impact_type', 'neutral')
                        text = item.get('need', '')
                        urgency = item.get('urgency', 'important')
                    else:
                        impact_type = 'neutral'
                        text = str(item)
                        urgency = 'important'
                    color = get_impact_color(impact_type)
                    st.markdown(
                        f"""<div style="background-color: {color}; padding: 10px; 
                        border-radius: 5px; margin: 5px 0;">
                        <strong>Urgency:</strong> {urgency.title()}<br>{text}</div>""",
                        unsafe_allow_html=True
                    )

            with actions_tabs[3]:
                st.write("#### Stakeholder Engagement")
                for item in ph_actions.get('stakeholder_engagement', []):
                    if isinstance(item, dict):
                        impact_type = item.get('impact_type', 'neutral')
                        text = item.get('stakeholder', '')
                        importance = item.get('importance', 'recommended')
                    else:
                        impact_type = 'neutral'
                        text = str(item)
                        importance = 'recommended'
                    color = get_impact_color(impact_type)
                    st.markdown(
                        f"""<div style="background-color: {color}; padding: 10px; 
                        border-radius: 5px; margin: 5px 0;">
                        <strong>Importance:</strong> {importance.title()}<br>{text}</div>""",
                        unsafe_allow_html=True
                    )

        # Overall Assessment Section
        st.write("### Overall Assessment")
        overall = analysis.get('overall_assessment', {})
        if overall:
            col1, col2 = st.columns(2)
            with col1:
                impact = overall.get('public_health', 'unknown')
                color = get_impact_color(impact)
                icon = '✅' if impact.lower() == 'positive' else '❌' if impact.lower() == 'negative' else '⚠️'
                st.markdown(
                    f"""<div style="background-color: {color}; padding: 10px; 
                    border-radius: 5px; margin: 5px 0;">
                    {icon} <strong>Public Health Impact:</strong> {impact.title()}</div>""",
                    unsafe_allow_html=True
                )
            with col2:
                impact = overall.get('local_government', 'unknown')
                color = get_impact_color(impact)
                icon = '✅' if impact.lower() == 'positive' else '❌' if impact.lower() == 'negative' else '⚠️'
                st.markdown(
                    f"""<div style="background-color: {color}; padding: 10px; 
                    border-radius: 5px; margin: 5px 0;">
                    {icon} <strong>Local Government Impact:</strong> {impact.title()}</div>""",
                    unsafe_allow_html=True
                )

    except Exception as e:
        logger.error(f"Error displaying analysis: {e}")
        st.error("An error occurred while displaying the analysis.")

def generate_download_link(content: str, filename: str, button_text: str = "Download", button_class: str = "download-button") -> str:
    """
    Generate an HTML download link for the provided content.

    Args:
        content (str): The content to be downloaded.
        filename (str): The filename for the download.
        button_text (str): The text displayed on the button.
        button_class (str): The CSS class for styling the button.

    Returns:
        str: An HTML anchor tag containing the download link.
    """
    import base64
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
        bill (dict): Bill information.
        analysis (dict): The analysis data.

    Returns:
        str: A formatted HTML document.
    """
    html = f"""
    <html>
    <head>
        <title>Analysis of Bill {bill.get('number', 'Unknown')}</title>
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
            pre {{
                background-color: #f0f4f8;
                padding: 15px;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <h1>Analysis of Bill {bill.get('number', 'Unknown')}</h1>
        <h2>Executive Summary</h2>
        <p>{analysis.get('summary', 'No executive summary available.')}</p>
        <h2>Full Analysis</h2>
        <pre>{json.dumps(analysis, indent=2)}</pre>
    </body>
    </html>
    """
    return html

def create_impact_visualization():
    """
    Create a simple impact trend visualization using dummy data.

    This function generates a line chart of impact trends. Replace the dummy
    data below with your actual impact data as needed.
    """
    dates = pd.date_range(start='2023-01-01', periods=10, freq='ME')
    data = {
        'Public Health Impact': [1, 2, 3, 2, 3, 4, 3, 5, 4, 6],
        'Local Gov Impact': [2, 3, 4, 3, 4, 5, 4, 6, 5, 7]
    }
    df = pd.DataFrame(data, index=dates)
    st.line_chart(df)

def get_impact_color(impact_type: str) -> str:
    """Return a hex color code based on the provided impact type."""
    colors = {
        'positive': '#dcfce7',  # light green
        'negative': '#fecaca',  # light red
        'neutral': '#e6f3ff',   # light blue
        'high': '#fecaca',      # light red
        'medium': '#fed7aa',    # light orange
        'low': '#dcfce7',       # light green
        'unknown': '#f3f4f6'    # light gray
    }
    return colors.get(impact_type.lower(), colors['neutral'])

# End of analysis.py