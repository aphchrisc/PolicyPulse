import streamlit as st
import logging
import base64
from analysis import analyze_bill, display_analysis, get_analysis_html, generate_download_link
from utils import get_impact_color

logger = logging.getLogger(__name__)

def view_bill_details(bill):
    """Save the selected bill into session state and retrieve its analysis."""
    st.session_state.current_bill_info = bill

    # Try to get existing analysis from database
    try:
        analysis = st.session_state.data_store.get_stored_analysis(str(bill['number']))
        if analysis:
            st.session_state.current_analysis = analysis
    except Exception as e:
        logger.error(f"Error retrieving analysis in view_bill_details: {e}")

    return bill

def display_detailed_bill(bill, ai_processor):
    """Display the detailed view for a single bill."""
    if st.button("← Back to List", key="back_to_list_top"):
        st.session_state.current_bill_info = None
        st.rerun()

    st.title(f"Bill {bill['number']}")
    st.header(bill['title'])
    st.markdown("---")

    # Basic bill information card
    with st.container():
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

    # Summary of Impact Levels
    st.markdown("---")
    st.subheader("Impact Summary")
    col1, col2 = st.columns(2)
    with col1:
        public_health_impact = bill.get('public_health_impact', 'unknown')
        color = get_impact_color(public_health_impact)
        st.markdown(f"""
            <div style='padding: 15px; border-radius: 5px; background-color: #f0f4f8;
            border-left: 4px solid {color}'>
            <strong>🏥 Public Health Impact Level:</strong> {public_health_impact.upper()}<br/><br/>
            {bill.get('public_health_reasoning', 'No assessment available')}
            </div>
        """, unsafe_allow_html=True)
    with col2:
        local_gov_impact = bill.get('local_gov_impact', 'unknown')
        color = get_impact_color(local_gov_impact)
        st.markdown(f"""
            <div style='padding: 15px; border-radius: 5px; background-color: #f0f4f8;
            border-left: 4px solid {color}'>
            <strong>🏛️ Local Government Impact Level:</strong> {local_gov_impact.upper()}<br/><br/>
            {bill.get('local_gov_reasoning', 'No assessment available')}
            </div>
        """, unsafe_allow_html=True)

    # AI Analysis Results
    st.markdown("---")
    st.subheader("🤖 Detailed AI Analysis")

    # Get analysis from session state or database
    analysis = None
    try:
        if hasattr(st.session_state, 'current_analysis') and st.session_state.current_analysis:
            analysis = st.session_state.current_analysis
        else:
            # Try to get from database
            analysis = st.session_state.data_store.get_stored_analysis(str(bill['number']))
            if analysis:
                st.session_state.current_analysis = analysis
                st.session_state.current_bill_info = bill
    except Exception as e:
        logger.error(f"Error retrieving analysis: {e}")

    if analysis:
        display_analysis(analysis)
    else:
        st.info("No detailed analysis available for this bill. Click 'Analyze Bill' to generate an analysis.")

    # Action Buttons
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        button_text = "🔄 Re-Analyze Bill" if analysis else "🤖 Analyze Bill"
        if st.button(button_text):
            if analyze_bill(st.session_state.congress_api, ai_processor, bill):
                st.success("Analysis complete!")
                st.rerun()
            else:
                st.error("Failed to analyze bill")
    with col2:
        if st.button("🔍 Toggle Raw Data"):
            st.session_state.show_raw = not st.session_state.get('show_raw', False)

    if st.session_state.get('show_raw', False):
        st.header("Raw Bill Details")
        st.json(bill)

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
            color = get_impact_color(impact_level)
            st.markdown(f"""
                <div style='padding: 10px; border-radius: 5px; text-align: center;
                background-color: {color}20; border: 1px solid {color}'>
                🏥 Public Health Impact:<br/><strong>{impact_level.upper()}</strong>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            impact_level = bill.get('local_gov_impact', 'unknown').lower()
            color = get_impact_color(impact_level)
            st.markdown(f"""
                <div style='padding: 10px; border-radius: 5px; text-align: center;
                background-color: {color}20; border: 1px solid {color}'>
                🏛️ Local Gov Impact:<br/><strong>{impact_level.upper()}</strong>
                </div>
            """, unsafe_allow_html=True)

        # View Details button
        unique_key = f"view_{bill.get('congress', '')}_{bill.get('type', '')}_{bill['number']}"
        if st.button("🔍 View Details", key=unique_key):
            view_bill_details(bill)
            st.rerun()

def display_bill_list(bills):
    """Display the list of bills with filtering options."""
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

    filtered_bills = bills
    if ph_filter != "All":
        filtered_bills = [
            b for b in filtered_bills
            if b.get('public_health_impact', 'unknown').lower() == ph_filter.lower()
        ]
    if lg_filter != "All":
        filtered_bills = [
            b for b in filtered_bills
            if b.get('local_gov_impact', 'unknown').lower() == lg_filter.lower()
        ]

    if filtered_bills:
        st.write(f"Showing {len(filtered_bills)} bills")
        for bill in filtered_bills:
            display_bill(bill)
    else:
        st.info("No bills found matching the selected filters.")