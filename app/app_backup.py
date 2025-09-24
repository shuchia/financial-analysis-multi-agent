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
from typing import Optional, Dict
import plotly.graph_objects as go
from utils.api_client import api_client

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
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='font-size: 3rem; background: linear-gradient(135deg, #FF6B35, #004E89);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                ⚒️ InvestForge
            </h1>
            <p style='color: #666; font-size: 1.2rem;'>Forge Your Financial Future</p>
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
                    if authenticate_user(email, password):
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        if remember:
                            save_session_cookie(email)
                        # Load user preferences
                        load_user_preferences()
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")

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

    # Sidebar
    with st.sidebar:
        st.markdown(f"### ⚒️ InvestForge")
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
    """Stock analysis page."""
    st.title("Stock Analysis")

    # Check for demo mode restrictions
    if st.session_state.demo_mode:
        st.info("🎮 Demo Mode: Explore all features with sample data!")

    # Check analysis limit for free users
    if st.session_state.user_plan == 'free' and st.session_state.analyses_count >= 5:
        st.error("You've reached your monthly analysis limit.")
        st.markdown("### Upgrade to Growth for unlimited analyses!")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Upgrade to Growth - $4.99/mo", type="primary", use_container_width=True):
                initiate_payment('growth')
        return

    # Analysis interface
    col1, col2 = st.columns([3, 1])

    with col1:
        ticker = st.text_input(
            "Enter Stock Symbol",
            value="AAPL" if st.session_state.demo_mode else "",
            placeholder="e.g., AAPL, GOOGL, TSLA"
        )

    with col2:
        analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)

    if analyze_button and ticker:
        # Increment analysis count for free users
        if st.session_state.user_plan == 'free' and not st.session_state.demo_mode:
            st.session_state.analyses_count += 1

        # Show analysis results
        with st.spinner("AI agents analyzing {}...".format(ticker)):
            # Here you would call your actual analysis functions
            # For now, showing placeholder
            st.success(f"Analysis complete for {ticker}!")

            # Display results in tabs
            tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Technical", "Fundamental", "AI Insights"])

            with tab1:
                display_overview(ticker)
            with tab2:
                display_technical_analysis(ticker)
            with tab3:
                display_fundamental_analysis(ticker)
            with tab4:
                display_ai_insights(ticker)


# =====================================
# Helper Functions
# =====================================

def authenticate_user(email: str, password: str) -> bool:
    """Authenticate user credentials using API."""
    result = api_client.login(email, password)
    return result is not None


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

def display_overview(ticker: str):
    """Display stock overview."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Current Price", "$150.25", "+2.3%")
    with col2:
        st.metric("Market Cap", "$2.5T", "+5.2%")
    with col3:
        st.metric("P/E Ratio", "28.5", "-1.2%")
    with col4:
        st.metric("Volume", "52.3M", "+15%")

    # Price chart
    st.markdown("### Price Chart")
    # Add actual chart here


def display_technical_analysis(ticker: str):
    """Display technical analysis."""
    st.markdown("### Technical Indicators")
    # Add technical analysis content


def display_fundamental_analysis(ticker: str):
    """Display fundamental analysis."""
    st.markdown("### Fundamental Metrics")
    # Add fundamental analysis content


def display_ai_insights(ticker: str):
    """Display AI-generated insights."""
    st.markdown("### AI Analysis")
    st.info("🤖 Our AI agents have analyzed this stock from multiple angles...")
    # Add AI insights content


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