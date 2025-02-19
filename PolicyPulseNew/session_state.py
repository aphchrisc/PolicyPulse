"""
Session state helper functions.
This module is responsible for initializing and loading
various session-level variables required by the application.
"""

import streamlit as st
import logging

logger = logging.getLogger(__name__)

def initialize_session_state():
    """
    Initialize required session state variables.
    These include objects for database access, current bill data,
    search results, and UI toggles.
    """
    if 'data_store' not in st.session_state:
        from data_store import DataStore  # Lazy import to avoid circular dependency
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
