# File: main.py

import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import logging
import base64
import json

from ai_processor import AIProcessor
from congress_api import CongressAPI
from alert_system import AlertSystem
from data_store import DataStore
from utils import load_custom_css

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_session_state():
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

def format_json_field(json_data, indent=2):
    """Format JSON data for better readability in Streamlit."""
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except:
            return json_data
    return json.dumps(json_data, indent=indent)

def view_bill_details(bill):
    """Display complete bill information including all database fields."""
    st.session_state.current_bill_info = bill

    # Basic Information
    st.header(f"Bill {bill.get('bill_type', '')} {bill.get('bill_number', '')}")
    st.subheader(bill.get('title', ''))

    col1, col2 = st.columns(2)
    with col1:
        st.write("**Congress:**", bill.get('congress', ''))
        st.write("**Introduced Date:**", bill.get('introduced_date', ''))
        st.write("**Status:**", bill.get('status', ''))

    with col2:
        st.write("**Public Health Impact:**", bill.get('public_health_impact', ''))
        st.write("**Local Government Impact:**", bill.get('local_gov_impact', ''))

    # Impact Analysis
    st.subheader("Impact Analysis")
    if bill.get('public_health_reasoning'):
        st.write("**Public Health Reasoning:**")
        st.write(bill.get('public_health_reasoning', ''))
    if bill.get('local_gov_reasoning'):
        st.write("**Local Government Reasoning:**")
        st.write(bill.get('local_gov_reasoning', ''))

    # Law Information (if available)
    if any(bill.get(field) for field in ['law_number', 'law_type', 'law_enacted_date']):
        st.subheader("Law Information")
        st.write("**Law Number:**", bill.get('law_number', ''))
        st.write("**Law Type:**", bill.get('law_type', ''))
        st.write("**Enacted Date:**", bill.get('law_enacted_date', ''))
        if bill.get('law_description'):
            st.write("**Description:**", bill.get('law_description', ''))

    # Bill Text
    if bill.get('bill_text'):
        with st.expander("View Bill Text"):
            st.text(bill.get('bill_text', ''))

    # Detailed Analysis
    if bill.get('analysis'):
        with st.expander("View Detailed Analysis"):
            st.json(bill.get('analysis'))

    # Raw API Response
    if bill.get('raw_api_response'):
        with st.expander("View Raw API Response"):
            st.json(bill.get('raw_api_response'))

    # Document Formats
    if bill.get('document_formats'):
        with st.expander("Available Document Formats"):
            st.json(bill.get('document_formats'))

    # Progression History
    if bill.get('progression_history'):
        with st.expander("View Progression History"):
            st.json(bill.get('progression_history'))

    return bill

def analyze_bill(congress_api, ai_processor, bill):
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
        logger.error(f"Error analyzing bill {bill.get('number', 'unknown')}: {e}")
        return False

def parse_date(date_str):
    """Parse a date string that may include a time component."""
    if 'T' in date_str:
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S').date()
    else:
        return datetime.strptime(date_str, '%Y-%m-%d').date()

def main():
    st.set_page_config(
        page_title="Congress Legislation Monitor",
        page_icon="🏛️",
        layout="wide"
    )
    load_custom_css()
    initialize_session_state()
    if "congress_api" not in st.session_state:
        st.session_state.congress_api = CongressAPI()
    if "ai_processor" not in st.session_state:
        st.session_state.ai_processor = AIProcessor()
    if "alert_system" not in st.session_state:
        st.session_state.alert_system = AlertSystem()

    st.title("🏛️ Congress Legislation Monitor")
    st.subheader("Public Health Policy Tracking Dashboard")

    # Sidebar search functionality
    with st.sidebar:
        st.header("Search Bills")
        search_query = st.text_input("Enter keyword(s)", value=st.session_state.search_query)
        if st.button("Search"):
            st.session_state.search_query = search_query
            results = st.session_state.data_store.get_bills_by_keywords([search_query])
            st.session_state.search_results = results
            st.success(f"Found {len(results)} matching bills.")

    # Main navigation tabs
    tabs = st.tabs([
        "Latest Legislation",
        "Enacted Laws",
        "Search History",
        "Analysis Dashboard",
        "Database Maintenance"
    ])

    # Latest Legislation tab
    with tabs[0]:
        if st.session_state.current_bill_info:
            view_bill_details(st.session_state.current_bill_info)
            st.markdown("---")
            if st.button("← Back to Bills List", key="back_to_list"):
                st.session_state.current_bill_info = None
                st.rerun()
        else:
            st.title("🏛️ Latest Legislation")
            bills = st.session_state.data_store.get_tracked_legislation()
            if bills:
                bill_dates = [parse_date(bill['introduced_date']) for bill in bills if bill.get('introduced_date')]
                if bill_dates:
                    min_date = min(bill_dates)
                    max_date = max(bill_dates)
                else:
                    min_date = max_date = None
                date_range = None
                if min_date and max_date:
                    date_range = st.date_input("Filter by Introduced Date", value=[min_date, max_date])
                num_items = st.number_input("Number of items to display", min_value=1, max_value=len(bills), value=len(bills))
                if date_range and len(date_range)==2:
                    start_date, end_date = date_range
                    filtered_bills = []
                    for bill in bills:
                        if bill.get('introduced_date'):
                            bill_date = parse_date(bill['introduced_date'])
                            if start_date <= bill_date <= end_date:
                                filtered_bills.append(bill)
                        else:
                            filtered_bills.append(bill)
                else:
                    filtered_bills = bills
                filtered_bills = filtered_bills[:num_items]
                st.header(f"Latest Legislation - ({len(filtered_bills)} Records)")
                from bill import display_bill_list
                display_bill_list(filtered_bills)
            else:
                st.info("No bills found in the database.")

    # Enacted Laws tab: load law records from the database
    with tabs[1]:
        if st.session_state.current_bill_info:
            from law import display_detailed_law
            display_detailed_law(st.session_state.current_bill_info, st.session_state.ai_processor)
            st.markdown("---")
            if st.button("← Back to Laws List", key="back_to_law_list"):
                st.session_state.current_bill_info = None
                st.rerun()
        else:
            st.title("Enacted Laws")
            # Instead of calling the API every time, load laws from the database:
            laws = st.session_state.data_store.get_enacted_laws()
            st.header(f"Enacted Laws - ({len(laws)} Records)")
            from law import display_law_list
            display_law_list(laws)

    # Search History tab
    with tabs[2]:
        st.header("Search History")
        try:
            history = st.session_state.data_store.get_search_history(st.session_state.user_email)
            if history:
                for item in history:
                    st.write(f"🔍 {item['query']} ({item['timestamp']})")
            else:
                st.info("No search history available")
        except Exception as e:
            logger.error(f"Error loading search history: {e}")
            st.error("Failed to load search history")

    # Analysis Dashboard tab
    with tabs[3]:
        st.header("Analysis Dashboard")
        st.write("### Trend Analysis")
        from analysis import create_impact_visualization
        create_impact_visualization()

    # Database Maintenance tab
    with tabs[4]:
        st.header("Database Maintenance")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 Manual Update Bills"):
                with st.spinner("Fetching latest bills..."):
                    try:
                        congress_api = st.session_state.congress_api
                        new_bills = congress_api.fetch_new_legislation()
                        if new_bills:
                            st.success(f"Updated {len(new_bills)} bills")
                        else:
                            st.info("No new bills found")
                    except Exception as e:
                        logger.error(f"Error updating bills: {e}")
                        st.error("Failed to update bills")
        with col2:
            if st.button("Manual Update Laws", key="manual_update_laws"):
                with st.spinner("Fetching recent laws..."):
                    try:
                        logger.info("Starting manual law update process...")
                        # Fetch recent laws from the API (this function stores them in the database)
                        new_laws = st.session_state.congress_api.get_recent_laws(days_back=30, limit=50)
                        logger.info(f"Retrieved {len(new_laws)} laws from API")

                        for law in new_laws:
                            logger.info(f"Processing law: {law.get('number')} - {law.get('title')}")
                            logger.info(f"Law data: {json.dumps(law, indent=2)}")

                            # Verify law data
                            if law.get('bill_text'):
                                logger.info("Bill text found, proceeding with analysis")
                                if not law.get('analysis'):
                                    # Use both bill_number and law_number for analysis
                                    analysis_success = st.session_state.ai_processor.analyze_legislation(
                                        text=law['bill_text'],
                                        bill_number=str(law['bill_number']),
                                        law_number=str(law['number']),
                                        db_session=st.session_state.data_store.db_session
                                    )
                                    if analysis_success:
                                        logger.info(f"Analysis completed for bill {law['bill_number']} (Law {law['number']})")
                                        stored_analysis = st.session_state.ai_processor.get_stored_analysis(
                                            bill_number=str(law['bill_number']),
                                            law_number=str(law['number']),
                                            db_session=st.session_state.data_store.db_session
                                        )
                                        if stored_analysis:
                                            impact_success = st.session_state.ai_processor.determine_impact_levels(
                                                stored_analysis,
                                                str(law['bill_number']),
                                                st.session_state.data_store.db_session,
                                                law_number=str(law['number'])
                                            )
                                            if impact_success:
                                                logger.info(f"Impact levels determined for bill {law['bill_number']} (Law {law['number']})")
                                            else:
                                                logger.warning(f"Failed to determine impact levels for bill {law['bill_number']} (Law {law['number']})")
                                        else:
                                            logger.warning(f"No stored analysis found for bill {law['bill_number']} (Law {law['number']})")
                                    else:
                                        logger.warning(f"Analysis failed for bill {law['bill_number']} (Law {law['number']})")
                            else:
                                logger.warning(f"No bill text found for law {law['number']}")

                        count = len(new_laws)
                        if count > 0:
                            st.success(f"Updated {count} laws")
                            logger.info(f"Successfully updated {count} laws")
                        else:
                            st.info("No new laws found to update")
                            logger.info("No new laws found in the specified timeframe")

                    except Exception as e:
                        logger.error(f"Error updating laws: {str(e)}")
                        st.error(f"Failed to update laws: {str(e)}")
        with col3:
            if st.button("Flush Database", type="secondary"):
                if st.checkbox("Confirm database flush - this cannot be undone", key="flush_confirm"):
                    with st.spinner("Flushing database..."):
                        try:
                            st.session_state.data_store.flush_database()
                            st.success("Database flushed successfully")
                        except Exception as e:
                            logger.error(f"Error flushing database: {e}")
                            st.error("Failed to flush database")
        st.write("Note: Legislation updates and analysis are automatically processed in the background if the scheduler is active.")

if __name__ == "__main__":
    main()