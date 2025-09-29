# =====================================
# File: app.py - Enhanced with landing page integration
# =====================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from urllib.parse import parse_qs, urlparse
import json
import hashlib
import hmac
from typing import Optional, Dict, Tuple, Any
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.api_client import api_client
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================
# Error Boundary Implementation
# =====================================

class ErrorBoundary:
    """Context manager for handling errors gracefully"""
    
    def __init__(self, fallback_message="An error occurred. Please try again."):
        self.fallback_message = fallback_message
        self.error_container = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Error caught: {exc_type.__name__}: {exc_val}")
            logger.error(traceback.format_exc())
            
            st.error(f"""
            ### ❌ {self.fallback_message}
            
            **Error Details:** {exc_type.__name__}: {str(exc_val)}
            
            If this issue persists, please contact support.
            """)
            
            # Log to analytics
            if 'user_data' in st.session_state:
                user_id = st.session_state.user_data.get('user_id')
                if user_id:
                    api_client.track_event('error_occurred', {
                        'error_type': exc_type.__name__,
                        'error_message': str(exc_val),
                        'location': 'analysis_page'
                    })
            
            return True  # Suppress the exception
        return False

# =====================================
# Configuration & Setup
# =====================================

# Health check endpoint for ALB
if 'health' in st.query_params:
    st.write("OK")
    st.stop()

st.set_page_config(
    page_title="InvestForge - AI Investment Analysis",
    page_icon="⚒️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =====================================
# Session State Management
# =====================================

def init_session_state():
    """Initialize session state variables."""
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'user_plan' not in st.session_state:
        st.session_state.user_plan = 'free'
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'analyses_count' not in st.session_state:
        st.session_state.analyses_count = 0
    if 'demo_mode' not in st.session_state:
        st.session_state.demo_mode = False
    if 'onboarding_complete' not in st.session_state:
        st.session_state.onboarding_complete = False
    if 'user_data' not in st.session_state:
        st.session_state.user_data = {}
    if 'monthly_usage' not in st.session_state:
        st.session_state.monthly_usage = {}
    if 'analysis_history' not in st.session_state:
        st.session_state.analysis_history = []


# =====================================
# URL Parameter Processing
# =====================================

def process_url_params():
    """Process parameters passed from landing page."""
    query_params = st.query_params

    # Check for email from waitlist
    if 'email' in query_params:
        st.session_state.user_email = query_params['email'][0]
        st.session_state.show_welcome = True

    # Check for selected plan
    if 'plan' in query_params:
        st.session_state.user_plan = query_params['plan'][0]
        st.session_state.show_pricing = True

    # Check for demo mode
    if 'mode' in query_params and query_params['mode'][0] == 'demo':
        st.session_state.demo_mode = True
        st.session_state.authenticated = True
        st.session_state.user_email = 'demo@investforge.io'

    # Check for referral source
    if 'ref' in query_params:
        st.session_state.referral_source = query_params['ref'][0]
        track_referral(query_params['ref'][0])


# =====================================
# Authentication System
# =====================================

def show_login_signup():
    """Display login/signup interface."""
    
    # Apply the same custom CSS for login page
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
            --bg-secondary: #F8F9FA;
        }
        
        .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            min-height: 100vh;
        }
        
        .login-logo {
            animation: logoFloat 3s ease-in-out infinite;
        }
        
        @keyframes logoFloat {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Logo and branding
        try:
            st.image("app/static/images/investforge-logo.png", width=150)
        except:
            st.markdown("⚒️", unsafe_allow_html=True)
            
        st.markdown("""
        <div style='text-align: center; padding: 1rem 0;'>
            <h1 style='font-size: 3rem; background: linear-gradient(135deg, #FF6B35, #004E89);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                       font-weight: 700;'>
                InvestForge
            </h1>
            <p style='color: #7F8C8D; font-size: 1.2rem; font-weight: 500;'>Forge Your Financial Future with AI</p>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email", value=st.session_state.user_email or "")
                password = st.text_input("Password", type="password")
                remember = st.checkbox("Remember me")

                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                with col2:
                    demo = st.form_submit_button("Try Demo", use_container_width=True)

                if submitted:
                    success, error_message = authenticate_user(email, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        if remember:
                            save_session_cookie(email)
                        # Load user preferences
                        load_user_preferences()
                        st.rerun()
                    else:
                        st.error(error_message)

                if demo:
                    st.session_state.demo_mode = True
                    st.session_state.authenticated = True
                    st.session_state.user_email = "demo@investforge.io"
                    st.rerun()

        with tab2:
            with st.form("signup_form"):
                email = st.text_input("Email", value=st.session_state.user_email or "")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")

                # Plan selection
                plan = st.radio(
                    "Choose Your Plan",
                    ["Free - Start Learning", "Growth ($4.99/mo) - Most Popular", "Pro ($9.99/mo) - Advanced"],
                    index=0 if st.session_state.user_plan == 'free' else
                    1 if st.session_state.user_plan == 'growth' else 2
                )

                terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")

                submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

                if submitted:
                    if not terms:
                        st.error("Please accept the terms and conditions.")
                    elif password != confirm_password:
                        st.error("Passwords do not match.")
                    elif len(password) < 8:
                        st.error("Password must be at least 8 characters.")
                    else:
                        with st.spinner("Creating your account..."):
                            if create_user_account(email, password, plan):
                                st.success("Account created successfully! Welcome to InvestForge!")
                                st.session_state.authenticated = True
                                st.session_state.user_email = email
                                st.session_state.show_onboarding = True
                                track_signup(email, plan)
                                # Load user preferences (will be empty for new users)
                                load_user_preferences()
                                st.rerun()
                            # Note: Error messages are now handled by the API client

        # Social login options
        st.markdown("---")
        st.markdown("Or continue with:")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔍 Google", use_container_width=True):
                initiate_google_auth()
        with col2:
            if st.button("🍎 Apple", use_container_width=True):
                initiate_apple_auth()
        with col3:
            if st.button("📧 Email Magic Link", use_container_width=True):
                send_magic_link(email)


# =====================================
# Onboarding Flow
# =====================================

def show_onboarding():
    """Display onboarding flow for new users."""
    st.markdown("## Welcome to InvestForge! 🎉")
    st.markdown("Let's get you started on your investment journey.")

    # Progress bar
    progress = st.progress(0)

    # Step 1: Investment Experience
    with st.container():
        st.markdown("### Step 1: Tell us about your experience")
        experience = st.radio(
            "How would you describe your investment experience?",
            ["Complete beginner 🌱", "Some knowledge 📚", "Intermediate 📈", "Advanced 🚀"]
        )
        progress.progress(25)

    # Step 2: Investment Goals
    with st.container():
        st.markdown("### Step 2: What are your goals?")
        goals = st.multiselect(
            "Select all that apply:",
            ["Learn about investing", "Build long-term wealth", "Generate passive income",
             "Save for retirement", "Short-term trading", "Understand my employer's stock"]
        )
        progress.progress(50)

    # Step 3: Risk Tolerance
    with st.container():
        st.markdown("### Step 3: Risk preference")
        risk = st.slider(
            "How much risk are you comfortable with?",
            1, 10, 5,
            help="1 = Very Conservative, 10 = Very Aggressive"
        )
        progress.progress(75)

    # Step 4: Initial Amount
    with st.container():
        st.markdown("### Step 4: Starting amount")
        amount = st.select_slider(
            "How much are you planning to start with?",
            options=["$0-100", "$100-500", "$500-1,000", "$1,000-5,000", "$5,000+"]
        )
        progress.progress(100)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Complete Setup", type="primary", use_container_width=True):
            # Save preferences
            save_user_preferences(experience, goals, risk, amount)
            st.session_state.onboarding_complete = True
            st.balloons()
            st.success("Setup complete! Let's analyze your first stock.")
            st.rerun()


# =====================================
# Main Application
# =====================================

def main_app():
    """Main application interface."""
    
    # Custom CSS to match landing page design
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
        
        /* Header Styling */
        header[data-testid="stHeader"] {
            background-color: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(0, 0, 0, 0.1);
        }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: var(--bg-secondary);
            border-right: 1px solid rgba(0, 0, 0, 0.1);
        }
        
        section[data-testid="stSidebar"] .element-container {
            padding: 0.5rem 0;
        }
        
        /* Button Styling */
        .stButton > button {
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(255, 107, 53, 0.3);
        }
        
        /* Primary Button Override */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
        }
        
        /* Metric Styling */
        div[data-testid="metric-container"] {
            background-color: var(--bg-secondary);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid rgba(0, 0, 0, 0.05);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }
        
        div[data-testid="metric-container"] label {
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        /* Select Box Styling */
        .stSelectbox > div > div {
            background-color: var(--bg-primary);
            border: 2px solid rgba(0, 78, 137, 0.2);
            border-radius: 8px;
        }
        
        .stSelectbox > div > div:hover {
            border-color: var(--primary-color);
        }
        
        /* Text Input Styling */
        .stTextInput > div > div {
            background-color: var(--bg-primary);
            border: 2px solid rgba(0, 78, 137, 0.2);
            border-radius: 8px;
        }
        
        .stTextInput > div > div:focus-within {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1);
        }
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            background-color: var(--bg-secondary);
            padding: 0.5rem;
            border-radius: 12px;
        }
        
        .stTabs [data-baseweb="tab"] {
            color: var(--text-secondary);
            font-weight: 500;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: white;
            color: var(--primary-color);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }
        
        /* Progress Bar */
        .stProgress > div > div {
            background-color: var(--primary-color);
        }
        
        /* Info/Warning/Error boxes */
        .stAlert {
            border-radius: 12px;
            border: none;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }
        
        /* Expander Styling */
        .streamlit-expanderHeader {
            background-color: var(--bg-secondary);
            border-radius: 8px;
            font-weight: 500;
        }
        
        /* Logo Container */
        .logo-container {
            text-align: center;
            padding: 2rem 0;
        }
        
        .logo-img {
            width: 80px;
            height: 80px;
            object-fit: contain;
            filter: drop-shadow(0 4px 15px rgba(255, 107, 53, 0.3));
            margin-bottom: 1rem;
        }
        
        .brand-text {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        /* Card Styling */
        .feature-card {
            background-color: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(0, 0, 0, 0.05);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .feature-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
        }
        
        /* Hide Streamlit Branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        # Logo and branding
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                st.image("app/static/images/investforge-logo.png", width=100)
            except:
                # Fallback if image not found
                st.markdown("⚒️", unsafe_allow_html=True)
            
            st.markdown("""
            <div style="text-align: center; margin-top: -10px;">
                <span class="brand-text">InvestForge</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown(f"**User:** {st.session_state.user_email}")
        st.markdown(f"**Plan:** {st.session_state.user_plan.title()}")

        if st.session_state.user_plan == 'free':
            analyses_left = 5 - st.session_state.analyses_count
            st.progress(st.session_state.analyses_count / 5)
            st.markdown(f"**Analyses Left:** {analyses_left}/5")

            if analyses_left <= 2:
                st.warning("Running low on analyses! Upgrade to Growth for unlimited access.")
                if st.button("🚀 Upgrade Now", use_container_width=True):
                    show_upgrade_modal()

        st.markdown("---")

        # Navigation
        page = st.selectbox(
            "Navigation",
            ["📊 Analysis", "💼 Portfolio", "📈 Backtesting",
             "🎯 Risk Assessment", "📚 Learn", "⚙️ Settings"]
        )

    # Main content area
    if page == "📊 Analysis":
        show_analysis_page()
    elif page == "💼 Portfolio":
        show_portfolio_page()
    elif page == "📈 Backtesting":
        show_backtesting_page()
    elif page == "🎯 Risk Assessment":
        show_risk_page()
    elif page == "📚 Learn":
        show_education_page()
    elif page == "⚙️ Settings":
        show_settings_page()


def show_analysis_page():
    """Stock analysis page with real AI integration."""
    
    # Enhanced page header with branding
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0 1rem 0;'>
        <h1 style='font-size: 2.5rem; background: linear-gradient(135deg, #FF6B35, #1A759F);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                   font-weight: 700; margin-bottom: 0.5rem;'>
            📊 AI-Powered Stock Analysis
        </h1>
        <p style='color: #7F8C8D; font-size: 1.1rem; margin: 0;'>
            Get comprehensive investment insights powered by multi-agent AI
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load usage on page load
    if 'usage_loaded' not in st.session_state:
        load_user_usage()
        st.session_state.usage_loaded = True
    
    # Check for demo mode
    if st.session_state.demo_mode:
        st.info("🎮 Demo Mode: Explore all features with sample data!")
    
    # Check usage limits
    can_analyze, usage_message = check_usage_limits()
    
    # Show usage info in sidebar
    with st.sidebar:
        if st.session_state.user_plan == 'free':
            st.markdown("### 📊 Usage This Month")
            st.markdown(f"**Analyses:** {st.session_state.analyses_count}/5")
            
            # Progress bar
            progress = st.session_state.analyses_count / 5
            st.progress(progress)
            
            if st.session_state.analyses_count >= 3:
                st.warning("Running low on analyses!")
                if st.button("🚀 Upgrade to Growth", use_container_width=True):
                    show_upgrade_modal()
        else:
            st.success("✨ " + usage_message)
    
    # Main analysis interface
    if not can_analyze:
        st.error(f"""
        ### 🚫 {usage_message}
        
        Upgrade to Growth plan for unlimited analyses and advanced features!
        """)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Upgrade to Growth - $4.99/mo", type="primary", use_container_width=True):
                initiate_payment('growth')
        return
    
    # Stock input
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ticker = st.text_input(
            "Enter Stock Symbol",
            value="AAPL" if st.session_state.demo_mode else "",
            placeholder="e.g., AAPL, GOOGL, TSLA",
            help="Enter a valid stock ticker symbol"
        ).upper()
    
    with col2:
        analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)
    
    # Run analysis
    if analyze_button and ticker:
        run_ai_analysis(ticker)
    
    # Display stored results
    if f'analysis_result_{ticker}' in st.session_state:
        display_analysis_results(ticker)


# =====================================
# Helper Functions
# =====================================

def authenticate_user(email: str, password: str) -> tuple[bool, str]:
    """Authenticate user credentials using API."""
    result = api_client.login(email, password)
    
    if result is None:
        return False, "Unable to connect to authentication service"
    
    if isinstance(result, dict) and result.get('error'):
        return False, result.get('message', 'Authentication failed')
    
    return True, ""


def create_user_account(email: str, password: str, plan: str) -> bool:
    """Create new user account using API."""
    result = api_client.signup(email, password, plan=plan)
    return result is not None


def load_user_preferences():
    """Load user preferences from API."""
    if st.session_state.user_email:
        preferences = api_client.get_user_preferences(st.session_state.user_email)
        if preferences:
            st.session_state.user_preferences = preferences
            return preferences
    return None


def save_user_preferences(experience, goals, risk, amount):
    """Save user onboarding preferences."""
    preferences = {
        'experience': experience,
        'goals': goals,
        'risk_tolerance': risk,
        'initial_amount': amount,
        'timestamp': datetime.now().isoformat()
    }
    
    # Save to session state
    st.session_state.user_preferences = preferences
    
    # Save to database via API
    if st.session_state.user_email:
        success = api_client.save_user_preferences(st.session_state.user_email, preferences)
        if success:
            st.success("✅ Preferences saved successfully!")
            
            # Track preferences completion
            user_data = st.session_state.get('user_data', {})
            user_id = user_data.get('user_id')
            if user_id:
                api_client.track_preferences_event(user_id, preferences)
                api_client.increment_feature_usage(user_id, 'onboarding_completed', 1)
        else:
            st.warning("⚠️ Preferences saved locally but couldn't sync to server")


def track_signup(email: str, plan: str):
    """Track user signup for analytics."""
    # Implement analytics tracking
    pass


def track_referral(source: str):
    """Track referral source."""
    # Implement referral tracking
    pass


def initiate_payment(plan: str):
    """Initiate Stripe payment flow."""
    # Implement Stripe checkout
    st.info(f"Redirecting to payment for {plan} plan...")


def show_upgrade_modal():
    """Show upgrade modal."""
    st.markdown("""
    ### 🚀 Upgrade to Growth

    **Unlock unlimited analyses and advanced features:**
    - ✅ Unlimited stock analyses
    - ✅ Portfolio optimization
    - ✅ Risk simulations
    - ✅ Backtesting strategies
    - ✅ Priority support

    **Only $4.99/month** (Less than a coffee!)
    """)

    if st.button("Upgrade Now", type="primary"):
        initiate_payment('growth')


# =====================================
# Usage Tracking Functions
# =====================================

def load_user_usage():
    """Load user's current month usage from API."""
    if not st.session_state.user_data:
        return
    
    user_id = st.session_state.user_data.get('user_id')
    if not user_id:
        return
    
    try:
        usage = api_client.get_user_usage(user_id)
        if usage:
            st.session_state.monthly_usage = usage.get('usage', {})
            st.session_state.analyses_count = st.session_state.monthly_usage.get('analyses_count', 0)
            logger.info(f"Loaded usage for user {user_id}: {st.session_state.analyses_count} analyses")
    except Exception as e:
        logger.error(f"Failed to load usage: {e}")
        st.session_state.monthly_usage = {}
        st.session_state.analyses_count = 0


def check_usage_limits() -> Tuple[bool, str]:
    """Check if user has reached their usage limits."""
    if st.session_state.demo_mode:
        return True, ""
    
    if st.session_state.user_plan == 'free':
        limit = 5
        current = st.session_state.analyses_count
        
        if current >= limit:
            return False, f"You've reached your monthly limit of {limit} analyses."
        else:
            remaining = limit - current
            return True, f"{remaining} analyses remaining this month"
    
    # Growth and Pro plans have unlimited analyses
    return True, "Unlimited analyses"


def increment_usage(feature: str = 'analyses_count'):
    """Increment usage counter and update in database."""
    if st.session_state.demo_mode:
        return
    
    user_id = st.session_state.user_data.get('user_id')
    if not user_id:
        return
    
    try:
        # Update local counter immediately for responsive UI
        if feature == 'analyses_count':
            st.session_state.analyses_count += 1
        
        # Update in database
        success = api_client.increment_feature_usage(user_id, feature, 1)
        if success:
            logger.info(f"Incremented {feature} usage for user {user_id}")
        else:
            logger.error(f"Failed to increment {feature} usage")
    except Exception as e:
        logger.error(f"Error incrementing usage: {e}")


# =====================================
# AI Analysis Functions
# =====================================

def run_ai_analysis(ticker: str):
    """Run the actual AI crew analysis."""
    
    with ErrorBoundary("Failed to complete analysis"):
        # Track usage immediately (optimistic update)
        if st.session_state.user_plan == 'free' and not st.session_state.demo_mode:
            increment_usage('analyses_count')
        
        # Create progress container
        progress_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize crew
            status_text.text("🤖 Initializing AI agents...")
            progress_bar.progress(10)
            
            try:
                # Import crew dynamically to handle import errors
                from crew import create_crew, run_analysis
                
                # Phase 1: Create crew
                status_text.text("🔧 Creating specialized AI crew...")
                progress_bar.progress(20)
                
                # Phase 2: Run analysis
                status_text.text(f"📊 Analyzing {ticker}...")
                progress_bar.progress(30)
                
                # Track analysis start
                user_id = st.session_state.user_data.get('user_id')
                if user_id:
                    api_client.track_analysis_event(user_id, ticker, "standard")
                
                # Run the actual analysis
                with st.spinner(f"AI agents working on {ticker} analysis..."):
                    result = run_analysis(ticker)
                
                # Phase 3: Process results
                status_text.text("📝 Processing analysis results...")
                progress_bar.progress(70)
                
                # Parse and structure the results
                analysis_data = parse_crew_results(result, ticker)
                
                # Phase 4: Store results
                status_text.text("💾 Saving analysis...")
                progress_bar.progress(90)
                
                # Store in session state
                st.session_state[f'analysis_result_{ticker}'] = {
                    'ticker': ticker,
                    'timestamp': datetime.now(),
                    'depth': depth,
                    'data': analysis_data,
                    'raw_result': result
                }
                
                # Add to history
                st.session_state.analysis_history.append({
                    'ticker': ticker,
                    'timestamp': datetime.now().isoformat(),
                    'depth': depth
                })
                
                # Complete
                progress_bar.progress(100)
                status_text.text("✅ Analysis complete!")
                
                # Clear progress after 1 second
                import time
                time.sleep(1)
                progress_container.empty()
                
                # Show success message
                st.success(f"✅ Analysis complete for **{ticker}**!")
                st.balloons()
                
            except ImportError as e:
                logger.error(f"Import error: {e}")
                # Fall back to mock analysis if crew import fails
                status_text.text("⚠️ Using simplified analysis...")
                progress_bar.progress(100)
                
                mock_data = generate_mock_analysis(ticker)
                st.session_state[f'analysis_result_{ticker}'] = {
                    'ticker': ticker,
                    'timestamp': datetime.now(),
                    'depth': depth,
                    'data': mock_data,
                    'raw_result': None
                }
                
                progress_container.empty()
                st.warning("Using simplified analysis. Full AI analysis requires additional setup.")


def parse_crew_results(result, ticker: str) -> Dict[str, Any]:
    """Parse the crew analysis results into structured data."""
    
    # Convert CrewOutput to structured format
    if hasattr(result, 'tasks_output'):
        tasks = result.tasks_output
        
        # Extract data from each agent's output
        research_data = str(tasks[0]) if len(tasks) > 0 else ""
        sentiment_data = str(tasks[1]) if len(tasks) > 1 else ""
        analysis_data = str(tasks[2]) if len(tasks) > 2 else ""
        strategy_data = str(tasks[3]) if len(tasks) > 3 else ""
        
        return {
            'research': research_data,
            'sentiment': sentiment_data,
            'analysis': analysis_data,
            'strategy': strategy_data,
            'full_result': str(result)
        }
    else:
        # Fallback for different result format
        return {
            'research': "",
            'sentiment': "",
            'analysis': "",
            'strategy': "",
            'full_result': str(result)
        }


def generate_mock_analysis(ticker: str) -> Dict[str, Any]:
    """Generate mock analysis data for demo/fallback."""
    
    try:
        # Get real data from yfinance
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1mo")
        
        current_price = hist['Close'].iloc[-1] if not hist.empty else 100
        price_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100) if not hist.empty else 5.2
        
        return {
            'overview': {
                'current_price': current_price,
                'price_change': price_change,
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'volume': hist['Volume'].iloc[-1] if not hist.empty else 0,
                'week_52_high': info.get('fiftyTwoWeekHigh', 0),
                'week_52_low': info.get('fiftyTwoWeekLow', 0)
            },
            'technical': {
                'rsi': 55.5,
                'macd': 'Bullish',
                'sma_20': current_price * 0.98,
                'sma_50': current_price * 0.95,
                'support': current_price * 0.93,
                'resistance': current_price * 1.05
            },
            'fundamental': {
                'revenue': info.get('totalRevenue', 0),
                'profit_margin': info.get('profitMargins', 0),
                'roe': info.get('returnOnEquity', 0),
                'debt_to_equity': info.get('debtToEquity', 0)
            },
            'ai_insights': "Based on technical and fundamental analysis, this stock shows moderate growth potential with balanced risk factors."
        }
    except Exception as e:
        logger.error(f"Error generating mock data: {e}")
        return {
            'overview': {},
            'technical': {},
            'fundamental': {},
            'ai_insights': "Analysis data temporarily unavailable."
        }


# =====================================
# Landing Page Integration Functions
# =====================================

def save_session_cookie(email: str):
    """Save session cookie for remember me functionality."""
    # In production, use proper session management
    st.session_state.remembered_email = email


def send_magic_link(email: str):
    """Send magic link for passwordless login."""
    if email:
        st.info(f"Magic link sent to {email}! Check your inbox.")
        # Implement actual magic link sending
    else:
        st.error("Please enter your email address.")


def initiate_google_auth():
    """Initiate Google OAuth flow."""
    # Implement Google OAuth
    st.info("Redirecting to Google login...")


def initiate_apple_auth():
    """Initiate Apple Sign In flow."""
    # Implement Apple Sign In
    st.info("Redirecting to Apple login...")


# =====================================
# Display Functions
# =====================================

def display_analysis_results(ticker: str):
    """Display the analysis results in organized tabs."""
    result_data = st.session_state.get(f'analysis_result_{ticker}')
    if not result_data:
        return
    
    # Show timestamp
    timestamp = result_data['timestamp']
    st.caption(f"Analysis completed at {timestamp.strftime('%I:%M %p on %B %d, %Y')}")
    
    # Create tabs for results
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Technical", "💰 Fundamental", "🤖 AI Insights"])
    
    data = result_data['data']
    
    with tab1:
        display_overview_tab(ticker, data)
    
    with tab2:
        display_technical_tab(ticker, data)
    
    with tab3:
        display_fundamental_tab(ticker, data)
    
    with tab4:
        display_ai_insights_tab(ticker, data)
    
    # Export options
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        if st.button("📥 Export as PDF", use_container_width=True):
            st.info("PDF export coming soon!")
    with col3:
        if st.button("📤 Share Analysis", use_container_width=True):
            st.info("Sharing feature coming soon!")


def display_overview_tab(ticker: str, data: Dict[str, Any]):
    """Display overview metrics with real or mock data."""
    
    st.markdown("### Stock Overview")
    
    # Try to get real data first
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1mo")
        
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            price_change = current_price - prev_close
            price_change_pct = (price_change / prev_close) * 100
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Current Price",
                    f"${current_price:.2f}",
                    f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
                )
            
            with col2:
                market_cap = info.get('marketCap', 0)
                if market_cap:
                    if market_cap > 1e12:
                        cap_str = f"${market_cap/1e12:.2f}T"
                    elif market_cap > 1e9:
                        cap_str = f"${market_cap/1e9:.2f}B"
                    else:
                        cap_str = f"${market_cap/1e6:.2f}M"
                else:
                    cap_str = "N/A"
                st.metric("Market Cap", cap_str)
            
            with col3:
                pe_ratio = info.get('trailingPE', 0)
                st.metric("P/E Ratio", f"{pe_ratio:.2f}" if pe_ratio else "N/A")
            
            with col4:
                volume = hist['Volume'].iloc[-1]
                if volume > 1e6:
                    vol_str = f"{volume/1e6:.1f}M"
                else:
                    vol_str = f"{volume/1e3:.1f}K"
                st.metric("Volume", vol_str)
            
            # Price chart
            st.markdown("#### Price Chart (1 Month)")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist['Close'],
                mode='lines',
                name='Close Price',
                line=dict(color='#FF6B35', width=2)
            ))
            fig.update_layout(
                height=400,
                showlegend=False,
                hovermode='x unified',
                yaxis_title="Price ($)",
                xaxis_title=""
            )
            st.plotly_chart(fig, use_container_width=True)
            
    except Exception as e:
        logger.error(f"Error displaying overview: {e}")
        st.error("Unable to load real-time data. Please try again.")


def display_technical_tab(ticker: str, data: Dict[str, Any]):
    """Display technical analysis results."""
    
    st.markdown("### Technical Analysis")
    
    # Check if we have real crew analysis data
    if 'research' in data and data['research']:
        st.markdown(data['research'])
    else:
        # Display mock technical indicators
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Key Indicators")
            st.info("""
            • **RSI (14):** 55.5 - Neutral
            • **MACD:** Bullish crossover
            • **Bollinger Bands:** Price near middle band
            • **Volume Trend:** Increasing
            """)
        
        with col2:
            st.markdown("#### Support & Resistance")
            st.info("""
            • **Strong Support:** $145.00
            • **Support:** $148.50
            • **Resistance:** $155.00
            • **Strong Resistance:** $158.00
            """)
        
        # Chart patterns
        st.markdown("#### Chart Patterns Detected")
        st.success("📈 Ascending triangle pattern forming - Bullish signal")


def display_fundamental_tab(ticker: str, data: Dict[str, Any]):
    """Display fundamental analysis results."""
    
    st.markdown("### Fundamental Analysis")
    
    # Check if we have real crew analysis data
    if 'analysis' in data and data['analysis']:
        st.markdown(data['analysis'])
    else:
        try:
            # Get real fundamental data
            stock = yf.Ticker(ticker)
            info = stock.info
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Financial Metrics")
                metrics = {
                    "Revenue (TTM)": info.get('totalRevenue', 0),
                    "Profit Margin": info.get('profitMargins', 0),
                    "Operating Margin": info.get('operatingMargins', 0),
                    "ROE": info.get('returnOnEquity', 0),
                    "ROA": info.get('returnOnAssets', 0)
                }
                
                for metric, value in metrics.items():
                    if value:
                        if "Margin" in metric or "ROE" in metric or "ROA" in metric:
                            st.write(f"**{metric}:** {value:.2%}")
                        else:
                            st.write(f"**{metric}:** ${value/1e9:.2f}B")
                    else:
                        st.write(f"**{metric}:** N/A")
            
            with col2:
                st.markdown("#### Valuation Ratios")
                ratios = {
                    "P/E Ratio": info.get('trailingPE', 0),
                    "Forward P/E": info.get('forwardPE', 0),
                    "P/B Ratio": info.get('priceToBook', 0),
                    "PEG Ratio": info.get('pegRatio', 0),
                    "EV/EBITDA": info.get('enterpriseToEbitda', 0)
                }
                
                for ratio, value in ratios.items():
                    if value:
                        st.write(f"**{ratio}:** {value:.2f}")
                    else:
                        st.write(f"**{ratio}:** N/A")
                        
        except Exception as e:
            logger.error(f"Error displaying fundamentals: {e}")
            st.info("Fundamental data analysis in progress...")


def display_ai_insights_tab(ticker: str, data: Dict[str, Any]):
    """Display AI-generated insights and recommendations."""
    
    st.markdown("### AI Analysis & Insights")
    
    # Check if we have real crew strategy data
    if 'strategy' in data and data['strategy']:
        st.markdown(data['strategy'])
    
    # Show sentiment if available
    if 'sentiment' in data and data['sentiment']:
        st.markdown("#### Market Sentiment")
        st.markdown(data['sentiment'])
    
    # Show full analysis if no specific sections
    if 'full_result' in data and data['full_result'] and not data.get('strategy'):
        st.markdown(data['full_result'])
    
    # Add investment recommendation section
    st.markdown("#### 🎯 Investment Recommendation")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("""
        **Short-term (1-3 months)**
        • Signal: HOLD
        • Target: $158
        • Stop Loss: $145
        """)
    
    with col2:
        st.success("""
        **Medium-term (3-12 months)**
        • Signal: BUY
        • Target: $175
        • Stop Loss: $140
        """)
    
    with col3:
        st.success("""
        **Long-term (1+ years)**
        • Signal: STRONG BUY
        • Target: $200+
        • Risk: Moderate
        """)


# Deprecated functions for backwards compatibility
def display_overview(ticker: str):
    """Display stock overview (deprecated - use display_overview_tab)."""
    display_overview_tab(ticker, {})


def display_technical_analysis(ticker: str):
    """Display technical analysis (deprecated - use display_technical_tab)."""
    display_technical_tab(ticker, {})


def display_fundamental_analysis(ticker: str):
    """Display fundamental analysis (deprecated - use display_fundamental_tab)."""
    display_fundamental_tab(ticker, {})


def display_ai_insights(ticker: str):
    """Display AI-generated insights (deprecated - use display_ai_insights_tab)."""
    display_ai_insights_tab(ticker, {})


def show_portfolio_page():
    """Portfolio management page."""
    st.title("Portfolio Optimization")

    if st.session_state.user_plan == 'free':
        st.warning("Portfolio optimization is a Growth feature. Upgrade to access!")
        return

    # Portfolio interface here


def show_backtesting_page():
    """Backtesting page."""
    st.title("Strategy Backtesting")

    if st.session_state.user_plan == 'free':
        st.warning("Backtesting is a Growth feature. Upgrade to access!")
        return

    # Backtesting interface here


def show_risk_page():
    """Risk assessment page."""
    st.title("Risk Assessment")
    # Risk assessment interface here


def show_education_page():
    """Educational content page."""
    st.title("Learn Investing")
    st.markdown("### Start your investment education journey")
    # Educational content here


def show_settings_page():
    """User settings page."""
    st.title("Settings")

    tab1, tab2, tab3 = st.tabs(["Profile", "Subscription", "Preferences"])

    with tab1:
        st.markdown("### Profile Settings")
        # Profile settings here

    with tab2:
        st.markdown("### Subscription Management")
        st.info(f"Current Plan: **{st.session_state.user_plan.title()}**")

        if st.session_state.user_plan != 'pro':
            if st.button("Upgrade Plan"):
                show_upgrade_modal()

    with tab3:
        st.markdown("### Preferences")
        # User preferences here


# =====================================
# Main Execution
# =====================================

if __name__ == "__main__":
    # Initialize session state
    init_session_state()

    # Process URL parameters from landing page
    process_url_params()

    # Show appropriate interface
    if not st.session_state.authenticated:
        show_login_signup()
    elif st.session_state.get('show_onboarding') and not st.session_state.onboarding_complete:
        show_onboarding()
    else:
        main_app()