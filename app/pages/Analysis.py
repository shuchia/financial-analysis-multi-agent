"""
Stock Analysis Page - InvestForge Multi-Page App
Extracted from app.py to enable clean navigation from ticker links
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path to import from app
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

# Import necessary functions from app
from components.analysis import render_analysis_page
from app import (
    load_user_usage,
    check_usage_limits,
    initiate_payment,
    icon
)

# Page configuration
st.set_page_config(
    page_title="Stock Analysis - InvestForge",
    page_icon="🔍",
    layout="wide"
)

# Authentication check
if not st.session_state.get('authenticated', False):
    st.error("⚠️ Please log in to access stock analysis.")
    if st.button("Go to Login"):
        st.switch_page("app.py")
    st.stop()

# Load CSS matching the main app
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* CSS Variables matching landing page */
    :root {
        --primary-color: #FF6B35;
        --secondary-color: #004E89;
        --accent-color: #1A759F;
        --success-color: #00BA6D;
        --warning-color: #F5B800;
        --danger-color: #E74C3C;
        --text-primary: #2C3E50;
        --text-secondary: #7F8C8D;
        --bg-primary: #FFFFFF;
        --bg-secondary: #F8F9FA;
    }

    /* Global Styles */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# Load usage on page load
if 'usage_loaded' not in st.session_state:
    load_user_usage()
    st.session_state.usage_loaded = True

# Check for demo mode
if st.session_state.get('demo_mode', False):
    st.info("🎮 Demo Mode: Explore all features with sample data!")

# Check usage limits
can_analyze, usage_message = check_usage_limits()

if not can_analyze:
    st.error(f"""
    ### 🚫 {usage_message}

    Upgrade to Growth plan for unlimited analyses and advanced features!
    """)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(":material/rocket_launch: Upgrade to Growth - $4.99/mo", type="primary", use_container_width=True):
            initiate_payment('growth')
    st.stop()

# Render the analysis page using the existing component
# This is the same function used in main_app()
render_analysis_page()
