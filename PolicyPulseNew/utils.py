import streamlit as st

def load_custom_css():
    """Load custom CSS for better UI appearance"""
    st.markdown("""
        <style>
        /* Base button styles */
        .material-button {
            padding: 12px 20px;
            border-radius: 8px;
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            width: 100%;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            margin: 4px 0;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
        }

        /* Primary button - for main actions like Download */
        .material-button.primary {
            background-color: #1976d2 !important;
            color: white !important;
        }
        .material-button.primary:hover {
            background-color: #1565c0 !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transform: translateY(-1px);
        }

        /* Secondary button - for view actions */
        .material-button.secondary {
            background-color: #FFE5CC !important;
            color: #333 !important;
        }
        .material-button.secondary:hover {
            background-color: #FFD6B3 !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transform: translateY(-1px);
        }

        /* Neutral button - for less prominent actions */
        .material-button.neutral {
            background-color: #f5f5f5 !important;
            color: #333 !important;
        }
        .material-button.neutral:hover {
            background-color: #e0e0e0 !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transform: translateY(-1px);
        }

        /* Other Streamlit component styles */
        .stButton > button {
            width: 100%;
        }
        .stProgress > div > div > div {
            background-color: #1976d2;
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
        .download-button {
            padding: 12px 20px;
            border-radius: 8px;
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            width: 100%;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            margin: 4px 0;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            background-color: #1976d2;
            color: white;
        }
        .download-button:hover {
            background-color: #1565c0;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transform: translateY(-1px);
        }

        </style>
    """, unsafe_allow_html=True)

def get_impact_color(impact_type: str) -> str:
    """Return a hex color code based on the impact type."""
    colors = {
        'positive': '#dcfce7',  # Light green
        'negative': '#fecaca',  # Light red
        'neutral': '#e6f3ff'    # Light blue
    }
    return colors.get(impact_type.lower(), colors['neutral'])