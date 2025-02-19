# File: law.py

import streamlit as st
import logging
from utils import get_impact_color
from analysis import analyze_bill, display_analysis

logger = logging.getLogger(__name__)

def view_law_details(law):
    """Save the selected law into session state to trigger the detailed view."""
    st.session_state.current_bill_info = law
    return law

def display_law(law):
    """Display a summary view of a law with key fields and impact levels."""
    law_header = f"#{law.get('number', '')} ({law.get('type', '').upper()}): {law.get('title', '')}"
    with st.expander(law_header, expanded=False):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"**Congress:** {law.get('congress', 'N/A')}")
            if law.get('enacted_date'):
                st.write(f"📅 **Enacted:** {law['enacted_date']}")
        with col2:
            impact_level = law.get('public_health_impact', 'unknown').lower()
            color = get_impact_color(impact_level)
            st.markdown(f"""
                <div style='padding: 10px; border-radius: 5px; text-align: center;
                background-color: {color}20; border: 1px solid {color}'>
                🏥 Public Health Impact:<br/><strong>{impact_level.upper()}</strong>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            impact_level = law.get('local_gov_impact', 'unknown').lower()
            color = get_impact_color(impact_level)
            st.markdown(f"""
                <div style='padding: 10px; border-radius: 5px; text-align: center;
                background-color: {color}20; border: 1px solid {color}'>
                🏛️ Local Gov Impact:<br/><strong>{impact_level.upper()}</strong>
                </div>
            """, unsafe_allow_html=True)
        if law.get('analysis') and isinstance(law['analysis'], dict):
            summary = law['analysis'].get('summary')
            if summary:
                st.markdown("---")
                st.write("🤖 **AI Analysis Summary:**")
                st.markdown(f"""
                    <div style='padding: 15px; border-radius: 5px; background-color: #f0f4f8;
                    border-left: 4px solid #4299e1'>
                    {summary}
                    </div>
                """, unsafe_allow_html=True)
        # Use a standard button for "View Details"
        unique_key = f"view_law_{law.get('congress', '')}_{law.get('type', '')}_{law.get('number', '')}"
        if st.button("🔍 View Details", key=unique_key):
            st.session_state.current_bill_info = law
            st.rerun()

def display_detailed_law(law, ai_processor):
    """Display the detailed view for a single law."""
    if st.button("← Back to List", key="back_to_list_top"):
        st.session_state.current_bill_info = None
        st.rerun()

    st.title(f"Bill {law.get('number', '')}")
    st.subheader(law.get('title', ''))

    # Basic Information
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Basic Information")
        st.write(f"**Congress:** {law.get('congress', 'N/A')}")
        st.write(f"**Type:** {law.get('type', 'N/A')}")
        st.write(f"**Enacted Date:** {law.get('enacted_date', 'N/A')}")
        if law.get('sponsors'):
            st.write("**Sponsors:**", ", ".join(law['sponsors']))
    with col2:
        st.markdown("### Current Status")
        st.write(f"**Latest Action Date:** {law.get('last_action_date', 'N/A')}")
        if law.get('last_action_text'):
            st.write("**Latest Action:**", law['last_action_text'])

    # Summary of Impact Levels
    st.markdown("---")
    st.subheader("Impact Summary")
    col1, col2 = st.columns(2)
    with col1:
        public_health_impact = law.get('public_health_impact', 'unknown')
        color = get_impact_color(public_health_impact)
        st.markdown(f"""
            <div style='padding: 15px; border-radius: 5px; background-color: #f0f4f8;
            border-left: 4px solid {color}'>
            <strong>🏥 Public Health Impact Level:</strong> {public_health_impact.upper()}<br/><br/>
            {law.get('public_health_reasoning', 'No assessment available')}
            </div>
        """, unsafe_allow_html=True)
    with col2:
        local_gov_impact = law.get('local_gov_impact', 'unknown')
        color = get_impact_color(local_gov_impact)
        st.markdown(f"""
            <div style='padding: 15px; border-radius: 5px; background-color: #f0f4f8;
            border-left: 4px solid {color}'>
            <strong>🏛️ Local Government Impact Level:</strong> {local_gov_impact.upper()}<br/><br/>
            {law.get('local_gov_reasoning', 'No assessment available')}
            </div>
        """, unsafe_allow_html=True)

    # AI Analysis Results
    st.markdown("---")
    st.subheader("🤖 Detailed AI Analysis")

    # Get analysis from database or session state
    analysis = None
    try:
        if st.session_state.get('current_analysis'):
            analysis = st.session_state.current_analysis
        else:
            # If not in session state, try to get from database
            analysis = st.session_state.data_store.get_stored_analysis(str(law.get('number', '')))
            if analysis:
                st.session_state.current_analysis = analysis
                st.session_state.current_bill_info = law
    except Exception as e:
        logger.error(f"Error retrieving analysis: {e}")

    if analysis:
        from analysis import display_analysis
        display_analysis(analysis)
    else:
        st.info("No detailed analysis available for this law. Click 'Analyze Law' to generate an analysis.")

    # Available Documents
    if law.get('document_formats'):
        st.markdown("### Available Documents")
        cols = st.columns(len(law['document_formats']))
        for idx, (fmt_type, url) in enumerate(law['document_formats'].items()):
            with cols[idx]:
                button_class = "primary" if fmt_type == "PDF" else "secondary"
                icon = "📥" if fmt_type == "PDF" else "📄"
                button_text = f"{icon} {fmt_type}" 
                st.markdown(
                    f'<a href="{url}" target="_blank" class="material-button {button_class}">{button_text}</a>',
                    unsafe_allow_html=True
                )

    # Action Buttons
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Re-Analyze Law"):
            if analyze_bill(st.session_state.congress_api, ai_processor, law):
                st.success("Analysis complete!")
                st.rerun()
            else:
                st.error("Failed to analyze law")
    with col2:
        if st.button("🔍 Toggle Raw Data"):
            st.session_state.show_raw = not st.session_state.get('show_raw', False)

    if st.session_state.get('show_raw', False):
        st.header("Raw Law Details")
        st.json(law)

    # Bill Progression History
    if law.get('progression_data'):
        st.markdown("---")
        st.subheader("📊 Bill to Law Progression")
        progression = law['progression_data'].get('progression_history', [])
        if progression:
            for action in progression:
                date_str = action.get('date', '')
                text = action.get('text', '')
                chamber = action.get('chamber', '')
                if date_str and text:
                    st.markdown(f"""
                        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0;">
                            <strong>{date_str}</strong> ({chamber})<br/><em>{text}</em>
                        </div>
                    """, unsafe_allow_html=True)

def display_law_list(laws):
    """Display the list of laws with filtering options."""
    col1, col2 = st.columns(2)
    with col1:
        ph_filter = st.selectbox(
            "Filter by Public Health Impact",
            ["All", "High", "Medium", "Low", "Unknown"],
            key="law_ph_filter"
        )
    with col2:
        lg_filter = st.selectbox(
            "Filter by Local Government Impact",
            ["All", "High", "Medium", "Low", "Unknown"],
            key="law_lg_filter"
        )
    filtered_laws = laws
    if ph_filter != "All":
        filtered_laws = [l for l in filtered_laws if l.get('public_health_impact', 'unknown').lower() == ph_filter.lower()]
    if lg_filter != "All":
        filtered_laws = [l for l in filtered_laws if l.get('local_gov_impact', 'unknown').lower() == lg_filter.lower()]
    if filtered_laws:
        st.write(f"Showing {len(filtered_laws)} laws")
        for law in filtered_laws:
            display_law(law)
    else:
        st.info("No laws found matching the selected filters.")