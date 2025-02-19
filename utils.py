import streamlit as st

def load_custom_css():
    """Load custom CSS for better UI appearance"""
    st.markdown("""
        <style>
        .stButton > button {
            width: 100%;
        }
        .stProgress > div > div > div {
            background-color: #0066cc;
        }
        .stAlert > div {
            padding: 1rem;
            border-radius: 0.5rem;
        }
        .stExpander {
            background-color: #f8f9fa;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .stTab {
            font-size: 1.1rem;
        }
        </style>
    """, unsafe_allow_html=True)
