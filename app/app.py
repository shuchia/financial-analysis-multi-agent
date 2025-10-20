# =====================================
# File: app.py - Enhanced with landing page integration
# =====================================

import streamlit as st
import pandas as pd
import numpy as np
import re
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
from components.analysis import render_analysis_page
from components.fractional_analysis import render_fractional_analysis_page
from components.save_portfolio_dialog import render_save_button, show_save_portfolio_dialog
import traceback
import logging
from utils.portfolio_parser import parse_portfolio_output, validate_portfolio_data
from utils.risk_parser import parse_risk_output
from tools.risk_assessment_tool import risk_assessment
from tools.portfolio_optimization_tool import PortfolioOptimizationTool
from quant_crew import QuantitativeAnalysisCrew
import asyncio
import threading
import portfoliocrew
from portfoliocrew import interpret_optimized_portfolio

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

def load_custom_css():
    """Load custom CSS to match landing page styling"""
    try:
        with open("app/static/css/custom.css", "r") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # Fallback inline CSS with key branding elements
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        :root {
            --primary-color: #FF6B35;
            --secondary-color: #004E89;
            --accent-color: #1A759F;
            --text-primary: #2C3E50;
            --text-secondary: #7F8C8D;
            --bg-primary: #FFFFFF;
            --bg-secondary: #F8F9FA;
            --border-color: #E1E8ED;
            --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        .stApp {
            font-family: var(--font-family) !important;
        }
        
        .gradient-text {
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 700;
        }
        
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            color: white;
            border: none;
            border-radius: 8px;
        }
        </style>
        """, unsafe_allow_html=True)

# Load custom CSS
load_custom_css()

def get_logo_base64():
    """Get InvestForge logo as base64 string"""
    import base64
    import os
    # Try multiple possible paths (local dev vs Docker container)
    possible_paths = [
        "static/images/investforge-logo.png",  # Docker container path
        "app/static/images/investforge-logo.png",  # Local dev path
        "assets/images/investforge-logo.png",  # Alternative path
    ]

    for path in possible_paths:
        try:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    logo_data = f.read()
                return base64.b64encode(logo_data).decode()
        except:
            continue

    return ""  # Return empty string if no logo found

def render_investforge_header(title="InvestForge", subtitle="Forge Your Financial Future with AI", center=True):
    """Render consistent InvestForge header with logo and branding"""
    logo_b64 = get_logo_base64()
    center_style = "text-align: center;" if center else ""

    if logo_b64:
        st.markdown(f"""
        <div style='{center_style} padding: 2rem 0;'>
            <img src='data:image/png;base64,{logo_b64}' style='height: 60px; margin-bottom: 1rem;' alt='InvestForge Logo'>
            <h1 class='gradient-text' style='font-size: 2.5rem; margin: 0.5rem 0;'>{title}</h1>
            <p style='color: var(--text-secondary); font-size: 1.2rem; margin: 0;'>{subtitle}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='{center_style} padding: 2rem 0;'>
            <div style='font-size: 3rem; margin-bottom: 1rem;'>⚒️</div>
            <h1 class='gradient-text' style='font-size: 2.5rem; margin: 0.5rem 0;'>{title}</h1>
            <p style='color: var(--text-secondary); font-size: 1.2rem; margin: 0;'>{subtitle}</p>
        </div>
        """, unsafe_allow_html=True)


# =====================================
# SIDEBAR CODE - COMMENTED OUT FOR HORIZONTAL NAV
# =====================================
# def render_sidebar():
#     """Render InvestForge sidebar with logo and navigation"""
#     with st.sidebar:
#         # Logo
#         logo_b64 = get_logo_base64()
#         if logo_b64:
#             st.markdown(f"""
#             <div style='text-align: center; padding: 1rem 0 0.5rem 0;'>
#                 <img src='data:image/png;base64,{logo_b64}' style='height: 50px; margin-bottom: 0.5rem;' alt='InvestForge Logo'>
#                 <h2 class='gradient-text' style='font-size: 1.5rem; margin: 0;'>InvestForge</h2>
#                 <p style='color: var(--text-secondary); font-size: 0.85rem; margin: 0.25rem 0;'>AI-Powered Investing</p>
#             </div>
#             """, unsafe_allow_html=True)
#         else:
#             st.markdown("""
#             <div style='text-align: center; padding: 1rem 0;'>
#                 <div style='font-size: 2rem; margin-bottom: 0.5rem;'>⚒️</div>
#                 <h2 class='gradient-text' style='font-size: 1.5rem; margin: 0;'>InvestForge</h2>
#                 <p style='color: var(--text-secondary); font-size: 0.85rem; margin: 0.25rem 0;'>AI-Powered Investing</p>
#             </div>
#             """, unsafe_allow_html=True)
#
#         st.markdown("---")
#
#         # Navigation menu
#         st.markdown("### 🧭 Navigation")
#
#         if st.button("💼 My Portfolio", use_container_width=True, type="secondary"):
#             st.session_state.show_portfolio_generation = True
#             st.session_state.show_portfolio_results = False
#             st.session_state.show_main_app = False
#             st.rerun()
#
#         if st.button("📊 Analyze Stocks", use_container_width=True, type="secondary"):
#             st.session_state.show_main_app = True
#             st.session_state.show_portfolio_generation = False
#             st.session_state.show_portfolio_results = False
#             st.rerun()
#
#         st.markdown("---")
#
#         # User info
#         if st.session_state.get('authenticated'):
#             st.markdown("### 👤 Account")
#             st.markdown(f"**Email:** {st.session_state.user_email}")
#             st.markdown(f"**Plan:** {st.session_state.user_plan.title()}")
#
#             # Usage info for free users
#             if st.session_state.user_plan == 'free':
#                 st.markdown("---")
#                 st.markdown("### 📊 Usage")
#                 st.markdown(f"**Analyses:** {st.session_state.analyses_count}/5")
#                 progress = st.session_state.analyses_count / 5
#                 st.progress(progress)
#                 if st.session_state.analyses_count >= 5:
#                     st.warning("⚠️ Limit reached")
#                     if st.button("⬆️ Upgrade", use_container_width=True, type="primary"):
#                         st.info("Upgrade feature coming soon!")
#
#             st.markdown("---")
#
#             if st.button("🚪 Logout", use_container_width=True):
#                 st.session_state.authenticated = False
#                 st.session_state.user_email = None
#                 st.rerun()


def render_horizontal_nav():
    """Render horizontal navigation bar at the top"""
    # Get logo
    logo_b64 = get_logo_base64()

    # Navbar styling with fixed widths to prevent wrapping
    st.markdown("""
    <style>
    /* Hide default Streamlit header */
    header[data-testid="stHeader"] {
        display: none;
    }

    /* Streamlit button styling for navbar */
    .stButton button {
        white-space: nowrap !important;
        padding: 0.375rem 0.75rem !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        min-width: fit-content !important;
    }

    /* Fix column gaps */
    [data-testid="column"] {
        padding: 0 0.25rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Create navbar with better column proportions
    cols = st.columns([1.2, 0.7, 0.7, 0.7, 0.7, 0.7, 2, 0.8, 0.4])

    with cols[0]:
        if logo_b64:
            st.markdown(f"""
            <div style='display: flex; align-items: center; gap: 0.5rem; color: #2C3E50; font-weight: 600; padding-top: 0.25rem;'>
                <img src='data:image/png;base64,{logo_b64}' style='height: 28px;' alt='InvestForge'>
                <span>InvestForge</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='color: #2C3E50; font-weight: 600; padding-top: 0.25rem;'>⚒️ InvestForge</div>
            """, unsafe_allow_html=True)

    with cols[1]:
        if st.button("🏠 Portfolio", key="nav_portfolio", use_container_width=True):
            # Reset all nav flags and route to portfolio dashboard
            st.session_state.show_main_app = False
            st.session_state.show_portfolio_generation = False
            st.session_state.show_portfolio_results = False
            st.session_state.show_portfolio_landing = False
            # Route based on user's portfolio status
            route_after_login()
            st.rerun()

    with cols[2]:
        if st.button("👁 Watchlist", key="nav_watchlist", use_container_width=True):
            st.info("Watchlist feature coming soon!")

    with cols[3]:
        if st.button("🔍 Analyze Stocks", key="nav_discover", use_container_width=True):
            # Goes to stock analysis (old main app)
            st.session_state.show_main_app = True
            st.session_state.show_portfolio_generation = False
            st.session_state.show_portfolio_results = False
            st.session_state.show_portfolio_landing = False
            st.rerun()

    with cols[4]:
        if st.button("📚 Learn", key="nav_learn", use_container_width=True):
            st.info("Educational resources coming soon!")

    with cols[5]:
        if st.button("💰 Budget", key="nav_budget", use_container_width=True):
            st.info("Budget planning feature coming soon!")

    with cols[6]:
        search_query = st.text_input("🔍 Search", placeholder="Search companies...", label_visibility="collapsed", key="nav_search")

    with cols[7]:
        if st.button("⬆️ Upgrade", key="nav_upgrade", type="primary", use_container_width=True):
            st.info("Upgrade feature coming soon!")

    with cols[8]:
        # User dropdown
        if st.session_state.get('authenticated'):
            user_menu = st.selectbox(
                "user",
                ["👤", "Account", "Settings", "Logout"],
                label_visibility="collapsed",
                key="nav_user_dropdown"
            )

            if user_menu == "Account":
                st.info(f"Logged in as: {st.session_state.user_email}")
            elif user_menu == "Logout":
                st.session_state.authenticated = False
                st.session_state.user_email = None
                st.rerun()
        else:
            st.markdown("<div style='text-align: center; padding-top: 0.25rem;'>👤</div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin: 0; border: none; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)


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
    if 'show_onboarding' not in st.session_state:
        st.session_state.show_onboarding = False
    if 'show_portfolio_generation' not in st.session_state:
        st.session_state.show_portfolio_generation = False
    if 'show_portfolio_results' not in st.session_state:
        st.session_state.show_portfolio_results = False
    if 'show_portfolio_landing' not in st.session_state:
        st.session_state.show_portfolio_landing = False
    if 'latest_portfolio' not in st.session_state:
        st.session_state.latest_portfolio = None
    if 'current_portfolio_id' not in st.session_state:
        st.session_state.current_portfolio_id = None
    if 'show_main_app' not in st.session_state:
        st.session_state.show_main_app = False


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
        
        /* Style input fields to match landing page */
        .stTextInput > div > div > input {
            border: 2px solid #e9ecef;
            border-radius: 12px;
            padding: 16px;
            font-family: 'Inter', sans-serif;
            font-size: 16px;
            transition: all 0.3s ease;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        
        .stTextInput > div > div > input:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1);
            outline: none;
        }
        
        /* Style buttons to match landing page */
        .stButton > button {
            border-radius: 12px;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            padding: 12px 24px;
            transition: all 0.3s ease;
            border: none;
        }
        
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            color: white;
        }
        
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(255, 107, 53, 0.3);
        }
        
        /* Style form containers */
        .stForm {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Logo and branding
        render_investforge_header()

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
                        # Load user preferences and route to appropriate page
                        load_user_preferences()
                        route_after_login()
                        st.rerun()
                    else:
                        st.error(error_message)

                if demo:
                    st.session_state.demo_mode = True
                    st.session_state.authenticated = True
                    st.session_state.user_email = "demo@investforge.io"
                    st.rerun()
            
        # Forgot password link (moved outside tab to avoid form context issues)
        if st.button("Forgot Password?", type="secondary", use_container_width=True):
            st.session_state.show_forgot_password = True
            st.rerun()

        with tab2:
            with st.form("signup_form"):
                email = st.text_input("Email", value=st.session_state.user_email or "")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")

                # Default to free plan (no selection needed)
                plan = "Free - Start Learning"

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
                                track_signup(email, plan)
                                # Load user preferences and route to appropriate page
                                load_user_preferences()
                                route_after_login()
                                st.rerun()
                            # Note: Error messages are now handled by the API client

        # Social login options removed for cleaner experience


# =====================================
# Forgot Password Flow
# =====================================

def show_forgot_password():
    """Display forgot password interface."""
    
    # Apply the same custom CSS
    st.markdown("""
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            min-height: 100vh;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Logo and branding
        render_investforge_header("Reset Your Password", "Enter your email to receive a password reset link")

        with st.form("forgot_password_form"):
            email = st.text_input("Email Address", placeholder="your@email.com")
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Send Reset Link", use_container_width=True, type="primary")
            with col2:
                cancel = st.form_submit_button("Back to Login", use_container_width=True)
            
            if submit and email:
                # For now, show a placeholder message
                # TODO: Implement actual password reset API call
                st.success(f"If an account exists with {email}, you will receive a password reset link shortly.")
                st.info("📧 Please check your email (including spam folder) for the reset link.")
                st.info("🔗 The reset link will expire in 1 hour for security.")
                
            elif submit and not email:
                st.error("Please enter your email address.")
                
            if cancel:
                st.session_state.show_forgot_password = False
                st.rerun()


# =====================================
# Onboarding Flow
# =====================================

def get_investment_amount_options(age_range: str) -> list:
    """Return investment amount options based on age range (as proxy for income/capacity)."""
    
    # Base amounts that work for most people
    base_options = [
        "$25 - Just getting started",
        "$50 - Small but steady start", 
        "$100 - Beginner friendly",
        "$250 - Ready to learn",
        "$500 - Serious about investing",
        "$1,000 - Confident starter",
        "$2,500 - Experienced beginner",
        "$5,000 - Substantial commitment",
        "$10,000+ - Experienced investor"
    ]
    
    # Adjust options based on age (younger = smaller suggested amounts)
    if "16-20" in age_range or "21-25" in age_range:
        # College/early career - emphasize smaller amounts
        return [
            "$10 - Perfect for learning",
            "$25 - Great starting point",
            "$50 - Building habits", 
            "$100 - Solid foundation",
            "$250 - Getting serious",
            "$500 - Strong commitment",
            "$1,000 - Advanced starter",
            "$2,500+ - High confidence"
        ]
    elif "26-30" in age_range or "31-35" in age_range:
        # Career building - moderate amounts
        return base_options
    else:
        # 36+ Established career - can handle larger amounts
        return [
            "$100 - Conservative start",
            "$250 - Testing the waters",
            "$500 - Steady approach", 
            "$1,000 - Confident beginner",
            "$2,500 - Serious investor",
            "$5,000 - Substantial start",
            "$10,000 - Major commitment",
            "$25,000+ - Experienced investor"
        ]


def show_portfolio_generation_overlay():
    """Display loading overlay while generating portfolio."""
    st.markdown("""
    <style>
        /* Full-screen overlay */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(248, 249, 250, 0.98);
            backdrop-filter: blur(10px);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Loading content container */
        .loading-content {
            text-align: center;
            padding: 3rem;
            background: white;
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            max-width: 500px;
            border: 2px solid #E1E8ED;
        }

        /* Animated spinner */
        .spinner {
            width: 80px;
            height: 80px;
            margin: 0 auto 2rem;
            border: 6px solid #f3f3f3;
            border-top: 6px solid #FF6B35;
            border-right: 6px solid #1A759F;
            border-radius: 50%;
            animation: spin 1.5s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Loading text */
        .loading-title {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #FF6B35 0%, #1A759F 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
        }

        .loading-subtitle {
            font-size: 1.1rem;
            color: #7F8C8D;
            margin-bottom: 2rem;
        }

        /* Progress dots animation */
        .progress-dots {
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin-top: 1.5rem;
        }

        .progress-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: linear-gradient(135deg, #FF6B35 0%, #1A759F 100%);
            animation: pulse 1.5s ease-in-out infinite;
        }

        .progress-dot:nth-child(2) {
            animation-delay: 0.3s;
        }

        .progress-dot:nth-child(3) {
            animation-delay: 0.6s;
        }

        @keyframes pulse {
            0%, 100% {
                opacity: 0.3;
                transform: scale(0.8);
            }
            50% {
                opacity: 1;
                transform: scale(1.2);
            }
        }
    </style>

    <div class="loading-overlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <div class="loading-title">Crafting Your Portfolio</div>
            <div class="loading-subtitle">Our AI is analyzing thousands of market scenarios to create your personalized investment strategy</div>
            <div class="progress-dots">
                <div class="progress-dot"></div>
                <div class="progress-dot"></div>
                <div class="progress-dot"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def show_onboarding():
    """Display streamlined single-screen onboarding flow."""

    # Check if we should show results instead of form
    if st.session_state.get('show_onboarding_results', False) and st.session_state.get('onboarding_data'):
        # Set flag to show overlay during generation
        st.session_state.generating_from_onboarding = True

        # Process and show results
        data = st.session_state.onboarding_data
        process_streamlined_onboarding(data['age_range'], data['timeline'],
                                     data['emergency_fund'], data['initial_investment'],
                                     data['loss_reaction'])
        # Clear the flags
        st.session_state.show_onboarding_results = False
        st.session_state.onboarding_data = None
        return

    # Minimal CSS - fix dropdown styling and prevent KaTeX rendering
    st.markdown("""
    <style>
        /* Reset selectbox styling to default */
        .stSelectbox > div > div {
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
        }

        /* Reset radio button styling */
        .stRadio > div {
            background-color: transparent;
        }

        /* Simple button styling */
        .stButton > button[kind="primary"] {
            background-color: #FF6B35;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
        }

        .stButton > button[kind="primary"]:hover {
            background-color: #E55A2B;
        }
    </style>
    """, unsafe_allow_html=True)

    # Use InvestForge logo from landing page - centered layout
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Logo and branding
        render_investforge_header("Welcome to InvestForge! 🚀", "Let's personalize your experience in 30 seconds")

        # Single form with all questions
        with st.form("streamlined_onboarding"):
            # Question 1: Age + Timeline Combo
            st.markdown("### 🎯 I'm investing for...")

            col1, col2 = st.columns(2)
            with col1:
                age_range = st.selectbox(
                    "My age:",
                    [
                        "16-20 (High school/Early college)",
                        "21-25 (College/Entry career)",
                        "26-30 (Early career)",
                        "31-35 (Establishing career)",
                        "36+ (Experienced)"
                    ],
                    index=2,  # Default to 26-30
                    help="Your age helps determine your investment capacity"
                )

            with col2:
                timeline = st.selectbox(
                    "Investment timeline:",
                    [
                        "Learning only (no timeline)",
                        "1-2 years",
                        "3-5 years",
                        "5-10 years",
                        "10+ years"
                    ],
                    index=2,  # Default to 3-5 years
                    help="How long before you need this money"
                )

            st.markdown("---")

            # Question 2: Emergency Fund Status
            st.markdown("### 💰 My emergency savings situation:")
            emergency_fund = st.radio(
                "Current emergency fund status:",
                [
                    "I'm set (3+ months expenses saved)",
                    "Getting there (1-3 months saved)",
                    "Just starting (less than 1 month)",
                    "I'll build it while investing"
                ],
                index=1,  # Default to "Getting there"
                help="Emergency funds help you avoid panic selling during market downturns"
            )

            st.markdown("---")

            # Question 3: Initial Investment Amount
            st.markdown("### 💰 How much can you comfortably invest to start?")

            # Use fixed amount options to avoid form state issues
            # (Dynamic options based on age can cause selectbox value mismatches in Streamlit forms)
            amount_options = [
                "$25 - Just getting started",
                "$50 - Small but steady start",
                "$100 - Beginner friendly",
                "$250 - Ready to learn",
                "$500 - Serious about investing",
                "$1,000 - Confident starter",
                "$2,500 - Experienced beginner",
                "$5,000 - Substantial commitment",
                "$10,000+ - Experienced investor"
            ]

            initial_investment = st.selectbox(
                "Choose your starting investment amount:",
                amount_options,
                index=2,  # Default to $100
                key="initial_investment_amount",  # Unique key for proper state tracking
                help="💡 Remember: only invest what you can afford to lose. You can always add more later!"
            )

            st.markdown("---")

            # Question 4: Loss Reaction Test
            # Use escaped text to prevent KaTeX rendering of dollar signs
            st.markdown("### 📉 If I invested \\$100 and it dropped to \\$70 next month, I'd probably:")
            loss_reaction = st.radio(
                "My likely reaction:",
                [
                    "Buy more - it's on sale!",
                    "Hold and wait it out",
                    "Worry but hold on",
                    "Sell before I lose more"
                ],
                index=1,  # Default to "Hold and wait it out"
                help="This helps us understand your natural response to market volatility"
            )

            st.markdown("---")

            # Submit button
            submitted = st.form_submit_button(
                "🚀 Start Investing",
                type="primary",
                use_container_width=True
            )

        if submitted:
            # Process the streamlined onboarding
            st.session_state.onboarding_data = {
                'age_range': age_range,
                'timeline': timeline,
                'emergency_fund': emergency_fund,
                'initial_investment': initial_investment,
                'loss_reaction': loss_reaction
            }
            st.session_state.show_onboarding_results = True
            st.rerun()


def process_streamlined_onboarding(age_range: str, timeline: str, emergency_fund: str, initial_investment: str, loss_reaction: str):
    """Process the streamlined 4-question onboarding and calculate risk profile."""
    
    # Calculate risk tolerance using the optimized algorithm
    risk_profile = calculate_risk_tolerance_fast(age_range, timeline, emergency_fund, loss_reaction)
    
    # Infer primary goal based on age and timeline
    primary_goal = infer_investment_goal(age_range, timeline)
    
    # Create comprehensive user preferences structure
    user_preferences = {
        'demographics': {
            'age_range': age_range,
            'income_range': infer_income_range(age_range),  # Infer based on age
        },
        'investment_goals': {
            'primary_goal': primary_goal,
            'timeline': timeline,
            'initial_investment_amount': initial_investment,
        },
        'risk_assessment': {
            'risk_profile': risk_profile['category'].lower(),
            'risk_score': risk_profile['score'],
            'emergency_fund_status': emergency_fund,
            'loss_reaction': loss_reaction,
        },
        'onboarding_complete': True,
        'onboarding_date': datetime.now().isoformat(),
        'onboarding_version': 'streamlined_v1'
    }
    
    # Store in session state
    st.session_state.user_preferences = user_preferences
    st.session_state.onboarding_complete = True

    # Save preferences
    save_user_preferences_to_api(user_preferences)

    # Skip intermediate results page - go directly to portfolio generation
    st.session_state.show_portfolio_generation = True
    st.session_state.show_onboarding = False
    st.rerun()


def calculate_risk_tolerance_fast(age_range: str, timeline: str, emergency_fund: str, loss_reaction: str) -> dict:
    """
    Fast risk tolerance calculation from just 3 questions.
    Returns risk score 0-1 and category with investment recommendations.
    """
    
    # Base score from age + timeline matrix (highest predictive power)
    age_timeline_matrix = {
        # (age_range, timeline): base_score
        ("16-20 (High school/Early college)", "Learning only (no timeline)"): 0.4,
        ("16-20 (High school/Early college)", "1-2 years"): 0.3,
        ("16-20 (High school/Early college)", "3-5 years"): 0.7,
        ("16-20 (High school/Early college)", "5-10 years"): 0.8,
        ("16-20 (High school/Early college)", "10+ years"): 0.9,
        
        ("21-25 (College/Entry career)", "Learning only (no timeline)"): 0.35,
        ("21-25 (College/Entry career)", "1-2 years"): 0.3,
        ("21-25 (College/Entry career)", "3-5 years"): 0.65,
        ("21-25 (College/Entry career)", "5-10 years"): 0.75,
        ("21-25 (College/Entry career)", "10+ years"): 0.85,
        
        ("26-30 (Early career)", "Learning only (no timeline)"): 0.3,
        ("26-30 (Early career)", "1-2 years"): 0.25,
        ("26-30 (Early career)", "3-5 years"): 0.55,
        ("26-30 (Early career)", "5-10 years"): 0.65,
        ("26-30 (Early career)", "10+ years"): 0.75,
        
        ("31-35 (Establishing career)", "Learning only (no timeline)"): 0.25,
        ("31-35 (Establishing career)", "1-2 years"): 0.2,
        ("31-35 (Establishing career)", "3-5 years"): 0.45,
        ("31-35 (Establishing career)", "5-10 years"): 0.55,
        ("31-35 (Establishing career)", "10+ years"): 0.65,
        
        ("36+ (Experienced)", "Learning only (no timeline)"): 0.2,
        ("36+ (Experienced)", "1-2 years"): 0.15,
        ("36+ (Experienced)", "3-5 years"): 0.35,
        ("36+ (Experienced)", "5-10 years"): 0.45,
        ("36+ (Experienced)", "10+ years"): 0.55,
    }
    
    base_score = age_timeline_matrix.get((age_range, timeline), 0.5)
    
    # Emergency fund modifier (multiplicative - most important)
    emergency_modifiers = {
        "I'm set (3+ months expenses saved)": 1.0,      # No change - they're prepared
        "Getting there (1-3 months saved)": 0.85,      # Reduce risk by 15%
        "Just starting (less than 1 month)": 0.65,     # Reduce risk by 35%
        "I'll build it while investing": 0.5           # Reduce risk by 50%
    }
    
    # Loss reaction modifier (additive - behavioral indicator)
    loss_modifiers = {
        "Buy more - it's on sale!": +0.2,       # Increase risk tolerance
        "Hold and wait it out": 0,              # Neutral - as expected
        "Worry but hold on": -0.1,              # Slightly decrease
        "Sell before I lose more": -0.3         # Significantly decrease
    }
    
    # Calculate final score
    final_score = base_score * emergency_modifiers[emergency_fund]
    final_score += loss_modifiers[loss_reaction]
    
    # Bound between 0.1 and 0.9
    final_score = max(0.1, min(0.9, final_score))
    
    # Categorize and provide recommendations
    if final_score < 0.33:
        return {
            "score": final_score,
            "category": "Conservative",
            "allocation": {"stocks": 30, "bonds": 50, "cash": 20},
            "products": ["VOO (S&P 500)", "BND (Bond Index)", "High-yield savings"],
            "description": "Focus on capital preservation with modest growth"
        }
    elif final_score < 0.67:
        return {
            "score": final_score,
            "category": "Moderate", 
            "allocation": {"stocks": 60, "bonds": 30, "cash": 10},
            "products": ["VTI (Total Market)", "VOO (S&P 500)", "Some individual stocks"],
            "description": "Balanced approach between growth and stability"
        }
    else:
        return {
            "score": final_score,
            "category": "Growth-Focused",
            "allocation": {"stocks": 80, "bonds": 15, "cash": 5},
            "products": ["QQQ (Tech Growth)", "VTI (Total Market)", "Individual growth stocks"],
            "description": "Aggressive growth with higher volatility tolerance"
        }


def infer_investment_goal(age_range: str, timeline: str) -> str:
    """
    Infer investment goal based on age and timeline combination.
    Uses demographic patterns to predict most likely goal.
    """
    
    # Goal inference matrix
    goal_matrix = {
        # Learning and short-term goals
        ("16-20 (High school/Early college)", "Learning only (no timeline)"): "first_investment",
        ("16-20 (High school/Early college)", "1-2 years"): "first_investment",
        ("21-25 (College/Entry career)", "Learning only (no timeline)"): "first_investment", 
        ("21-25 (College/Entry career)", "1-2 years"): "emergency_fund",
        ("26-30 (Early career)", "Learning only (no timeline)"): "wealth_building",
        ("26-30 (Early career)", "1-2 years"): "emergency_fund",
        ("31-35 (Establishing career)", "Learning only (no timeline)"): "wealth_building",
        ("31-35 (Establishing career)", "1-2 years"): "major_purchase",
        ("36+ (Experienced)", "Learning only (no timeline)"): "wealth_building",
        ("36+ (Experienced)", "1-2 years"): "major_purchase",
        
        # Medium-term goals  
        ("16-20 (High school/Early college)", "3-5 years"): "wealth_building",
        ("16-20 (High school/Early college)", "5-10 years"): "wealth_building",
        ("21-25 (College/Entry career)", "3-5 years"): "wealth_building", 
        ("21-25 (College/Entry career)", "5-10 years"): "wealth_building",
        ("26-30 (Early career)", "3-5 years"): "wealth_building",
        ("26-30 (Early career)", "5-10 years"): "wealth_building",
        ("31-35 (Establishing career)", "3-5 years"): "wealth_building",
        ("31-35 (Establishing career)", "5-10 years"): "retirement_planning",
        ("36+ (Experienced)", "3-5 years"): "wealth_building",
        ("36+ (Experienced)", "5-10 years"): "retirement_planning",
        
        # Long-term goals
        ("16-20 (High school/Early college)", "10+ years"): "retirement_planning",
        ("21-25 (College/Entry career)", "10+ years"): "retirement_planning", 
        ("26-30 (Early career)", "10+ years"): "retirement_planning",
        ("31-35 (Establishing career)", "10+ years"): "retirement_planning",
        ("36+ (Experienced)", "10+ years"): "retirement_planning",
    }
    
    return goal_matrix.get((age_range, timeline), "wealth_building")


def infer_income_range(age_range: str) -> str:
    """Infer likely income range based on age (demographic averages)."""
    income_map = {
        "16-20 (High school/Early college)": "10k-25k",    # Part-time, allowance
        "21-25 (College/Entry career)": "25k-50k",         # Entry level, college
        "26-30 (Early career)": "50k-75k",                 # Early career
        "31-35 (Establishing career)": "75k-100k",         # Established career  
        "36+ (Experienced)": "100k+"                       # Peak earning years
    }
    return income_map.get(age_range, "50k-75k")


def show_onboarding_results(risk_profile: dict, primary_goal: str):
    """Display onboarding results with personalized recommendations."""
    
    st.success("🎉 **Profile Complete!** Your personalized investment plan is ready.")
    
    # Display risk profile results
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"### 🎯 Your Investment Profile: **{risk_profile['category']}**")
        st.markdown(f"*{risk_profile['description']}*")
        
        st.markdown("#### 📊 Recommended Asset Allocation")
        allocation = risk_profile['allocation']
        
        # Create a simple text-based visualization
        st.markdown(f"""
        - **Stocks**: {allocation['stocks']}% 📈
        - **Bonds**: {allocation['bonds']}% 🏦  
        - **Cash**: {allocation['cash']}% 💵
        """)
        
        st.markdown("#### 🛒 Recommended Products")
        for product in risk_profile['products']:
            st.markdown(f"• {product}")
    
    with col2:
        st.markdown("#### 🎯 Inferred Goal")
        goal_display = {
            "emergency_fund": "🚨 Emergency Fund",
            "first_investment": "🌱 First Investment", 
            "major_purchase": "🏠 Major Purchase",
            "wealth_building": "💰 Wealth Building",
            "retirement_planning": "🏖️ Retirement Planning"
        }
        st.info(goal_display.get(primary_goal, "💰 Wealth Building"))
        
        st.markdown("#### 📈 Risk Score")
        st.metric("Risk Tolerance", f"{risk_profile['score']:.2f}")
    
    # Action button - simplified to only portfolio generation
    st.markdown("---")
    
    # Center the button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("💼 Generate My Portfolio", type="primary", use_container_width=True, key="generate_portfolio_btn"):
            st.session_state.show_portfolio_generation = True
            st.session_state.show_onboarding = False
            st.rerun()
    
    # Add informational text about stock analysis
    st.markdown("---")
    st.info("💡 **Tip**: After generating your portfolio, you can analyze individual stocks in the main application interface!")


def generate_portfolio_with_progress():
    """Generate portfolio with progress tracking."""

    # Check if we're generating from onboarding - show overlay instead of standard UI
    if st.session_state.get('generating_from_onboarding', False):
        # Show the overlay
        show_portfolio_generation_overlay()

        # Continue with generation in the background
        # The overlay will stay visible until generation completes
    else:
        # Standard UI for direct portfolio generation (not from onboarding)
        # Add navigation menu
        st.markdown("## 🎯 InvestForge Portfolio Creator")

        # Simple navigation
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📊 Analyze Stocks", use_container_width=True):
                # Switch to stock analysis mode
                st.session_state.show_portfolio_generation = False
                st.session_state.show_main_app = True
                st.rerun()

        st.markdown("---")
        st.markdown("### 💼 Your Personalized Portfolio")

    # Initialize progress tracking
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    
    try:
        # Get user preferences
        user_preferences = st.session_state.get('user_preferences', {})
        
        # Extract investment amount from preferences
        investment_amount_str = user_preferences.get('investment_goals', {}).get('initial_investment_amount', '$100 - Beginner friendly')
        logger.info(f"Raw investment_amount_str from user preferences: '{investment_amount_str}'")

        # Extract numeric amount using regex (e.g., "$1,000 - Confident starter" -> 1000)
        # Handle formats: "$100 - Description", "$10,000+ - Description", "$25 - Description"
        try:
            import re
            # Extract first number (with optional commas and +) from the string
            match = re.search(r'\$?([\d,]+)\+?', str(investment_amount_str))
            if match:
                # Remove commas and convert to float
                amount_str = match.group(1).replace(',', '')
                investment_amount = float(amount_str)
                logger.info(f"Successfully parsed investment amount: ${investment_amount:,.2f}")
            else:
                logger.warning(f"No numeric value found in '{investment_amount_str}', using default 100")
                investment_amount = 100.0
        except Exception as e:
            logger.warning(f"Failed to parse investment amount '{investment_amount_str}': {str(e)}, using default 100")
            investment_amount = 100.0  # Default fallback
        
        # Prepare user profile for crew
        user_profile = {
            'age_range': user_preferences.get('demographics', {}).get('age_range', '26-30'),
            'income_range': user_preferences.get('demographics', {}).get('income_range', '50k-75k'),
            'primary_goal': user_preferences.get('investment_goals', {}).get('primary_goal', 'wealth_building'),
            'timeline': user_preferences.get('investment_goals', {}).get('timeline', '5-10 years'),
            'risk_profile': user_preferences.get('risk_assessment', {}).get('risk_profile', 'moderate'),
            'risk_score': user_preferences.get('risk_assessment', {}).get('risk_score', 0.5),
            'emergency_fund_status': user_preferences.get('risk_assessment', {}).get('emergency_fund_status', 'Getting there'),
            'loss_reaction': user_preferences.get('risk_assessment', {}).get('loss_reaction', 'Hold and wait it out')
        }
        
        # Show parsed investment amount for user verification
        st.info(f"💰 Generating portfolio for: **${investment_amount:,.0f}**")

        # Progress updates
        status_placeholder.write("🔄 Initializing portfolio analysis...")
        progress_bar.progress(10)

        # Initialize crew
        status_placeholder.write("🤖 Setting up AI portfolio strategist...")
        progress_bar.progress(20)

        # Create portfolio
        status_placeholder.write(f"💡 Analyzing best investments for ${investment_amount:,.0f}...")
        progress_bar.progress(40)
        
        # Call portfolio crew (pass numeric value, not formatted string)
        result = portfoliocrew.create_portfolio(
            amount=investment_amount,  # Pass as number, portfoliocrew will format
            user_profile=user_profile
        )
        
        progress_bar.progress(80)
        status_placeholder.write("✨ Finalizing your personalized portfolio...")
        
        # Store results in session state
        st.session_state.portfolio_result = {
            'result': result,
            'investment_amount': investment_amount,
            'generated_at': datetime.now().isoformat(),
            'user_profile': user_profile
        }
        
        progress_bar.progress(100)
        
        # Show success animation
        st.balloons()
        status_placeholder.success("✅ Portfolio generated successfully!")
        
        # Clear progress indicators after a moment
        import time
        time.sleep(1)
        progress_placeholder.empty()
        status_placeholder.empty()
        progress_bar.empty()
        
        # Navigate to portfolio results
        st.session_state.show_portfolio_generation = False
        st.session_state.show_portfolio_results = True
        # Clear the overlay flag
        st.session_state.generating_from_onboarding = False
        st.rerun()
        
    except Exception as e:
        status_placeholder.error(f"❌ Error generating portfolio: {str(e)}")
        st.error("Failed to generate portfolio. Please try again.")
        if st.button("🔄 Retry", type="primary"):
            st.session_state.show_portfolio_generation = False
            st.rerun()


def escape_markdown_latex(text: str) -> str:
    """
    Escape LaTeX/math characters in text to prevent katex rendering.

    Args:
        text: Raw text that may contain LaTeX triggers

    Returns:
        Text with escaped characters safe for st.markdown()
    """
    if not text:
        return text

    # Simple approach: escape common LaTeX triggers
    # Streamlit interprets $ and _ as LaTeX, causing katex font rendering

    # Escape dollar signs (but preserve if already escaped)
    if '\\$' not in text:
        text = text.replace('$', '\\$')

    # Escape underscores (but preserve if already escaped)
    if '\\_' not in text:
        text = text.replace('_', '\\_')

    return text


def get_ticker_name(ticker: str) -> str:
    """Get company/ETF name for a ticker symbol."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        name = stock.info.get('longName') or stock.info.get('shortName') or ticker
        # Shorten very long names
        if len(name) > 40:
            name = name[:37] + "..."
        return name
    except:
        return ticker


def create_performance_chart(projection_data: Dict) -> go.Figure:
    """
    Create an interactive performance projection chart with three scenarios.

    Args:
        projection_data: Dictionary containing projection scenarios and timeline data

    Returns:
        Plotly Figure object with the performance projections
    """
    try:
        # Extract data
        scenarios = projection_data.get('scenarios', {})
        timeline_months = projection_data.get('timeline_months', 0)
        timeline_years = projection_data.get('timeline_years', 0)
        initial_investment = projection_data.get('initial_investment', 0)

        # Create month labels for x-axis
        months = list(range(timeline_months + 1))

        # Create figure
        fig = go.Figure()

        # Add conservative scenario
        if 'conservative' in scenarios:
            fig.add_trace(go.Scatter(
                x=months,
                y=scenarios['conservative']['values'],
                mode='lines',
                name='Conservative',
                line=dict(color='#FF6B6B', width=2, dash='dot'),
                hovertemplate='<b>Conservative</b><br>Month: %{x}<br>Value: $%{y:,.0f}<extra></extra>'
            ))

        # Add expected scenario (thicker line, more prominent)
        if 'expected' in scenarios:
            fig.add_trace(go.Scatter(
                x=months,
                y=scenarios['expected']['values'],
                mode='lines',
                name='Expected',
                line=dict(color='#4ECDC4', width=3),
                hovertemplate='<b>Expected</b><br>Month: %{x}<br>Value: $%{y:,.0f}<extra></extra>'
            ))

        # Add optimistic scenario
        if 'optimistic' in scenarios:
            fig.add_trace(go.Scatter(
                x=months,
                y=scenarios['optimistic']['values'],
                mode='lines',
                name='Optimistic',
                line=dict(color='#95E1D3', width=2, dash='dot'),
                hovertemplate='<b>Optimistic</b><br>Month: %{x}<br>Value: $%{y:,.0f}<extra></extra>'
            ))

        # Add initial investment reference line
        fig.add_hline(
            y=initial_investment,
            line_dash="dash",
            line_color="gray",
            opacity=0.5,
            annotation_text="Initial Investment",
            annotation_position="left"
        )

        # Update layout
        fig.update_layout(
            title=dict(
                text=f'Portfolio Performance Projection ({timeline_years} Years)',
                font=dict(size=20, color='#2C3E50')
            ),
            xaxis=dict(
                title='Months',
                showgrid=True,
                gridcolor='#E8E8E8',
                zeroline=False
            ),
            yaxis=dict(
                title='Portfolio Value ($)',
                showgrid=True,
                gridcolor='#E8E8E8',
                zeroline=False,
                tickformat='$,.0f'
            ),
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#CCCCCC",
                borderwidth=1
            ),
            margin=dict(l=60, r=30, t=80, b=60),
            height=400
        )

        return fig

    except Exception as e:
        logger.error(f"Error creating performance chart: {str(e)}")
        # Return empty figure with error message
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error creating chart: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color='red')
        )
        return fig


def show_portfolio_results():
    """Display the generated portfolio results with progressive enhancements."""
    if 'portfolio_result' not in st.session_state:
        st.error("No portfolio results found. Please generate a portfolio first.")
        if st.button("🔄 Generate Portfolio", type="primary"):
            st.session_state.show_portfolio_results = False
            st.session_state.show_portfolio_generation = True
            st.rerun()
        return

    portfolio_data = st.session_state.portfolio_result
    result = portfolio_data['result']
    investment_amount = portfolio_data['investment_amount']
    user_profile = portfolio_data.get('user_profile', {})

    # Debug logging
    logger.info(f"Result type: {type(result)}")
    logger.info(f"Result has tasks_output: {hasattr(result, 'tasks_output')}")
    if hasattr(result, 'tasks_output'):
        logger.info(f"Tasks output: {result.tasks_output}")
        if result.tasks_output:
            logger.info(f"First task output type: {type(result.tasks_output[0])}")
            if hasattr(result.tasks_output[0], 'raw'):
                logger.info(f"First task raw preview: {result.tasks_output[0].raw[:500]}")

    # ============================================
    # SUCCESS HEADER - InvestForge Style
    # ============================================

    # Extract metrics for header
    risk_profile = user_profile.get('risk_profile', 'moderate').capitalize()
    timeline = user_profile.get('timeline', '5-10 years')
    # Convert risk_score from 0-1 scale to 0-10 scale
    risk_score_raw = user_profile.get('risk_score', 0.5)
    risk_score = risk_score_raw * 10  # Convert to 0-10 scale

    # Parse portfolio data first (needed for projections)
    # BUT: If portfolio was optimized, use the optimized version from session state instead
    if st.session_state.get('portfolio_was_optimized', False) and 'structured_portfolio' in st.session_state:
        # Portfolio was optimized - use the optimized version from session state
        structured_portfolio = st.session_state.structured_portfolio
        portfolio_output = st.session_state.get('portfolio_output', "Optimized portfolio")
        logger.info("Using optimized portfolio from session state")
    elif hasattr(result, 'tasks_output') and result.tasks_output:
        # First time or not optimized - parse from original result
        portfolio_output = result.tasks_output[0].raw if result.tasks_output else "No portfolio data"
        structured_portfolio = parse_portfolio_output(result, investment_amount)
        st.session_state.structured_portfolio = structured_portfolio
        logger.info(f"Parsed original portfolio from result: {len(structured_portfolio.get('tickers', []))} tickers")
    else:
        logger.error(f"Unable to parse portfolio - result structure: {result}")
        st.error("Unable to parse portfolio results.")
        if st.button("🔄 Try Again", type="primary"):
            st.session_state.show_portfolio_results = False
            st.session_state.show_portfolio_generation = True
            st.rerun()
        return

    # Validate that we have tickers
    if not structured_portfolio.get('tickers'):
        logger.error("No tickers found in structured portfolio")
        st.error("❌ Portfolio generation failed - no investments were selected.")
        st.warning("This may be due to:")
        st.markdown("""
        - Invalid or empty response from AI portfolio strategist
        - Parsing error in portfolio output
        - Network or API issues
        """)
        st.info("💡 Please try generating the portfolio again or contact support if the issue persists.")
        if st.button("🔄 Try Again", type="primary"):
            st.session_state.show_portfolio_results = False
            st.session_state.show_portfolio_generation = True
            # Clear the problematic result
            if 'portfolio_result' in st.session_state:
                del st.session_state.portfolio_result
            st.rerun()
        return

    # Calculate diversification score for header
    categories = []
    for ticker in structured_portfolio['tickers']:
        category = "N/A"
        for alloc in structured_portfolio.get('allocations', []):
            if alloc['ticker'] == ticker:
                category = alloc.get('category', 'N/A')
                break
        categories.append(category)
    unique_categories = len(set(categories)) - (1 if "N/A" in categories else 0)
    diversification_score = min(100, int((unique_categories / max(len(structured_portfolio['tickers']), 1)) * 100))

    # Display success header
    st.markdown("""
    <style>
    .success-header {
        background: linear-gradient(135deg, #FF6B35 0%, #4ECDC4 100%);
        border-radius: 15px;
        padding: 2rem;
        margin-bottom: 2rem;
        color: white;
    }
    .success-title {
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .success-subtitle {
        font-size: 1rem;
        opacity: 0.95;
        margin-bottom: 1.5rem;
    }
    .badge-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }
    .badge {
        background: rgba(255, 255, 255, 0.25);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        padding: 1.25rem;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.95;
    }
    </style>
    """, unsafe_allow_html=True)

    # Extract expected return from portfolio output and calculate based on timeline
    expected_return_pct = "N/A"
    expected_return_amount = "N/A"
    timeline_display = timeline

    # Try multiple patterns to extract annual return percentage from portfolio output
    import re
    avg_annual_return = None

    # Pattern 1: "Expected annual return: X-Y%"
    return_match = re.search(r'Expected annual return[^:]*:\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%', str(portfolio_output), re.IGNORECASE)
    if return_match:
        low = float(return_match.group(1))
        high = float(return_match.group(2))
        avg_annual_return = (low + high) / 2
    else:
        # Pattern 2: "X-Y% annual return" or "X-Y% yearly"
        return_match = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%\s*(?:annual|yearly|per year)', str(portfolio_output), re.IGNORECASE)
        if return_match:
            low = float(return_match.group(1))
            high = float(return_match.group(2))
            avg_annual_return = (low + high) / 2
        else:
            # Pattern 3: Any percentage range in the output (less specific)
            return_match = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%', str(portfolio_output))
            if return_match:
                low = float(return_match.group(1))
                high = float(return_match.group(2))
                # Only use if in reasonable return range (3-30%)
                if 3 <= low <= 30 and 3 <= high <= 30:
                    avg_annual_return = (low + high) / 2

    # Fallback: Use defaults based on risk profile if no match found
    if avg_annual_return is None:
        risk_profile_lower = risk_profile.lower()
        if 'conservative' in risk_profile_lower:
            avg_annual_return = 6.0
        elif 'aggressive' in risk_profile_lower:
            avg_annual_return = 12.5
        else:  # moderate
            avg_annual_return = 8.5

    # Now calculate display values
    if avg_annual_return:
        expected_return_pct = f"~{avg_annual_return:.1f}% avg annually"

        # Calculate expected return amount based on timeline
        # Parse timeline to years
        timeline_years = 5  # default
        if "1-2" in timeline:
            timeline_years = 2
            timeline_display = "2Y"
        elif "3-5" in timeline:
            timeline_years = 4
            timeline_display = "4Y"
        elif "5-10" in timeline:
            timeline_years = 7
            timeline_display = "7Y"
        elif "10+" in timeline:
            timeline_years = 15
            timeline_display = "15Y"

        # Calculate compound return over timeline
        total_return = investment_amount * ((1 + avg_annual_return/100) ** timeline_years) - investment_amount
        expected_return_amount = f"+${total_return:,.0f}"

    st.markdown(f"""
    <div class="success-header">
        <div class="success-title">
            🧠 AI Portfolio Created Successfully!
        </div>
        <div class="success-subtitle">
            Powered by specialized AI agents analyzing market data, risk factors, and your personal goals
        </div>
        <div class="badge-row">
            <div class="badge">📊 Risk Profile: {risk_profile}</div>
            <div class="badge">⏰ Timeline: {timeline}</div>
            <div class="badge">🎯 Diversification: {diversification_score}%</div>
        </div>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Initial Investment</div>
                <div class="metric-value">${investment_amount:,.0f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Expected Return ({timeline_display})</div>
                <div class="metric-value" style="color: #2ecc71;">{expected_return_amount}</div>
                <div class="metric-label">{expected_return_pct}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Risk Score</div>
                <div class="metric-value">{risk_score:.1f}/10</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Diversification</div>
                <div class="metric-value">{diversification_score}%</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ============================================
    # SECTION 1: Performance Projection Chart (Full Width)
    # ============================================

    # Extract projection data from second task output
    projection_data = None
    projection_narrative = None

    # Check if projections were regenerated after optimization (if so, don't use old narrative)
    if 'projection_data' in st.session_state:
        # Use regenerated projection data (from optimization)
        projection_data = st.session_state.projection_data
        projection_narrative = None  # Force use of fallback narrative generation with new data
        logger.info("Using regenerated projection data from optimization")
    elif hasattr(result, 'tasks_output') and len(result.tasks_output) > 1:
        # The second task contains the projection data (original portfolio generation)
        projection_task_output = result.tasks_output[1]
        projection_narrative = projection_task_output.raw if hasattr(projection_task_output, 'raw') else str(projection_task_output)

        # Try to extract JSON data from the narrative (CrewAI embeds tool output as JSON in text)
        try:
            import json
            import re
            # Look for JSON-like structures in the text
            json_match = re.search(r'\{[^{}]*"scenarios"[^{}]*\{.*?\}.*?\}', str(projection_narrative), re.DOTALL)
            if json_match:
                projection_data = json.loads(json_match.group())
                logger.info("Successfully extracted projection data from task output")
        except Exception as e:
            logger.warning(f"Could not extract projection JSON: {str(e)}")

    # Fallback: Recalculate projections if data not found
    if not projection_data and user_profile:
        try:
            from tools.performance_projection_tool import _calculate_projections_impl
            from portfoliocrew import parse_timeline_to_years

            # Parse expected return from portfolio output
            expected_return = 0.08  # Default 8%
            if structured_portfolio.get('expected_return'):
                # Extract midpoint from range like "7-9%"
                return_match = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)', str(structured_portfolio['expected_return']))
                if return_match:
                    low = float(return_match.group(1))
                    high = float(return_match.group(2))
                    expected_return = (low + high) / 2 / 100  # Convert to decimal

            # Get timeline and volatility
            timeline_years = parse_timeline_to_years(user_profile.get('timeline', '5-10 years'))
            risk_profile = user_profile.get('risk_profile', 'moderate').lower()
            volatility_map = {'conservative': 0.10, 'moderate': 0.15, 'aggressive': 0.20}
            annual_volatility = volatility_map.get(risk_profile, 0.15)

            # Calculate projections using the non-decorated implementation
            projection_data = _calculate_projections_impl(
                investment_amount=float(investment_amount),
                expected_annual_return=expected_return,
                timeline_years=timeline_years,
                annual_volatility=annual_volatility
            )
            logger.info("Recalculated projection data as fallback")
        except Exception as e:
            logger.error(f"Failed to recalculate projections: {str(e)}")

    # ============================================
    # MAIN CONTENT: 4-TAB LAYOUT
    # ============================================

    # Add custom tab styling
    st.markdown("""
    <style>
    /* Style the tabs container */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 8px;
        border-radius: 12px;
    }

    /* Style individual tabs */
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent;
        border-radius: 8px;
        color: #6c757d;
        font-weight: 500;
        padding: 0 24px;
        border: none;
    }

    /* Style the active/selected tab */
    .stTabs [aria-selected="true"] {
        background-color: white;
        color: #212529;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Remove the default underline indicator */
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: transparent;
    }

    /* Hover effect for non-selected tabs */
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(255, 255, 255, 0.5);
    }
    </style>
    """, unsafe_allow_html=True)

    # Create 4 tabs
    tab_overview, tab_risk, tab_projections, tab_budget = st.tabs([
        "📊 Overview",
        "⚠️ Risk Analysis",
        "📈 Projections",
        "💰 Budget Plan"
    ])

    # ============================================
    # TAB 1: OVERVIEW - Portfolio Allocation Table
    # ============================================
    with tab_overview:

        # Always use the session state version to get latest updates (e.g., after optimization)
        if 'structured_portfolio' in st.session_state:
            structured_portfolio = st.session_state.structured_portfolio

        # Conditional header based on whether portfolio was optimized
        if st.session_state.get('portfolio_was_optimized', False):
            st.markdown("### 📊 Optimized Portfolio Allocation")
        else:
            st.markdown("### 📊 Suggested Portfolio Allocation")

        # Display allocation table with enhanced design
        if structured_portfolio['tickers']:
            # Get ticker names and create enhanced portfolio table
            portfolio_table_data = []
            for i, ticker in enumerate(structured_portfolio['tickers']):
                # Get category
                category = "N/A"
                for alloc in structured_portfolio.get('allocations', []):
                    if alloc['ticker'] == ticker:
                        category = alloc.get('category', 'N/A')
                        break

                # Get asset name and current price
                asset_name = get_ticker_name(ticker)

                # Calculate actual shares based on current price
                amount = structured_portfolio['amounts'][i]
                try:
                    import yfinance as yf
                    stock = yf.Ticker(ticker)
                    current_price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')
                    if current_price and current_price > 0:
                        shares = round(amount / current_price, 4)
                    else:
                        # Fallback if price not available
                        shares = 0
                except:
                    shares = 0

                portfolio_table_data.append({
                    'Ticker': ticker,
                    'Asset Name': asset_name,
                    'Type': category,
                    'Allocation': structured_portfolio['weights'][i],
                    'Amount': amount,
                    'Shares': shares
                })

            # Create styled table
            st.markdown("""
            <style>
            .allocation-table {
                width: 100%;
                border-collapse: collapse;
                margin: 1rem 0;
            }
            .allocation-table th {
                background: #f8f9fa;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                border-bottom: 2px solid #dee2e6;
            }
            .allocation-table td {
                padding: 12px;
                border-bottom: 1px solid #dee2e6;
            }
            .type-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 0.85rem;
                font-weight: 500;
            }
            .badge-etf { background: #e3f2fd; color: #1976d2; }
            .badge-stock { background: #f3e5f5; color: #7b1fa2; }
            .badge-tech { background: #e8f5e9; color: #388e3c; }
            .badge-other { background: #fff3e0; color: #f57c00; }
            .allocation-bar {
                width: 100%;
                height: 8px;
                background: #e9ecef;
                border-radius: 4px;
                overflow: hidden;
                margin-top: 4px;
            }
            .allocation-fill {
                height: 100%;
                background: linear-gradient(90deg, #FF6B35 0%, #4ECDC4 100%);
                border-radius: 4px;
            }
            </style>
            """, unsafe_allow_html=True)

            # Display table with HTML for better styling
            table_html = '<table class="allocation-table"><thead><tr>'
            table_html += '<th>Ticker</th><th>Asset Name</th><th>Type</th><th>Allocation</th><th>Amount</th><th>Shares</th>'
            table_html += '</tr></thead><tbody>'

            for item in portfolio_table_data:
                # Determine badge class
                badge_class = "badge-other"
                if "ETF" in item['Type'].upper():
                    badge_class = "badge-etf"
                elif "STOCK" in item['Type'].upper() or "TECHNOLOGY" in item['Type'].upper():
                    badge_class = "badge-tech"

                alloc_pct = item['Allocation'] * 100
                table_html += f'<tr>'
                table_html += f'<td><strong>{item["Ticker"]}</strong></td>'
                table_html += f'<td>{item["Asset Name"]}</td>'
                table_html += f'<td><span class="type-badge {badge_class}">{item["Type"]}</span></td>'
                table_html += f'<td>{alloc_pct:.1f}%<div class="allocation-bar"><div class="allocation-fill" style="width: {alloc_pct}%"></div></div></td>'
                table_html += f'<td>${item["Amount"]:,.2f}</td>'
                table_html += f'<td>{item["Shares"]}</td>'
                table_html += f'</tr>'

            table_html += '</tbody></table>'
            st.markdown(table_html, unsafe_allow_html=True)

            # Action buttons
            st.markdown("---")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("💾 Save Portfolio", type="secondary", use_container_width=True):
                    # Prepare portfolio data for save dialog
                    try:
                        portfolio_data_to_save = {
                            'user_profile': user_profile,
                            'allocations': [
                                {
                                    'ticker': str(ticker),
                                    'percentage': float(weight * 100),
                                    'amount': float(weight * investment_amount),
                                    'category': structured_portfolio.get('allocations', [{}])[i].get('category', 'Stock') if i < len(structured_portfolio.get('allocations', [])) else 'Stock'
                                }
                                for i, (ticker, weight) in enumerate(zip(structured_portfolio['tickers'], structured_portfolio['weights']))
                            ],
                            'investment_amount': float(investment_amount),
                            'expected_return': structured_portfolio.get('expected_return', 'N/A')
                        }

                        user_id = st.session_state.get('user_email', 'demo@investforge.ai')
                        if not user_id or user_id == 'demo@investforge.ai':
                            st.error("Please log in to save portfolios")
                        else:
                            show_save_portfolio_dialog(portfolio_data_to_save, user_id)
                    except Exception as e:
                        st.error(f"Error preparing portfolio data: {str(e)}")
                        logger.error(f"Portfolio save preparation error: {str(e)}")

            with col2:
                # Hide optimize button if portfolio was already optimized
                if not st.session_state.get('portfolio_was_optimized', False):
                    if st.button("🎯 Smart Optimize", type="primary", use_container_width=True,
                                help="Uses quantitative models to improve your returns"):
                        # Trigger optimization
                        with st.spinner("🔄 Optimizing portfolio allocation..."):
                            try:
                                # Run optimization using direct tool call + AI interpretation
                                opt_crew_result = QuantitativeAnalysisCrew().optimize_portfolio(
                                    tickers=structured_portfolio['tickers'],
                                    current_weights=structured_portfolio['weights'],
                                    user_profile=user_profile,
                                    investment_amount=investment_amount
                                )

                                st.session_state.portfolio_optimization_crew = opt_crew_result
                                st.success("✅ Portfolio optimization completed!")
                                st.rerun()

                            except Exception as e:
                                st.error(f"Optimization failed: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc())
                else:
                    st.info("✅ Portfolio is already optimized")

        else:
            st.warning("No portfolio allocation data available.")

        # ============================================
        # OPTIMIZATION METRICS OR PORTFOLIO INSIGHTS
        # ============================================
        # Check if optimization has been run
        if 'portfolio_optimization_crew' in st.session_state:
            opt_result = st.session_state.portfolio_optimization_crew

            # Extract structured data
            if isinstance(opt_result, dict) and 'tool_output' in opt_result:
                tool_output = opt_result['tool_output']
                recommendations = opt_result.get('recommendations', [])

                st.markdown("---")
                st.markdown("## 📊 Quantitative Optimization Metrics")

                # SECTION A: Current vs Optimized Comparison
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### Current Portfolio")
                    # Display current portfolio metrics if available
                    if 'current_portfolio' in tool_output:
                        current_portfolio = tool_output['current_portfolio']

                        # Use portfolio's stated expected return (from agent) instead of calculated historical return
                        # This matches what's shown in Portfolio Overview
                        portfolio_expected_return = None
                        if structured_portfolio.get('expected_return'):
                            # Extract midpoint from range like "7-9%"
                            return_match = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)', str(structured_portfolio['expected_return']))
                            if return_match:
                                low = float(return_match.group(1))
                                high = float(return_match.group(2))
                                portfolio_expected_return = (low + high) / 2 / 100  # Convert to decimal

                        # Display expected return (use portfolio's stated return if available, otherwise use calculated)
                        display_return = portfolio_expected_return if portfolio_expected_return else current_portfolio['expected_return']

                        st.metric("Expected Return", f"{display_return*100:.1f}%")
                        st.metric("Volatility", f"{current_portfolio['volatility']*100:.1f}%")
                        st.metric("Sharpe Ratio", f"{current_portfolio['sharpe_ratio']:.2f}")

                        # Add tooltip explaining the return source
                        if portfolio_expected_return:
                            st.caption("📊 Expected return from portfolio strategy; volatility & Sharpe from historical data")
                    elif structured_portfolio.get('weights'):
                        # Fallback if current_portfolio not in tool_output
                        current_weights_list = structured_portfolio['weights']
                        tickers_list = structured_portfolio['tickers']

                        current_return = sum(
                            w * tool_output['individual_returns'].get(t, 0)
                            for t, w in zip(tickers_list, current_weights_list)
                        )
                        st.metric("Expected Return", f"{current_return*100:.1f}%")
                        st.warning("⚠️ Volatility and Sharpe ratio not available for current portfolio")

                with col2:
                    st.markdown("### Optimized Portfolio (Max Sharpe)")
                    opt_portfolio = tool_output['max_sharpe_portfolio']

                    # Show improvement delta if we have current portfolio metrics
                    return_delta = None
                    volatility_delta = None
                    sharpe_delta = None

                    if 'current_portfolio' in tool_output:
                        current = tool_output['current_portfolio']
                        # Use the same display_return calculated above for consistent comparison
                        current_return_for_comparison = display_return if 'display_return' in locals() else current['expected_return']
                        return_delta = f"+{(opt_portfolio['expected_return']-current_return_for_comparison)*100:.1f}%"
                        volatility_delta = f"{(opt_portfolio['volatility']-current['volatility'])*100:.1f}%"
                        sharpe_delta = f"+{opt_portfolio['sharpe_ratio']-current['sharpe_ratio']:.2f}"

                    st.metric(
                        "Expected Return",
                        f"{opt_portfolio['expected_return']*100:.1f}%",
                        delta=return_delta
                    )
                    st.metric(
                        "Volatility",
                        f"{opt_portfolio['volatility']*100:.1f}%",
                        delta=volatility_delta,
                        delta_color="inverse"  # Lower volatility is better
                    )
                    st.metric(
                        "Sharpe Ratio",
                        f"{opt_portfolio['sharpe_ratio']:.2f}",
                        delta=sharpe_delta
                    )

                # SECTION B: Recommendations Table
                if recommendations:
                    st.markdown("### 💡 Recommended Changes")
                    for rec in recommendations:
                        if rec['action'] == 'increase':
                            st.success(
                                f"📈 **{rec['ticker']}**: Increase from {rec['current_weight']*100:.1f}% to {rec['optimized_weight']*100:.1f}% "
                                f"(+{rec['percentage_change']:.1f}% / ${rec['dollar_amount']:,.2f})"
                            )
                        else:
                            st.warning(
                                f"📉 **{rec['ticker']}**: Decrease from {rec['current_weight']*100:.1f}% to {rec['optimized_weight']*100:.1f}% "
                                f"(-{rec['percentage_change']:.1f}% / ${rec['dollar_amount']:,.2f})"
                            )

                    # Apply button - Show confirmation dialog
                    @st.dialog("Confirm Portfolio Optimization")
                    def confirm_apply_optimization():
                        """Confirmation dialog for applying optimized portfolio."""
                        # Fetch data from session state (don't rely on closure variables)
                        if 'portfolio_optimization_crew' not in st.session_state:
                            st.error("Optimization data not found")
                            return

                        opt_result = st.session_state.portfolio_optimization_crew
                        tool_output = opt_result.get('tool_output', {})
                        structured_portfolio = st.session_state.get('structured_portfolio', {})

                        st.markdown("### ⚠️ This will replace your original portfolio")

                        # Show before/after comparison
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("**Current Portfolio**")
                            if 'current_portfolio' in tool_output:
                                current_return = tool_output['current_portfolio']['expected_return']
                                # Use portfolio's stated return if available
                                if structured_portfolio.get('expected_return'):
                                    return_match = re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)',
                                                            str(structured_portfolio['expected_return']))
                                    if return_match:
                                        low = float(return_match.group(1))
                                        high = float(return_match.group(2))
                                        current_return = (low + high) / 2 / 100
                                st.metric("Expected Return", f"{current_return*100:.1f}%")
                            else:
                                st.info("No metrics available")

                        with col2:
                            st.markdown("**Optimized Portfolio**")
                            opt_return = tool_output['max_sharpe_portfolio']['expected_return']
                            improvement = opt_return - (current_return if 'current_portfolio' in tool_output else opt_return)
                            st.metric("Expected Return", f"{opt_return*100:.1f}%",
                                     delta=f"+{improvement*100:.1f}%" if improvement > 0 else None)

                        st.markdown("---")
                        st.markdown("**Changes that will be applied:**")
                        st.markdown("- Portfolio allocation will be updated to optimized weights")
                        st.markdown("- Portfolio insights will be regenerated")
                        st.markdown("- Risk analysis will be recalculated")
                        st.markdown("- Performance projections will be updated")

                        st.warning("⚠️ **Note:** This action cannot be undone.")

                        # Confirmation buttons
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.button("✅ Confirm & Apply", type="primary", use_container_width=True):
                                apply_optimized_portfolio()
                                st.rerun()
                        with col2:
                            if st.button("❌ Cancel", use_container_width=True):
                                st.rerun()

                    def apply_optimized_portfolio():
                        """Apply the optimized portfolio and regenerate all components."""
                        with st.spinner("🔄 Applying optimized portfolio..."):
                            try:
                                # Get all data from session state (don't rely on closure)
                                opt_result = st.session_state.portfolio_optimization_crew
                                tool_output = opt_result['tool_output']
                                portfolio_data = st.session_state.get('portfolio_result', {})
                                investment_amount = portfolio_data.get('investment_amount', 10000)
                                user_profile = portfolio_data.get('user_profile', {})

                                # STEP 1: Update portfolio with optimized weights
                                optimized_weights = tool_output['max_sharpe_portfolio']['weights']
                                opt_portfolio = tool_output['max_sharpe_portfolio']

                                # Filter out holdings with exactly 0% allocation
                                # This removes holdings the optimization suggests eliminating
                                # Using a very small threshold (1e-10) to handle floating point precision
                                MIN_ALLOCATION_THRESHOLD = 1e-10  # Effectively 0%
                                filtered_weights = {ticker: weight for ticker, weight in optimized_weights.items()
                                                   if weight > MIN_ALLOCATION_THRESHOLD}

                                logger.info(f"Filtered out {len(optimized_weights) - len(filtered_weights)} holdings with 0% allocation")

                                # Create new structured portfolio (only non-zero holdings)
                                new_tickers = list(filtered_weights.keys())
                                new_weights = list(filtered_weights.values())
                                new_amounts = [w * investment_amount for w in new_weights]

                                # Reconstruct allocations with placeholder reasoning (will be updated by Portfolio Insights)
                                new_allocations = []
                                for ticker, weight, amount in zip(new_tickers, new_weights, new_amounts):
                                    new_allocations.append({
                                        'ticker': ticker,
                                        'percentage': weight * 100,
                                        'amount': amount,
                                        'reasoning': 'Optimized allocation for improved risk-adjusted returns',
                                        'category': 'N/A'  # Will be updated by Portfolio Insights
                                    })

                                # Update expected return from optimization
                                opt_return = opt_portfolio['expected_return']

                                # Create a completely NEW structured portfolio dictionary
                                # (don't modify the existing one to avoid closure issues)
                                updated_portfolio = {
                                    'tickers': new_tickers,
                                    'weights': new_weights,
                                    'amounts': new_amounts,
                                    'allocations': new_allocations,
                                    'expected_return': f"{opt_return*100-1:.0f}-{opt_return*100+1:.0f}%",
                                    'investment_amount': investment_amount,
                                    'user_profile': user_profile
                                }

                                # Update session state with new portfolio
                                st.session_state.structured_portfolio = updated_portfolio
                                logger.info(f"Updated structured_portfolio in session state with optimized tickers: {new_tickers}")

                                # STEP 2: Regenerate Portfolio Insights with specialized interpretation task
                                with st.spinner("🔄 Regenerating portfolio insights..."):
                                    try:
                                        # Call the portfolio interpretation function from portfoliocrew
                                        portfolio_insights_result = interpret_optimized_portfolio(
                                            optimized_weights=optimized_weights,
                                            optimization_metrics={
                                                'expected_return': opt_return,
                                                'volatility': opt_portfolio['volatility'],
                                                'sharpe_ratio': opt_portfolio['sharpe_ratio']
                                            },
                                            investment_amount=investment_amount,
                                            user_profile=user_profile
                                        )

                                        # Parse the result and update structured_portfolio with better reasoning
                                        parsed_insights = parse_portfolio_output(portfolio_insights_result, investment_amount)

                                        # Update allocations with parsed reasoning and categories
                                        if parsed_insights['allocations']:
                                            for alloc in updated_portfolio['allocations']:
                                                # Find matching allocation from parsed insights
                                                matching = next((p for p in parsed_insights['allocations']
                                                               if p['ticker'] == alloc['ticker']), None)
                                                if matching:
                                                    alloc['reasoning'] = matching['reasoning']
                                                    alloc['category'] = matching.get('category', 'N/A')

                                        # Store the full output for Portfolio Insights display
                                        # Extract raw text from CrewOutput before storing
                                        if hasattr(portfolio_insights_result, 'tasks_output') and portfolio_insights_result.tasks_output:
                                            st.session_state.portfolio_output = portfolio_insights_result.tasks_output[0].raw
                                        else:
                                            st.session_state.portfolio_output = str(portfolio_insights_result)
                                        st.session_state.structured_portfolio = updated_portfolio
                                        logger.info("Updated portfolio with insights reasoning and categories")

                                    except Exception as e:
                                        logger.error(f"Error regenerating portfolio insights: {str(e)}")
                                        # Continue anyway with basic reasoning
                                        st.session_state.portfolio_output = f"Optimized portfolio with {len(new_tickers)} holdings"

                                # STEP 3: Regenerate Risk Analysis
                                with st.spinner("🔄 Recalculating risk analysis..."):
                                    try:
                                        crew_risk_result = QuantitativeAnalysisCrew().analyze_portfolio_risk(
                                            tickers=new_tickers,
                                            weights=new_weights,
                                            user_profile=user_profile,
                                            investment_amount=investment_amount
                                        )

                                        # Store the raw crew output for narrative display
                                        st.session_state.portfolio_risk_crew_result = crew_risk_result

                                        # Transform to UI-expected format (same as initial portfolio)
                                        if isinstance(crew_risk_result, dict) and 'tool_output' in crew_risk_result:
                                            tool_output = crew_risk_result['tool_output']

                                            # Convert to the format expected by the UI
                                            risk_results = {
                                                "portfolio_metrics": {
                                                    "beta": 1.0,  # Default, VaR tool doesn't calculate beta
                                                    "sharpe_ratio": tool_output.get('portfolio_metrics', {}).get('sharpe_ratio', 0.0),
                                                    "value_at_risk_95": float(tool_output.get('var_historical', {}).get('95%', 0.0)) / investment_amount * 100,
                                                    "value_at_risk_99": float(tool_output.get('var_historical', {}).get('99%', 0.0)) / investment_amount * 100,
                                                    "max_drawdown": tool_output.get('portfolio_metrics', {}).get('max_drawdown', 0.0),
                                                    "annual_volatility": tool_output.get('portfolio_metrics', {}).get('annual_volatility', 0.0),
                                                    "expected_annual_return": tool_output.get('portfolio_metrics', {}).get('annual_return', 0.0)
                                                },
                                                "risk_contributions": tool_output.get('risk_contributions', {}),
                                                "risk_alignment": {
                                                    "user_profile": user_profile.get('risk_profile', 'moderate'),
                                                    "risk_score": user_profile.get('risk_score', 0.5),
                                                    "portfolio_risk_level": "aligned",
                                                    "expected_volatility_range": "12%-18%",
                                                    "actual_volatility": f"{tool_output.get('portfolio_metrics', {}).get('annual_volatility', 0.0):.1f}%",
                                                    "adjustment_recommendation": None
                                                },
                                                "diversification_metrics": {
                                                    "number_of_positions": len(new_tickers),
                                                    "effective_number_of_stocks": 0,
                                                    "concentration_risk": "moderate"
                                                },
                                                "value_at_risk_interpretation": {
                                                    "95%": tool_output.get('interpretation', {}).get('95%_var_interpretation', 'Data pending'),
                                                    "99%": f"1% chance of losing more than ${tool_output.get('var_historical', {}).get('99%', 0.0):,.2f} over 10 days"
                                                }
                                            }
                                            st.session_state.portfolio_risk_analysis = risk_results
                                        else:
                                            # Fallback: Parse the narrative output
                                            risk_results = parse_risk_output(
                                                crew_risk_result,
                                                user_profile=user_profile,
                                                investment_amount=investment_amount
                                            )
                                            st.session_state.portfolio_risk_analysis = risk_results

                                    except Exception as e:
                                        logger.error(f"Error regenerating risk analysis: {str(e)}")
                                        # Clear old risk analysis to force regeneration later
                                        if 'portfolio_risk_analysis' in st.session_state:
                                            del st.session_state.portfolio_risk_analysis

                                # STEP 4: Regenerate Projections
                                with st.spinner("🔄 Updating performance projections..."):
                                    try:
                                        from tools.performance_projection_tool import _calculate_projections_impl
                                        from portfoliocrew import parse_timeline_to_years

                                        timeline_years = parse_timeline_to_years(user_profile.get('timeline', '5-10 years'))
                                        risk_profile = user_profile.get('risk_profile', 'moderate').lower()
                                        volatility_map = {
                                            'conservative': 0.10,
                                            'moderate': 0.15,
                                            'aggressive': 0.20
                                        }
                                        annual_volatility = volatility_map.get(risk_profile, 0.15)

                                        projection_result = _calculate_projections_impl(
                                            investment_amount=investment_amount,
                                            expected_annual_return=opt_return,  # Use optimized return
                                            timeline_years=timeline_years,
                                            annual_volatility=annual_volatility
                                        )

                                        st.session_state.projection_data = projection_result
                                    except Exception as e:
                                        logger.error(f"Error regenerating projections: {str(e)}")
                                        # Clear old projections to force regeneration later
                                        if 'projection_data' in st.session_state:
                                            del st.session_state.projection_data

                                # STEP 5: Set flag to hide optimize button and clear optimization result
                                st.session_state.portfolio_was_optimized = True
                                if 'portfolio_optimization_crew' in st.session_state:
                                    del st.session_state.portfolio_optimization_crew

                                st.success("✅ Portfolio successfully updated with optimized allocation!")
                                st.info("📊 Portfolio insights, risk analysis, and projections have been regenerated.")

                            except Exception as e:
                                logger.error(f"Error applying optimized portfolio: {str(e)}")
                                st.error(f"Failed to apply optimization: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc())

                    # Show the apply button
                    if st.button("✅ Apply Optimized Allocation", type="primary"):
                        confirm_apply_optimization()

                # SECTION C: AI Narrative (Expandable)
                with st.expander("🤖 AI Portfolio Manager Recommendations", expanded=False):
                    narrative = opt_result.get('narrative')
                    if narrative:
                        if hasattr(narrative, 'tasks_output') and narrative.tasks_output:
                            st.markdown(escape_markdown_latex(narrative.tasks_output[0].raw))
                        else:
                            st.markdown(escape_markdown_latex(str(narrative)))

        # Show Portfolio Insights if no optimization is active
        elif portfolio_output:
            st.markdown("---")
            st.markdown("## 💡 Portfolio Insights")

            # Add category styling
            st.markdown("""
            <style>
            .insight-category {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 1.5rem;
                margin: 1rem 0;
            }
            .insight-category-title {
                font-size: 1.1rem;
                font-weight: 700;
                margin-bottom: 1rem;
                color: #2C3E50;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            .insight-item {
                margin: 0.5rem 0;
                padding-left: 1.5rem;
                position: relative;
                font-size: 0.95rem;
                line-height: 1.5;
            }
            .insight-item:before {
                content: "✓";
                position: absolute;
                left: 0;
                color: #4ECDC4;
                font-weight: bold;
            }
            .holding-row {
                margin: 0.75rem 0;
                padding: 0.75rem;
                background: #f8f9fa;
                border-radius: 6px;
                border-left: 3px solid #4ECDC4;
            }
            .holding-ticker {
                font-weight: 700;
                color: #2C3E50;
                font-size: 1rem;
            }
            .holding-reasoning {
                color: #555;
                font-size: 0.9rem;
                margin-top: 0.25rem;
                white-space: normal;
                word-wrap: break-word;
                overflow-wrap: break-word;
                line-height: 1.5;
                display: block;
                overflow: visible;
                max-width: 100%;
                text-overflow: clip;
            }
            </style>
            """, unsafe_allow_html=True)

            # Parse portfolio output to extract insights using section headers
            import re

            # Extract sections by headers
            # Risk Management section
            risk_section_match = re.search(r'##\s*RISK MANAGEMENT\s*\n(.*?)(?=##|\Z)', str(portfolio_output), re.IGNORECASE | re.DOTALL)
            risk_items = []
            if risk_section_match:
                risk_section = risk_section_match.group(1)
                # Extract bullet points or dashes
                risk_items = [r.strip() for r in re.findall(r'[-•]\s*([^\n]+)', risk_section) if r.strip()]

            # Performance Outlook section
            performance_section_match = re.search(r'##\s*PERFORMANCE OUTLOOK\s*\n(.*?)(?=##|\Z)', str(portfolio_output), re.IGNORECASE | re.DOTALL)
            expected_return_range = None
            rebalancing_trigger = None
            monitoring_frequency = None
            volatility_expectations = None

            if performance_section_match:
                performance_section = performance_section_match.group(1)
                # Extract expected return
                return_match = re.search(r'Expected Annual Return:\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%', performance_section, re.IGNORECASE)
                if return_match:
                    low = return_match.group(1)
                    high = return_match.group(2)
                    expected_return_range = f"{low}-{high}%"

                # Extract monitoring points
                rebalancing_match = re.search(r'Rebalancing trigger:\s*([^\n]+)', performance_section, re.IGNORECASE)
                if rebalancing_match:
                    rebalancing_trigger = rebalancing_match.group(1).strip()

                frequency_match = re.search(r'Monitoring frequency:\s*([^\n]+)', performance_section, re.IGNORECASE)
                if frequency_match:
                    monitoring_frequency = frequency_match.group(1).strip()

                volatility_match = re.search(r'Volatility expectations:\s*([^\n]+)', performance_section, re.IGNORECASE)
                if volatility_match:
                    volatility_expectations = volatility_match.group(1).strip()

            # Cost Efficiency section
            cost_section_match = re.search(r'##\s*COST EFFICIENCY\s*\n(.*?)(?=##|\Z)', str(portfolio_output), re.IGNORECASE | re.DOTALL)
            cost_items = []
            if cost_section_match:
                cost_section = cost_section_match.group(1)
                # Extract bullet points or dashes
                cost_items = [c.strip() for c in re.findall(r'[-•]\s*([^\n]+)', cost_section) if c.strip()]

            formatted_output = escape_markdown_latex(portfolio_output)

            # Group insights into categories
            col1, col2 = st.columns(2)

            with col1:
                # Asset Allocation - Show each holding with reasoning
                st.markdown('<div class="insight-category"><div class="insight-category-title">🎯 Asset Allocation</div>', unsafe_allow_html=True)

                # Use structured portfolio data (already parsed correctly)
                for alloc in structured_portfolio.get('allocations', []):
                    ticker = alloc.get('ticker', 'N/A')
                    percentage = alloc.get('percentage', 0)
                    reasoning = alloc.get('reasoning', 'Diversification component')
                    st.markdown(f'''
                    <div class="holding-row">
                        <div class="holding-ticker">{ticker} - {percentage:.1f}%</div>
                        <div class="holding-reasoning">{reasoning}</div>
                    </div>
                    ''', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

                # Performance Outlook - Show expected return and KPIs
                st.markdown('<div class="insight-category"><div class="insight-category-title">📊 Performance Outlook</div>', unsafe_allow_html=True)

                if expected_return_range:
                    st.markdown(f'<div class="insight-item">Expected annual return: {expected_return_range}</div>', unsafe_allow_html=True)

                if rebalancing_trigger:
                    st.markdown(f'<div class="insight-item"><strong>Rebalancing:</strong> {rebalancing_trigger}</div>', unsafe_allow_html=True)

                if monitoring_frequency:
                    st.markdown(f'<div class="insight-item"><strong>Monitoring:</strong> {monitoring_frequency}</div>', unsafe_allow_html=True)

                if volatility_expectations:
                    st.markdown(f'<div class="insight-item"><strong>Volatility:</strong> {volatility_expectations}</div>', unsafe_allow_html=True)

                # Fallback if no data extracted
                if not expected_return_range and not rebalancing_trigger:
                    st.markdown('<div class="insight-item">Portfolio designed to align with your investment goals and timeline</div>', unsafe_allow_html=True)
                    st.markdown('<div class="insight-item">Review quarterly and rebalance when allocations drift significantly</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                # Risk Management - Show portfolio-specific risks
                st.markdown('<div class="insight-category"><div class="insight-category-title">⚠️ Risk Management</div>', unsafe_allow_html=True)

                if risk_items:
                    for risk in risk_items[:5]:  # Show up to 5 risks
                        st.markdown(f'<div class="insight-item">{risk}</div>', unsafe_allow_html=True)
                else:
                    # Fallback risks
                    st.markdown('<div class="insight-item">Monitor market volatility and economic conditions</div>', unsafe_allow_html=True)
                    st.markdown('<div class="insight-item">Maintain emergency fund before investing</div>', unsafe_allow_html=True)
                    st.markdown('<div class="insight-item">Review portfolio allocation quarterly</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

                # Cost Efficiency - Show specific expense ratios and fee insights
                st.markdown('<div class="insight-category"><div class="insight-category-title">💰 Cost Efficiency</div>', unsafe_allow_html=True)

                if cost_items:
                    for cost_item in cost_items[:4]:  # Show up to 4 cost items
                        st.markdown(f'<div class="insight-item">{cost_item}</div>', unsafe_allow_html=True)
                else:
                    # Fallback cost insights
                    st.markdown('<div class="insight-item">Low-cost index funds prioritized</div>', unsafe_allow_html=True)
                    st.markdown('<div class="insight-item">Tax-efficient fund structure</div>', unsafe_allow_html=True)
                    st.markdown('<div class="insight-item">Minimal management fees</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

    # ============================================
    # TAB 2: RISK ANALYSIS
    # ============================================
    with tab_risk:
        #st.markdown("### ⚠️ Risk Analysis")

        # Always use the session state version to get latest updates (e.g., after optimization)
        if 'structured_portfolio' in st.session_state:
            structured_portfolio = st.session_state.structured_portfolio

        if structured_portfolio['tickers']:
            structured = structured_portfolio

            # Check if risk analysis already completed
            if 'portfolio_risk_analysis' not in st.session_state:
                with st.spinner("🔄 Analyzing portfolio risk with AI crew..."):
                    try:
                        # Run risk analysis using AI crew (using already imported class)
                        crew_risk_result = QuantitativeAnalysisCrew().analyze_portfolio_risk(
                            tickers=structured['tickers'],
                            weights=structured['weights'],
                            user_profile=user_profile,
                            investment_amount=investment_amount
                        )

                        # Store the raw crew output for narrative display
                        st.session_state.portfolio_risk_crew_result = crew_risk_result

                        # NEW: Extract structured tool output directly
                        if isinstance(crew_risk_result, dict) and 'tool_output' in crew_risk_result:
                            # Use the tool output directly - no parsing needed!
                            tool_output = crew_risk_result['tool_output']

                            # Convert to the format expected by the UI
                            risk_results = {
                                "portfolio_metrics": {
                                    "beta": 1.0,  # Default, VaR tool doesn't calculate beta
                                    "sharpe_ratio": tool_output.get('portfolio_metrics', {}).get('sharpe_ratio', 0.0),
                                    "value_at_risk_95": float(tool_output.get('var_historical', {}).get('95%', 0.0)) / investment_amount * 100,
                                    "value_at_risk_99": float(tool_output.get('var_historical', {}).get('99%', 0.0)) / investment_amount * 100,
                                    "max_drawdown": tool_output.get('portfolio_metrics', {}).get('max_drawdown', 0.0),
                                    "annual_volatility": tool_output.get('portfolio_metrics', {}).get('annual_volatility', 0.0),
                                    "expected_annual_return": tool_output.get('portfolio_metrics', {}).get('annual_return', 0.0)
                                },
                                "risk_contributions": tool_output.get('risk_contributions', {}),
                                "risk_alignment": {
                                    "user_profile": user_profile.get('risk_profile', 'moderate'),
                                    "risk_score": user_profile.get('risk_score', 0.5),
                                    "portfolio_risk_level": "aligned",
                                    "expected_volatility_range": "12%-18%",
                                    "actual_volatility": f"{tool_output.get('portfolio_metrics', {}).get('annual_volatility', 0.0):.1f}%",
                                    "adjustment_recommendation": None
                                },
                                "diversification_metrics": {
                                    "number_of_positions": len(structured['tickers']),
                                    "effective_number_of_stocks": 0,
                                    "concentration_risk": "moderate"
                                },
                                "value_at_risk_interpretation": {
                                    "95%": tool_output.get('interpretation', {}).get('95%_var_interpretation', 'Data pending'),
                                    "99%": f"1% chance of losing more than ${tool_output.get('var_historical', {}).get('99%', 0.0):,.2f} over 10 days"
                                }
                            }
                            st.session_state.portfolio_risk_analysis = risk_results
                        else:
                            # Fallback: Parse the narrative output (old behavior)
                            risk_results = parse_risk_output(
                                crew_risk_result,
                                user_profile=user_profile,
                                investment_amount=investment_amount
                            )
                            st.session_state.portfolio_risk_analysis = risk_results
                    except Exception as e:
                        st.error(f"AI Risk analysis failed: {str(e)}")
                        # Fallback to direct tool call
                        try:
                            portfolio_for_risk = {
                                'tickers': structured['tickers'],
                                'weights': structured['weights'],
                                'user_profile': user_profile,
                                'total_amount': investment_amount
                            }
                            risk_results = risk_assessment(portfolio=portfolio_for_risk, period="1y")
                            st.session_state.portfolio_risk_analysis = risk_results
                        except Exception as e2:
                            st.error(f"Fallback risk analysis also failed: {str(e2)}")
                            risk_results = None
            else:
                risk_results = st.session_state.portfolio_risk_analysis

            # Check for excluded tickers warning
            if 'portfolio_risk_crew_result' in st.session_state:
                crew_risk_result = st.session_state.portfolio_risk_crew_result
                if isinstance(crew_risk_result, dict):
                    # Check if tickers were excluded
                    invalid_tickers = crew_risk_result.get('invalid_tickers', [])
                    valid_tickers = crew_risk_result.get('valid_tickers', [])

                    if invalid_tickers:
                        st.warning(
                            f"⚠️ **Data Limitation**: {len(invalid_tickers)} ticker(s) excluded from risk analysis due to insufficient historical data: "
                            f"**{', '.join(invalid_tickers)}**\n\n"
                            f"Risk metrics calculated using: **{', '.join(valid_tickers)}**"
                        )

            # Display Risk Metrics Dashboard FIRST
            if risk_results:
                st.markdown("#### 📊 Risk Metrics Dashboard")
                # Display risk metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Portfolio Beta",
                        f"{risk_results['portfolio_metrics']['beta']:.2f}",
                        help="Market sensitivity (1.0 = market average)"
                    )
                
                with col2:
                    st.metric(
                        "Sharpe Ratio",
                        f"{risk_results['portfolio_metrics']['sharpe_ratio']:.2f}",
                        help="Risk-adjusted returns"
                    )
                
                with col3:
                    st.metric(
                        "Annual Volatility",
                        f"{risk_results['portfolio_metrics']['annual_volatility']:.1f}%",
                        help="Expected portfolio fluctuation"
                    )
                
                with col4:
                    st.metric(
                        "Max Drawdown",
                        f"{risk_results['portfolio_metrics']['max_drawdown']:.1f}%",
                        help="Worst historical decline"
                    )
                
                # Risk alignment
                st.markdown("#### Risk Profile Alignment")
                alignment = risk_results['risk_alignment']
                if alignment['portfolio_risk_level'] == 'aligned':
                    st.success(f"✅ Portfolio matches your {alignment['user_profile']} risk profile")
                else:
                    st.warning(f"⚠️ Portfolio is {alignment['portfolio_risk_level'].replace('_', ' ')}")
                    if alignment['adjustment_recommendation']:
                        st.info(f"💡 {alignment['adjustment_recommendation']}")
                
                # Value at Risk
                with st.expander("💰 Value at Risk (VaR)"):
                    st.markdown(f"**95% VaR**: {risk_results['value_at_risk_interpretation']['95%']}")
                    st.markdown(f"**99% VaR**: {risk_results['value_at_risk_interpretation']['99%']}")
                
                # Risk contributions
                with st.expander("📊 Individual Stock Risk Contributions"):
                    risk_df = pd.DataFrame([
                        {
                            'Ticker': ticker,
                            'Weight': f"{data['weight']*100:.1f}%",
                            'Volatility': f"{data['volatility']*100:.1f}%",
                            'Risk Contribution': f"{data['percentage_of_risk']:.1f}%"
                        }
                        for ticker, data in risk_results['risk_contributions'].items()
                    ])
                    st.dataframe(risk_df, use_container_width=True)

                # Display AI Risk Summary & Recommendations (non-duplicate content only)
                if 'portfolio_risk_crew_result' in st.session_state:
                    st.markdown("---")
                    with st.expander("💡 Risk Summary & Recommendations", expanded=False):
                        crew_risk_result = st.session_state.portfolio_risk_crew_result

                        # NEW: Handle the new structure with tool_output and narrative
                        if isinstance(crew_risk_result, dict) and 'narrative' in crew_risk_result:
                            narrative_result = crew_risk_result['narrative']
                            if hasattr(narrative_result, 'tasks_output') and narrative_result.tasks_output:
                                crew_output = narrative_result.tasks_output[0].raw
                            else:
                                crew_output = str(narrative_result)
                        elif hasattr(crew_risk_result, 'tasks_output') and crew_risk_result.tasks_output:
                            crew_output = crew_risk_result.tasks_output[0].raw
                        else:
                            crew_output = str(crew_risk_result)

                        # Display the full narrative cleanly (no parsing needed)
                        st.markdown(escape_markdown_latex(crew_output))
            else:
                st.info("📊 Risk analysis will appear here once portfolio is parsed")

    # ============================================
    # TAB 3: PROJECTIONS
    # ============================================
    with tab_projections:
        st.markdown("### 📈 Performance Projections")

        # Display performance chart if we have projection data
        if projection_data:
            # Create and display the chart
            fig = create_performance_chart(projection_data)
            st.plotly_chart(fig, use_container_width=True, key="performance_projection_chart")

            # Display scenario metrics below the chart
            if 'summary' in projection_data:
                col1, col2, col3 = st.columns(3)
                summary = projection_data['summary']

                with col1:
                    st.metric(
                        "📊 Conservative Scenario",
                        summary.get('conservative_final_value', 'N/A'),
                        summary.get('conservative_total_return', 'N/A'),
                        help="If market underperforms"
                    )

                with col2:
                    st.metric(
                        "📊 Expected Scenario",
                        summary.get('expected_final_value', 'N/A'),
                        summary.get('expected_total_return', 'N/A'),
                        help="Most likely outcome"
                    )

                with col3:
                    st.metric(
                        "📊 Optimistic Scenario",
                        summary.get('optimistic_final_value', 'N/A'),
                        summary.get('optimistic_total_return', 'N/A'),
                        help="If market outperforms"
                    )

            # Display AI narrative about projections
            if projection_narrative:
                st.markdown("---")
                st.markdown("#### 💬 What This Means for You")
                st.markdown(escape_markdown_latex(projection_narrative))
            elif projection_data and 'summary' in projection_data:
                # Fallback: Generate simple narrative from projection data
                st.markdown("---")
                st.markdown("#### 💬 What This Means for You")
                summary = projection_data['summary']
                timeline_years = projection_data.get('timeline_years', 5)

                fallback_narrative = f"""
**Investment Outlook**: Based on your ${investment_amount:,.0f} initial investment over {timeline_years} years:

**Conservative Scenario** ({summary.get('conservative_final_value', 'N/A')}):
- Even in challenging market conditions, your portfolio could grow to {summary.get('conservative_final_value', 'N/A')}
- This represents a return of {summary.get('conservative_total_return', 'N/A')}

**Expected Scenario** ({summary.get('expected_final_value', 'N/A')}):
- Under normal market conditions, you're projected to reach {summary.get('expected_final_value', 'N/A')}
- This would be a {summary.get('expected_total_return', 'N/A')} return on your investment

**Optimistic Scenario** ({summary.get('optimistic_final_value', 'N/A')}):
- In favorable market conditions, your portfolio could grow to {summary.get('optimistic_final_value', 'N/A')}
- This represents a potential {summary.get('optimistic_total_return', 'N/A')} return

**Key Takeaways**:
- Your portfolio is designed to align with your **{user_profile.get('risk_profile', 'moderate')}** risk tolerance
- Regular monitoring and rebalancing can help optimize returns
- Consider dollar-cost averaging to reduce market timing risk
                """
                st.markdown(fallback_narrative)
        else:
            st.info("📊 Performance projections will be displayed here after generation.")

    # ============================================
    # TAB 4: BUDGET PLAN
    # ============================================
    with tab_budget:
        st.markdown("### 💰 Budget Plan & Next Steps")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 💵 Investment Breakdown")
            st.metric("Initial Investment", f"${investment_amount:,.0f}")
            st.metric("Recommended Monthly Addition", f"${investment_amount * 0.1:,.0f}", help="10% of initial investment")

            st.markdown("---")
            st.markdown("#### 📅 Timeline")
            st.info(f"**Investment Horizon:** {timeline}")
            st.write(f"Based on your {timeline} timeline, here's what to expect:")
            st.write("• **Short-term (1-2 years):** Focus on stability, monitor quarterly")
            st.write("• **Mid-term (3-5 years):** Balanced growth, rebalance annually")
            st.write("• **Long-term (10+ years):** Maximize growth, review semi-annually")

        with col2:
            st.markdown("#### 🎯 Action Plan")
            st.markdown("""
            ✅ **Step 1:** Open a brokerage account (if needed)
            - Recommended: Fidelity, Vanguard, or Schwab

            ✅ **Step 2:** Fund your account
            - Transfer ${:,.0f}

            ✅ **Step 3:** Execute trades
            - Use the allocation percentages above
            - Consider fractional shares for precise allocation

            ✅ **Step 4:** Set up monitoring
            - Review quarterly
            - Rebalance when allocations drift >5%

            ✅ **Step 5:** Stay the course
            - Don't panic sell during downturns
            - Consider dollar-cost averaging for additions
            """.format(investment_amount))

    # ============================================
    # PORTFOLIO INSIGHTS SECTION (DISABLED)
    # Now displayed inside Overview tab instead of after all tabs
    # ============================================
    if False:  # Disabled - moved to Overview tab
        # Add category styling
        st.markdown("""
        <style>
        .insight-category {
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
        }
        .insight-category-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: #2C3E50;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .insight-item {
            margin: 0.5rem 0;
            padding-left: 1.5rem;
            position: relative;
            font-size: 0.95rem;
            line-height: 1.5;
        }
        .insight-item:before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #4ECDC4;
            font-weight: bold;
        }
        .holding-row {
            margin: 0.75rem 0;
            padding: 0.75rem;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 3px solid #4ECDC4;
        }
        .holding-ticker {
            font-weight: 700;
            color: #2C3E50;
            font-size: 1rem;
        }
        .holding-reasoning {
            color: #555;
            font-size: 0.9rem;
            margin-top: 0.25rem;
            white-space: normal;
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.5;
            display: block;
            overflow: visible;
            max-width: 100%;
            text-overflow: clip;
        }
        </style>
        """, unsafe_allow_html=True)

        # Parse portfolio output to extract insights using section headers
        import re

        # Extract holdings with reasoning (format: TICKER (Category) - XX% ($X,XXX) - Reasoning)
        holdings_pattern = r'([A-Z]{1,5})\s*\([^)]+\)\s*-\s*(\d+(?:\.\d+)?%)\s*\(\$[\d,]+\)\s*-\s*([^\n]+)'
        holdings_matches = re.findall(holdings_pattern, str(portfolio_output))

        # Extract sections by headers
        # Risk Management section
        risk_section_match = re.search(r'##\s*RISK MANAGEMENT\s*\n(.*?)(?=##|\Z)', str(portfolio_output), re.IGNORECASE | re.DOTALL)
        risk_items = []
        if risk_section_match:
            risk_section = risk_section_match.group(1)
            # Extract bullet points or dashes
            risk_items = [r.strip() for r in re.findall(r'[-•]\s*([^\n]+)', risk_section) if r.strip()]

        # Performance Outlook section
        performance_section_match = re.search(r'##\s*PERFORMANCE OUTLOOK\s*\n(.*?)(?=##|\Z)', str(portfolio_output), re.IGNORECASE | re.DOTALL)
        expected_return_range = None
        rebalancing_trigger = None
        monitoring_frequency = None
        volatility_expectations = None

        if performance_section_match:
            performance_section = performance_section_match.group(1)
            # Extract expected return
            return_match = re.search(r'Expected Annual Return:\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%', performance_section, re.IGNORECASE)
            if return_match:
                low = return_match.group(1)
                high = return_match.group(2)
                expected_return_range = f"{low}-{high}%"

            # Extract monitoring points
            rebalancing_match = re.search(r'Rebalancing trigger:\s*([^\n]+)', performance_section, re.IGNORECASE)
            if rebalancing_match:
                rebalancing_trigger = rebalancing_match.group(1).strip()

            frequency_match = re.search(r'Monitoring frequency:\s*([^\n]+)', performance_section, re.IGNORECASE)
            if frequency_match:
                monitoring_frequency = frequency_match.group(1).strip()

            volatility_match = re.search(r'Volatility expectations:\s*([^\n]+)', performance_section, re.IGNORECASE)
            if volatility_match:
                volatility_expectations = volatility_match.group(1).strip()

        # Cost Efficiency section
        cost_section_match = re.search(r'##\s*COST EFFICIENCY\s*\n(.*?)(?=##|\Z)', str(portfolio_output), re.IGNORECASE | re.DOTALL)
        cost_items = []
        if cost_section_match:
            cost_section = cost_section_match.group(1)
            # Extract bullet points or dashes
            cost_items = [c.strip() for c in re.findall(r'[-•]\s*([^\n]+)', cost_section) if c.strip()]

        formatted_output = escape_markdown_latex(portfolio_output)

        # Group insights into categories
        col1, col2 = st.columns(2)

        with col1:
            # Asset Allocation - Show each holding with reasoning
            st.markdown('<div class="insight-category"><div class="insight-category-title">🎯 Asset Allocation</div>', unsafe_allow_html=True)
            if holdings_matches:
                for ticker, percentage, reasoning in holdings_matches:
                    st.markdown(f'''
                    <div class="holding-row">
                        <div class="holding-ticker">{ticker} - {percentage}</div>
                        <div class="holding-reasoning">{reasoning}</div>
                    </div>
                    ''', unsafe_allow_html=True)
            else:
                # Fallback if pattern doesn't match
                for alloc in structured_portfolio.get('allocations', []):
                    ticker = alloc.get('ticker', 'N/A')
                    percentage = alloc.get('percentage', 0)
                    reasoning = alloc.get('reasoning', 'Diversification component')
                    st.markdown(f'''
                    <div class="holding-row">
                        <div class="holding-ticker">{ticker} - {percentage}%</div>
                        <div class="holding-reasoning">{reasoning}</div>
                    </div>
                    ''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Performance Outlook - Show expected return and KPIs
            st.markdown('<div class="insight-category"><div class="insight-category-title">📊 Performance Outlook</div>', unsafe_allow_html=True)

            if expected_return_range:
                st.markdown(f'<div class="insight-item">Expected annual return: {expected_return_range}</div>', unsafe_allow_html=True)

            if rebalancing_trigger:
                st.markdown(f'<div class="insight-item"><strong>Rebalancing:</strong> {rebalancing_trigger}</div>', unsafe_allow_html=True)

            if monitoring_frequency:
                st.markdown(f'<div class="insight-item"><strong>Monitoring:</strong> {monitoring_frequency}</div>', unsafe_allow_html=True)

            if volatility_expectations:
                st.markdown(f'<div class="insight-item"><strong>Volatility:</strong> {volatility_expectations}</div>', unsafe_allow_html=True)

            # Fallback if no data extracted
            if not expected_return_range and not rebalancing_trigger:
                st.markdown('<div class="insight-item">Portfolio designed to align with your investment goals and timeline</div>', unsafe_allow_html=True)
                st.markdown('<div class="insight-item">Review quarterly and rebalance when allocations drift significantly</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            # Risk Management - Show portfolio-specific risks
            st.markdown('<div class="insight-category"><div class="insight-category-title">⚠️ Risk Management</div>', unsafe_allow_html=True)

            if risk_items:
                for risk in risk_items[:5]:  # Show up to 5 risks
                    st.markdown(f'<div class="insight-item">{risk}</div>', unsafe_allow_html=True)
            else:
                # Fallback risks
                st.markdown('<div class="insight-item">Monitor market volatility and economic conditions</div>', unsafe_allow_html=True)
                st.markdown('<div class="insight-item">Maintain emergency fund before investing</div>', unsafe_allow_html=True)
                st.markdown('<div class="insight-item">Review portfolio allocation quarterly</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            # Cost Efficiency - Show specific expense ratios and fee insights
            st.markdown('<div class="insight-category"><div class="insight-category-title">💰 Cost Efficiency</div>', unsafe_allow_html=True)

            if cost_items:
                for cost_item in cost_items[:4]:  # Show up to 4 cost items
                    st.markdown(f'<div class="insight-item">{cost_item}</div>', unsafe_allow_html=True)
            else:
                # Fallback cost insights
                st.markdown('<div class="insight-item">Low-cost index funds prioritized</div>', unsafe_allow_html=True)
                st.markdown('<div class="insight-item">Tax-efficient fund structure</div>', unsafe_allow_html=True)
                st.markdown('<div class="insight-item">Minimal management fees</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)
            
            # Display optimization results (prioritize AI crew results)
            if 'portfolio_optimization_crew' in st.session_state:
                st.markdown("#### 🤖 AI Crew Optimization Results")
                opt_crew_result = st.session_state.portfolio_optimization_crew
                
                # Extract and display AI crew results
                if hasattr(opt_crew_result, 'tasks_output') and opt_crew_result.tasks_output:
                    crew_output = opt_crew_result.tasks_output[0].raw
                    st.markdown("##### AI Portfolio Manager Recommendations:")
                    st.markdown(escape_markdown_latex(crew_output))
                else:
                    st.markdown(escape_markdown_latex(str(opt_crew_result)))
                
                st.markdown("---")
            
            if 'portfolio_optimization' in st.session_state:
                opt_results = st.session_state.portfolio_optimization
                st.markdown("#### 📊 Quantitative Optimization Metrics")
                
                # Show comparison
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### Current Portfolio")
                    current = opt_results['current_portfolio']
                    st.metric("Expected Return", f"{current['expected_return']*100:.1f}%")
                    st.metric("Volatility", f"{current['volatility']*100:.1f}%")
                    st.metric("Sharpe Ratio", f"{current['sharpe_ratio']:.2f}")
                
                with col2:
                    st.markdown("#### Optimized Portfolio")
                    enhanced = opt_results['enhanced_portfolio']
                    improvements = opt_results['improvements']
                    
                    st.metric(
                        "Expected Return", 
                        f"{enhanced['expected_return']*100:.1f}%",
                        f"{improvements['return_increase']:.1f}%"
                    )
                    st.metric(
                        "Volatility", 
                        f"{enhanced['volatility']*100:.1f}%",
                        f"{improvements['risk_change']:.1f}%"
                    )
                    st.metric(
                        "Sharpe Ratio", 
                        f"{enhanced['sharpe_ratio']:.2f}",
                        f"{improvements['sharpe_increase']:.2f}"
                    )
                
                # Show recommendations
                if opt_results.get('recommendations'):
                    st.markdown("#### 💡 Optimization Recommendations")
                    for rec in opt_results['recommendations']:
                        if rec['action'] == 'increase':
                            st.success(f"📈 **{rec['ticker']}**: Increase by {rec['percentage_change']:.1f}% (${rec['dollar_amount']:,.2f})")
                        else:
                            st.warning(f"📉 **{rec['ticker']}**: Decrease by {abs(rec['percentage_change']):.1f}% (${rec['dollar_amount']:,.2f})")
                
                    if st.button("✅ Apply Optimized Allocation", type="primary"):
                        st.info("🚧 Feature coming soon: Apply optimization and rebalance portfolio")

    # ============================================
    # QUICK ACTIONS SECTION (COMMENTED OUT)
    # ============================================
    # st.markdown("---")
    # st.markdown("### 📌 Quick Actions")
    #
    # col1, col2, col3 = st.columns(3)
    # with col1:
    #     if st.button("📈 Analyze Individual Stocks", type="secondary", use_container_width=True):
    #         st.session_state.show_portfolio_results = False
    #         st.session_state.show_main_app = True
    #         st.rerun()
    #
    # with col2:
    #     if st.button("📊 View Detailed Analysis", type="secondary", use_container_width=True):
    #         st.info("Coming soon: Detailed stock-by-stock analysis")
    #
    # with col3:
    #     if st.button("📖 Educational Resources", type="secondary", use_container_width=True):
    #         st.info("Scroll down to see educational content")

    # ============================================
    # SECTION 3: Education Content (Bottom, Collapsible)
    # ============================================
    st.markdown("---")

    with st.expander("📚 Investment Education & Learning Resources", expanded=False):
        st.markdown("### 📚 Investment Education")

        # Check if education content already exists in session state
        if 'education_content' in st.session_state:
            education_result = st.session_state.education_content
            if isinstance(education_result, dict) and 'content' in education_result:
                education_content = education_result['content']
                if hasattr(education_content, 'tasks_output') and education_content.tasks_output:
                    st.markdown(escape_markdown_latex(education_content.tasks_output[0].raw))
                else:
                    st.markdown(escape_markdown_latex(str(education_content)))
            else:
                st.markdown(escape_markdown_latex(str(education_result)))
        else:
            # Trigger education generation if not available
            if st.button("📖 Generate Educational Content", type="primary"):
                with st.spinner("🎓 Creating personalized education content..."):
                    try:
                        # Get the portfolio output for education
                        portfolio_text = portfolio_output if portfolio_output else "Portfolio data"

                        education_result = portfoliocrew.create_education(
                            amount=investment_amount,  # Pass as number
                            portfolio=portfolio_text,
                            user_profile=user_profile
                        )
                        if education_result:
                            # Store and display
                            st.session_state.education_content = education_result

                            # Extract content from the education result
                            if isinstance(education_result, dict) and 'content' in education_result:
                                education_content = education_result['content']
                                if hasattr(education_content, 'tasks_output') and education_content.tasks_output:
                                    st.markdown(escape_markdown_latex(education_content.tasks_output[0].raw))
                                else:
                                    st.markdown(escape_markdown_latex(str(education_content)))
                            else:
                                st.markdown(escape_markdown_latex(str(education_result)))
                    except Exception as e:
                        st.error(f"Failed to generate education content: {str(e)}")
        
        # Generic education content
        with st.expander("ℹ️ Understanding Your Portfolio"):
            st.markdown("""
            **Why this portfolio?**
            - Matched to your risk tolerance and timeline
            - Diversified across asset classes
            - Optimized for your investment amount
            - Suitable for your experience level
            
            **Next Steps:**
            1. Open a brokerage account if you haven't already
            2. Start with the recommended allocation
            3. Review and rebalance quarterly
            4. Continue learning about each investment
            """)


def show_portfolio_landing():
    """Portfolio landing page - shows latest saved portfolio."""

    st.title("📊 My Portfolio")

    portfolio = st.session_state.get('latest_portfolio')

    if not portfolio:
        st.info("No saved portfolios found.")
        if st.button("Create Your First Portfolio", type="primary"):
            st.session_state.show_portfolio_generation = True
            st.session_state.show_portfolio_landing = False
            st.rerun()
        return

    # Display portfolio header
    st.markdown(f"### {portfolio.get('name', 'My Portfolio')}")
    created_at = portfolio.get('created_at', 'N/A')
    st.caption(f"Created: {created_at}")

    # Quick metrics
    col1, col2, col3 = st.columns(3)

    allocations = portfolio.get('allocations', [])
    total_amount = sum(float(a.get('amount', 0)) for a in allocations)

    with col1:
        st.metric("Portfolio Value", f"${total_amount:,.2f}")
    with col2:
        # Extract from preferences or default
        prefs = portfolio.get('preferences', {})
        risk = prefs.get('risk_tolerance', 'Moderate')
        st.metric("Risk Profile", risk.title())
    with col3:
        st.metric("Holdings", len(allocations))

    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔍 View Full Analysis", type="primary", use_container_width=True):
            # Will be implemented in Phase 4
            load_and_refresh_portfolio(portfolio)

    with col2:
        if st.button("✏️ Create New Portfolio", use_container_width=True):
            st.session_state.show_portfolio_generation = True
            st.session_state.show_portfolio_landing = False
            st.rerun()

    with col3:
        if st.button("🗑️ Delete Portfolio", use_container_width=True):
            st.warning("Delete functionality coming soon")

    # Asset allocation summary
    st.markdown("---")
    st.markdown("### 📋 Asset Allocation")

    for alloc in allocations[:5]:  # Show top 5
        ticker = alloc.get('ticker', 'N/A')
        percentage = float(alloc.get('percentage', 0))
        amount = float(alloc.get('amount', 0))
        st.markdown(f"**{ticker}**: {percentage:.1f}% (${amount:,.2f})")

    if len(allocations) > 5:
        st.caption(f"...and {len(allocations) - 5} more holdings")


def load_and_refresh_portfolio(portfolio):
    """Load saved portfolio and regenerate AI analysis with fresh data."""

    with st.spinner("🔄 Loading portfolio and refreshing analysis..."):

        # Extract data from saved portfolio
        allocations = portfolio.get('allocations', [])
        tickers = [a['ticker'] for a in allocations]
        weights = [float(a['percentage']) / 100 for a in allocations]  # Convert % to decimal
        investment_amount = sum(float(a.get('amount', 0)) for a in allocations)
        user_profile = portfolio.get('preferences', {})

        # Reconstruct structured portfolio
        structured_portfolio = {
            'tickers': tickers,
            'weights': weights,
            'categories': [a.get('category', 'Stock') for a in allocations]
        }

        st.session_state.structured_portfolio = structured_portfolio
        st.session_state.investment_amount = investment_amount
        st.session_state.user_profile = user_profile
        st.session_state.current_portfolio_id = portfolio.get('portfolio_id')

        # STEP 1: Regenerate portfolio insights
        with st.spinner("🤖 Regenerating portfolio insights with latest market data..."):
            try:
                from portfoliocrew import PortfolioCrew

                portfolio_output = PortfolioCrew().generate_portfolio(
                    user_profile=user_profile,
                    preferences=user_profile,
                    override_allocation={'tickers': tickers, 'weights': weights}
                )
                st.session_state.portfolio_output = portfolio_output
            except Exception as e:
                logger.error(f"Error regenerating insights: {str(e)}")
                st.session_state.portfolio_output = "Portfolio loaded successfully."

        # STEP 2: Regenerate risk analysis
        with st.spinner("⚠️ Analyzing current risk metrics..."):
            try:
                crew_risk_result = QuantitativeAnalysisCrew().analyze_portfolio_risk(
                    tickers=tickers,
                    weights=weights,
                    user_profile=user_profile,
                    investment_amount=investment_amount
                )
                st.session_state.portfolio_risk_crew_result = crew_risk_result

                # Transform to expected format (same as in show_portfolio_results)
                if isinstance(crew_risk_result, dict) and 'tool_output' in crew_risk_result:
                    tool_output = crew_risk_result['tool_output']
                    risk_results = {
                        "portfolio_metrics": {
                            "beta": 1.0,
                            "sharpe_ratio": tool_output.get('portfolio_metrics', {}).get('sharpe_ratio', 0.0),
                            "value_at_risk_95": float(tool_output.get('var_historical', {}).get('95%', 0.0)) / investment_amount * 100,
                            "value_at_risk_99": float(tool_output.get('var_historical', {}).get('99%', 0.0)) / investment_amount * 100,
                            "max_drawdown": tool_output.get('portfolio_metrics', {}).get('max_drawdown', 0.0),
                            "annual_volatility": tool_output.get('portfolio_metrics', {}).get('annual_volatility', 0.0),
                            "expected_annual_return": tool_output.get('portfolio_metrics', {}).get('annual_return', 0.0)
                        },
                        "risk_contributions": tool_output.get('risk_contributions', {}),
                        "risk_alignment": {
                            "user_profile": user_profile.get('risk_profile', 'moderate'),
                            "risk_score": user_profile.get('risk_score', 0.5),
                            "portfolio_risk_level": "aligned",
                            "expected_volatility_range": "12%-18%",
                            "actual_volatility": f"{tool_output.get('portfolio_metrics', {}).get('annual_volatility', 0.0):.1f}%",
                            "adjustment_recommendation": None
                        },
                        "diversification_metrics": {
                            "number_of_positions": len(tickers),
                            "effective_number_of_stocks": 0,
                            "concentration_risk": "moderate"
                        },
                        "value_at_risk_interpretation": {
                            "95%": tool_output.get('interpretation', {}).get('95%_var_interpretation', 'Data pending'),
                            "99%": f"1% chance of losing more than ${tool_output.get('var_historical', {}).get('99%', 0.0):,.2f} over 10 days"
                        }
                    }
                    st.session_state.portfolio_risk_analysis = risk_results
                else:
                    # Fallback: Parse the narrative output
                    risk_results = parse_risk_output(
                        crew_risk_result,
                        user_profile=user_profile,
                        investment_amount=investment_amount
                    )
                    st.session_state.portfolio_risk_analysis = risk_results

            except Exception as e:
                logger.error(f"Error regenerating risk: {str(e)}")

        # STEP 3: Regenerate projections
        with st.spinner("📈 Calculating updated performance projections..."):
            try:
                from tools.performance_projection_tool import _calculate_projections_impl
                from portfoliocrew import parse_timeline_to_years

                timeline_years = parse_timeline_to_years(user_profile.get('timeline', '5-10 years'))
                risk_profile = user_profile.get('risk_profile', 'moderate').lower()
                volatility_map = {
                    'conservative': 0.10,
                    'moderate': 0.15,
                    'aggressive': 0.20
                }
                annual_volatility = volatility_map.get(risk_profile, 0.15)

                projection_result = _calculate_projections_impl(
                    investment_amount=investment_amount,
                    expected_annual_return=0.097,  # Default, can be extracted from portfolio
                    timeline_years=timeline_years,
                    annual_volatility=annual_volatility
                )
                st.session_state.projection_data = projection_result
            except Exception as e:
                logger.error(f"Error regenerating projections: {str(e)}")

        # Navigate to results page
        st.session_state.show_portfolio_results = True
        st.session_state.show_portfolio_landing = False
        st.rerun()


def save_user_preferences_to_api(preferences: dict):
    """Save user preferences to the API backend."""
    try:
        user_email = st.session_state.get('user_email')
        if user_email and not st.session_state.get('demo_mode', False):
            # Use the existing API client to save preferences
            success = api_client.save_user_preferences(user_email, preferences)
            if success:
                # Extract user ID for tracking (if available)
                user_id = st.session_state.get('user_data', {}).get('id', user_email)
                
                # Map new comprehensive structure to legacy tracking format for backward compatibility
                legacy_format = {
                    'experience': map_age_to_experience(preferences.get('demographics', {}).get('age_range', '')),
                    'risk_tolerance': preferences.get('risk_assessment', {}).get('risk_profile', ''),
                    'initial_amount': preferences.get('investment_goals', {}).get('initial_investment_amount', ''),
                    'timestamp': preferences.get('onboarding_date', datetime.now().isoformat())
                }
                
                # Track preferences event for analytics
                api_client.track_preferences_event(user_id, legacy_format)
                api_client.increment_feature_usage(user_id, 'onboarding_completed', 1)
        else:
            st.warning("⚠️ Preferences saved locally but couldn't sync to server")
    except Exception as e:
        # Silent fail - preferences are still saved in session state
        pass


def map_age_to_experience(age_range: str) -> str:
    """Map age range to experience level for backward compatibility."""
    if "16-20" in age_range or "21-25" in age_range:
        return "beginner"
    elif "26-30" in age_range or "31-35" in age_range:
        return "intermediate"
    else:
        return "experienced"


def show_demographics_step():
    """Step 1: Collect demographics and primary investment goals."""
    st.markdown("### 🌟 Tell us about yourself")
    st.markdown("This helps us personalize your experience and provide age-appropriate guidance.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Your age range:**")
        age_range = st.selectbox(
            "Choose your age group",
            ["16-20 (High school/Early college)", "21-25 (College/Entry career)", 
             "26-30 (Early career)", "31-35 (Establishing career)", "36+ (Experienced)"],
            help="💡 Different life stages have different investment strategies"
        )
        
        st.markdown("**Your current income range:**")
        income_range = st.selectbox(
            "Choose your income bracket",
            ["Student/No income", "$0-25k", "$25k-50k", "$50k-75k", "$75k+"],
            help="💡 This helps us suggest appropriate investment amounts"
        )
    
    with col2:
        st.markdown("**What's your primary goal?**")
        primary_goal = st.selectbox(
            "Choose your main objective",
            ["Learn investing basics", "Build emergency fund", "Save for a major purchase", 
             "Long-term wealth building", "Retirement planning", "Generate side income"],
            help="💡 Your goal shapes your investment strategy"
        )
        
        st.markdown("**Investment timeline:**")
        timeline = st.selectbox(
            "When do you need this money?",
            ["Learning only (no timeline)", "1-2 years", "3-5 years", "5-10 years", "10+ years"],
            help="💡 Longer timelines allow for more growth-focused strategies"
        )
    
    # Educational tip
    st.info("💡 **Quick Tip:** Starting early is your biggest advantage! Even small amounts can grow significantly over time thanks to compound interest.")
    
    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Continue to Risk Assessment", type="primary", use_container_width=True):
            st.session_state.onboarding_data.update({
                'age_range': age_range,
                'income_range': income_range,
                'primary_goal': primary_goal,
                'timeline': timeline
            })
            st.session_state.onboarding_step = 2
            st.rerun()

def show_risk_scenarios_step():
    """Step 2: Scenario-based risk assessment with real-world examples."""
    st.markdown("### 🎯 How do you handle uncertainty?")
    st.markdown("Let's explore different scenarios to understand your comfort level with risk.")
    
    # Scenario 1: Market volatility
    st.markdown("**Scenario 1: Market Roller Coaster 🎢**")
    st.markdown("You invested $1,000 six months ago. The stock market has been volatile:")
    
    scenario1_options = [
        "😰 I'd sell immediately to avoid further losses (-20% → -$200)",
        "😐 I'd hold and hope it recovers soon (-20% → -$200)", 
        "😊 I'd hold knowing markets recover long-term (-20% → -$200)",
        "🚀 I'd buy more while prices are low! (-20% → -$200)"
    ]
    scenario1 = st.radio("Your $1,000 is now worth $800. What do you do?", scenario1_options, key="scenario1")
    
    # Scenario 2: Investment choice
    st.markdown("**Scenario 2: Investment Decision 💰**")
    st.markdown("You have $500 to invest and three options:")
    
    scenario2_options = [
        "🏦 High-yield savings (guaranteed 4% per year)",
        "📈 Broad market fund (historically 8-10%, but volatile)",
        "🎲 Individual growth stocks (potentially 15%+, high risk)",
        "🔄 Mix of all three for balance"
    ]
    scenario2 = st.radio("Which appeals to you most?", scenario2_options, key="scenario2")
    
    # Scenario 3: Time horizon
    st.markdown("**Scenario 3: Timeline Reality Check ⏰**")
    
    age_range = st.session_state.onboarding_data.get('age_range', '')
    if '16-20' in age_range or '21-25' in age_range:
        st.markdown("Since you're young, you have **decades** to invest before retirement.")
        scenario3_text = "With 40+ years until retirement, you can:"
    else:
        st.markdown("You have significant time for long-term investing.")
        scenario3_text = "With your timeline, you can:"
    
    scenario3_options = [
        "🐌 Play it safe with mostly bonds and savings",
        "⚖️ Balance between growth and safety (60/40 stocks/bonds)",
        "🚀 Focus on growth with mostly stocks",
        "🤔 I'm not sure what's best for my situation"
    ]
    scenario3 = st.radio(scenario3_text, scenario3_options, key="scenario3")
    
    # Educational insight based on age
    if '16-20' in age_range or '21-25' in age_range:
        st.success("🎓 **Young Investor Advantage:** Your age is your superpower! Time lets you ride out market ups and downs while your investments grow.")
    
    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.onboarding_step = 1
            st.rerun()
    with col3:
        if st.button("Continue →", type="primary", use_container_width=True):
            # Calculate risk profile based on scenarios
            risk_score = calculate_risk_score(scenario1, scenario2, scenario3)
            st.session_state.onboarding_data.update({
                'scenario1': scenario1,
                'scenario2': scenario2, 
                'scenario3': scenario3,
                'risk_score': risk_score,
                'risk_profile': get_risk_profile(risk_score)
            })
            st.session_state.onboarding_step = 3
            st.rerun()

def show_investment_amount_step():
    """Step 3: Investment amount with contextual comparisons and guidance."""
    st.markdown("### 💰 Let's talk money")
    st.markdown("How much can you comfortably invest? Remember: only invest what you can afford to lose!")
    
    # Get user context
    age_range = st.session_state.onboarding_data.get('age_range', '')
    income_range = st.session_state.onboarding_data.get('income_range', '')
    
    # Contextual guidance based on income
    if income_range == "Student/No income":
        st.info("💡 **Student Tip:** Start small! Even $25-50 monthly helps you learn. Focus on paper trading or micro-investing apps first.")
        amount_options = ["$0 (learning mode)", "$25-50", "$50-100", "$100-250", "$250+"]
    elif "$0-25k" in income_range:
        st.info("💡 **Starting Out:** Build your emergency fund first! Then start with whatever you're comfortable losing - even $50 is a great start.")
        amount_options = ["$25-50", "$50-100", "$100-250", "$250-500", "$500+"]
    elif "$25k-50k" in income_range:
        st.info("💡 **Building Wealth:** Consider the 50/30/20 rule: 50% needs, 30% wants, 20% savings/investing.")
        amount_options = ["$100-250", "$250-500", "$500-1,000", "$1,000-2,500", "$2,500+"]
    else:
        st.info("💡 **Growing Wealth:** You're in a strong position! Consider maximizing tax-advantaged accounts first.")
        amount_options = ["$500-1,000", "$1,000-2,500", "$2,500-5,000", "$5,000-10,000", "$10,000+"]
    
    initial_amount = st.selectbox(
        "Choose your starting investment amount:",
        amount_options,
        help="💡 You can always add more later as you get comfortable"
    )
    
    # Contextual comparison
    st.markdown("**💭 Putting this in perspective:**")
    if "25-50" in initial_amount:
        st.markdown("- About 1-2 restaurant meals")
        st.markdown("- A streaming service subscription") 
        st.markdown("- Perfect for learning without stress!")
    elif "50-100" in initial_amount:
        st.markdown("- A nice dinner out")
        st.markdown("- A video game or two")
        st.markdown("- Great starting point for hands-on learning")
    elif "100-250" in initial_amount:
        st.markdown("- A weekend shopping trip")
        st.markdown("- A few tanks of gas")
        st.markdown("- Solid foundation for your investment journey")
    elif "250-500" in initial_amount:
        st.markdown("- A weekend getaway")
        st.markdown("- New phone or laptop upgrade")
        st.markdown("- Meaningful start to wealth building")
    
    # Emergency fund check
    st.markdown("**🏦 Quick financial health check:**")
    has_emergency = st.checkbox(
        "I have at least $500-1,000 saved for emergencies",
        help="💡 Emergency funds should come before investing!"
    )
    
    if not has_emergency and initial_amount not in ["$0 (learning mode)", "$25-50"]:
        st.warning("⚠️ **Consider building an emergency fund first!** This protects your investments by preventing early withdrawals.")
    
    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.onboarding_step = 2
            st.rerun()
    with col3:
        if st.button("Continue →", type="primary", use_container_width=True):
            st.session_state.onboarding_data.update({
                'initial_amount': initial_amount,
                'has_emergency_fund': has_emergency
            })
            st.session_state.onboarding_step = 4
            st.rerun()

def show_first_analysis_tutorial():
    """Step 4: Interactive tutorial for first stock analysis."""
    st.markdown("### 📈 Your First Stock Analysis")
    st.markdown("Let's walk through analyzing a real company together!")
    
    # Tutorial introduction
    st.info("🎓 **Tutorial Mode:** We'll analyze a well-known company to show you how our AI works. You'll learn what to look for in any investment!")
    
    # Suggest beginner-friendly stocks based on user profile
    age_range = st.session_state.onboarding_data.get('age_range', '')
    primary_goal = st.session_state.onboarding_data.get('primary_goal', '')
    
    suggested_stocks = get_beginner_stock_suggestions(age_range, primary_goal)
    
    st.markdown("**🌟 Great starter companies to analyze:**")
    for stock, reason in suggested_stocks.items():
        st.markdown(f"- **{stock}**: {reason}")
    
    st.markdown("**Choose a company to analyze:**")
    tutorial_stock = st.selectbox(
        "Pick one for your first analysis:",
        list(suggested_stocks.keys()),
        help="💡 These are all well-established companies perfect for learning"
    )
    
    # What they'll learn
    st.markdown("**📚 In this analysis, you'll learn about:**")
    learning_points = [
        "📊 **Financial Health**: Is the company profitable and growing?",
        "💰 **Stock Valuation**: Is the stock fairly priced?", 
        "🎯 **Business Model**: How does the company make money?",
        "📈 **Growth Potential**: What's the outlook for the future?",
        "⚠️ **Risk Factors**: What could go wrong?"
    ]
    
    for point in learning_points:
        st.markdown(point)
    
    # Set expectations
    st.success("🔍 **What to expect:** Our AI will analyze this company from multiple angles and explain everything in simple terms. This takes about 2-3 minutes.")
    
    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.onboarding_step = 3
            st.rerun()
    with col3:
        if st.button("Start Analysis Tutorial", type="primary", use_container_width=True):
            st.session_state.onboarding_data.update({
                'tutorial_stock': tutorial_stock,
                'suggested_stocks': suggested_stocks
            })
            st.session_state.onboarding_step = 5
            st.rerun()

def show_action_plan_step():
    """Step 5: Generate personalized action plan and complete onboarding."""
    st.markdown("### 🎯 Your Personalized Investment Plan")
    
    # Get user data
    data = st.session_state.onboarding_data
    age_range = data.get('age_range', '')
    primary_goal = data.get('primary_goal', '')
    timeline = data.get('timeline', '')
    risk_profile = data.get('risk_profile', 'Moderate')
    initial_amount = data.get('initial_amount', '')
    
    # Generate personalized recommendations
    plan = generate_personalized_plan(data)
    
    st.markdown("**🌟 Based on your responses, here's your personalized roadmap:**")
    
    # Quick summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Your Profile", f"{age_range.split(' ')[0]} • {risk_profile}")
        st.metric("Primary Goal", primary_goal)
    with col2:
        st.metric("Timeline", timeline)
        st.metric("Starting Amount", initial_amount)
    
    # Personalized recommendations
    st.markdown("**📋 Your Action Plan:**")
    for i, action in enumerate(plan['actions'], 1):
        st.markdown(f"{i}. {action}")
    
    # Achievement system preview
    st.markdown("**🏆 Your Achievement Journey:**")
    achievements = [
        "🎓 **Knowledge Seeker**: Complete your first analysis (Ready to unlock!)",
        "📈 **Market Explorer**: Analyze 5 different companies",
        "🧠 **Wise Investor**: Create your first watchlist",
        "🚀 **Portfolio Builder**: Track your investment performance",
        "💎 **Long-term Thinker**: Hold an analysis for 30+ days"
    ]
    
    for achievement in achievements:
        st.markdown(achievement)
    
    # Next steps
    st.success(f"🎉 **Ready to start!** Your first analysis of {data.get('tutorial_stock', 'a great company')} will unlock your first achievement.")
    
    # Save preferences
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Complete Setup & Start Analysis", type="primary", use_container_width=True):
            # Save all onboarding data as user preferences
            save_enhanced_user_preferences(st.session_state.onboarding_data)
            st.session_state.onboarding_complete = True
            st.session_state.first_analysis_stock = data.get('tutorial_stock', 'AAPL')
            
            # Track onboarding completion
            api_client.track_event('onboarding_completed', {
                'age_range': age_range,
                'risk_profile': risk_profile,
                'primary_goal': primary_goal,
                'completion_time': datetime.utcnow().isoformat()
            })
            
            st.balloons()
            st.success("🎉 Setup complete! Starting your first analysis...")
            st.rerun()
    
    # Back button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Back"):
            st.session_state.onboarding_step = 4
            st.rerun()

def calculate_risk_score(scenario1, scenario2, scenario3):
    """Calculate risk tolerance score from scenario responses."""
    score = 0
    
    # Scenario 1 scoring
    if "sell immediately" in scenario1:
        score += 1
    elif "hold and hope" in scenario1:
        score += 2
    elif "hold knowing markets" in scenario1:
        score += 3
    elif "buy more" in scenario1:
        score += 4
    
    # Scenario 2 scoring
    if "High-yield savings" in scenario2:
        score += 1
    elif "Mix of all three" in scenario2:
        score += 2
    elif "Broad market fund" in scenario2:
        score += 3
    elif "Individual growth stocks" in scenario2:
        score += 4
    
    # Scenario 3 scoring
    if "Play it safe" in scenario3:
        score += 1
    elif "not sure" in scenario3:
        score += 2
    elif "Balance between" in scenario3:
        score += 3
    elif "Focus on growth" in scenario3:
        score += 4
    
    return score

def get_risk_profile(score):
    """Convert risk score to profile description."""
    if score <= 4:
        return "Conservative"
    elif score <= 7:
        return "Moderate"
    elif score <= 10:
        return "Growth-Oriented"
    else:
        return "Aggressive"

def get_beginner_stock_suggestions(age_range, primary_goal):
    """Get beginner-friendly stock suggestions based on profile."""
    suggestions = {
        "Apple (AAPL)": "Tech giant you probably use daily - iPhone, Mac, iPad",
        "Microsoft (MSFT)": "Powers most computers and cloud services worldwide", 
        "Amazon (AMZN)": "E-commerce and cloud computing leader",
        "Coca-Cola (KO)": "Classic dividend stock, over 130 years old",
        "Johnson & Johnson (JNJ)": "Healthcare giant with steady growth"
    }
    
    if "Learn" in primary_goal:
        suggestions["Vanguard S&P 500 ETF (VOO)"] = "Owns pieces of 500 top US companies - perfect for beginners"
    
    return suggestions

def generate_personalized_plan(data):
    """Generate personalized investment action plan."""
    age_range = data.get('age_range', '')
    primary_goal = data.get('primary_goal', '')
    risk_profile = data.get('risk_profile', 'Moderate')
    
    actions = []
    
    # Age-specific guidance
    if '16-20' in age_range or '21-25' in age_range:
        actions.append("🎓 Focus on learning and building good financial habits")
        actions.append("💰 Start with index funds or ETFs for broad market exposure")
        actions.append("⏰ Take advantage of your long investment timeline")
    
    # Goal-specific actions
    if "Learn" in primary_goal:
        actions.append("📚 Complete analysis tutorials and read educational content")
        actions.append("📊 Practice with paper trading before using real money")
    elif "emergency fund" in primary_goal:
        actions.append("🏦 Prioritize high-yield savings for emergency fund")
        actions.append("🎯 Invest only after securing 3-6 months of expenses")
    elif "Long-term" in primary_goal:
        actions.append("📈 Focus on diversified growth investments")
        actions.append("🔄 Set up automatic monthly contributions")
    
    # Risk-specific guidance
    if risk_profile == "Conservative":
        actions.append("🛡️ Start with broad market ETFs and blue-chip stocks")
    elif risk_profile == "Growth-Oriented":
        actions.append("🚀 Consider growth stocks and technology companies")
    
    actions.append("📱 Use InvestForge to analyze companies before investing")
    actions.append("🏆 Track your progress with our achievement system")
    
    return {"actions": actions}

def save_enhanced_user_preferences(onboarding_data):
    """Save enhanced preference structure to database."""
    user_email = st.session_state.get('user_data', {}).get('email')
    if not user_email:
        return False
    
    # Transform onboarding data to preference structure
    preferences = {
        'demographics': {
            'age_range': onboarding_data.get('age_range'),
            'income_range': onboarding_data.get('income_range')
        },
        'investment_goals': {
            'primary_goal': onboarding_data.get('primary_goal'),
            'timeline': onboarding_data.get('timeline')
        },
        'risk_assessment': {
            'risk_score': onboarding_data.get('risk_score'),
            'risk_profile': onboarding_data.get('risk_profile'),
            'scenario_responses': {
                'scenario1': onboarding_data.get('scenario1'),
                'scenario2': onboarding_data.get('scenario2'),
                'scenario3': onboarding_data.get('scenario3')
            }
        },
        'financial_status': {
            'initial_amount': onboarding_data.get('initial_amount'),
            'has_emergency_fund': onboarding_data.get('has_emergency_fund', False)
        },
        'tutorial_preferences': {
            'tutorial_stock': onboarding_data.get('tutorial_stock'),
            'suggested_stocks': onboarding_data.get('suggested_stocks', {})
        },
        'achievements': {
            'unlocked': [],
            'progress': {}
        },
        'onboarding_completed_at': datetime.utcnow().isoformat()
    }
    
    return api_client.save_user_preferences(user_email, preferences)


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

    # Old sidebar code removed - now using render_sidebar()
    # Main app content - Stock Analysis
    show_analysis_page()


def show_fractional_analysis_page():
    """Fractional share analysis page."""
    
    # Load usage on page load
    if 'usage_loaded' not in st.session_state:
        load_user_usage()
        st.session_state.usage_loaded = True
    
    # Check for demo mode
    if st.session_state.demo_mode:
        st.info("🎮 Demo Mode: Explore fractional share features with sample data!")
    
    # Create a mock user object for component compatibility
    mock_user = {
        'plan': st.session_state.get('user_plan', 'free'),
        'usage': {
            'fractional_calculations_count': st.session_state.get('fractional_calculations_count', 0)
        }
    }
    
    # Temporarily set session state for component
    original_user_data = st.session_state.get('user_data')
    st.session_state.user_data = mock_user
    
    try:
        render_fractional_analysis_page()
    finally:
        # Restore original session state
        if original_user_data is not None:
            st.session_state.user_data = original_user_data
        else:
            st.session_state.pop('user_data', None)


def show_analysis_page():
    """Stock analysis page with real AI integration."""
    
    # Load usage on page load
    if 'usage_loaded' not in st.session_state:
        load_user_usage()
        st.session_state.usage_loaded = True
    
    # Check for demo mode
    if st.session_state.demo_mode:
        st.info("🎮 Demo Mode: Explore all features with sample data!")
    
    # Check usage limits
    can_analyze, usage_message = check_usage_limits()

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
    
    # Check if this is a first-time user coming from onboarding
    is_first_analysis = st.session_state.get('first_analysis_stock') is not None
    tutorial_stock = st.session_state.get('first_analysis_stock', '')
    
    # Check if user just completed onboarding with enhanced preferences
    user_preferences = st.session_state.get('user_preferences', {})
    is_young_investor = False
    if isinstance(user_preferences, dict):
        demographics = user_preferences.get('demographics', {})
        age_range = demographics.get('age_range', '')
        is_young_investor = any(age in age_range for age in ['16-20', '21-25', '26-30'])
    
    # Show tutorial mode for first analysis
    if is_first_analysis and tutorial_stock:
        show_first_analysis_tutorial_interface(tutorial_stock)
        return
    
    # Use the refactored component-based analysis page
    # Create a mock user object for component compatibility
    mock_user = {
        'plan': st.session_state.get('user_plan', 'free'),
        'usage': {
            'analyses_count': st.session_state.get('analyses_count', 0)
        }
    }
    
    # Temporarily set session state for component
    original_user_data = st.session_state.get('user_data')
    st.session_state.user_data = mock_user
    
    try:
        render_analysis_page()
    finally:
        # Restore original session state
        if original_user_data is not None:
            st.session_state.user_data = original_user_data
        else:
            st.session_state.pop('user_data', None)

def show_first_analysis_tutorial_interface(tutorial_stock):
    """Show tutorial interface for first analysis."""
    st.markdown("### 🎓 Your First Analysis Tutorial")
    st.info(f"📚 **Tutorial Mode**: You're about to analyze {tutorial_stock}! We'll guide you through each step.")
    
    # Tutorial introduction
    with st.expander("📖 What you'll learn in this analysis", expanded=True):
        st.markdown("""
        **This analysis will teach you:**
        - 📊 **Company Fundamentals**: Revenue, profit, debt levels
        - 💰 **Stock Valuation**: Is the stock fairly priced?
        - 📈 **Growth Prospects**: Future outlook and potential
        - ⚠️ **Risk Factors**: What could affect the stock price
        - 🎯 **Investment Decision**: Should you buy, hold, or avoid?
        
        **Analysis time**: About 2-3 minutes
        """)
    
    # Pre-filled ticker with tutorial stock
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ticker = st.text_input(
            "📈 Analyzing Company",
            value=tutorial_stock,
            disabled=True,
            help=f"Tutorial analysis for {tutorial_stock} - you can analyze other stocks after this!"
        )
    
    with col2:
        tutorial_button = st.button("🎓 Start Tutorial Analysis", type="primary", use_container_width=True)
    
    # Educational preview
    st.markdown("### 🔍 What we'll examine:")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **📊 Financial Health**
        - Revenue growth
        - Profit margins
        - Debt levels
        """)
    
    with col2:
        st.markdown("""
        **💰 Valuation**
        - Price-to-earnings ratio
        - Compared to competitors
        - Fair value estimate
        """)
    
    with col3:
        st.markdown("""
        **🎯 Future Outlook**
        - Growth potential
        - Market trends
        - Risk assessment
        """)
    
    if tutorial_button:
        # Track tutorial start
        api_client.track_event('tutorial_analysis_started', {
            'tutorial_stock': tutorial_stock,
            'user_age_range': st.session_state.get('user_preferences', {}).get('demographics', {}).get('age_range', '')
        })
        
        # Clear first analysis flag and run normal analysis
        st.session_state.first_analysis_stock = None
        st.session_state.tutorial_mode = True
        run_ai_analysis_with_tutorial(tutorial_stock)
    
    # Display tutorial results if available
    if f'analysis_result_{tutorial_stock}' in st.session_state:
        display_tutorial_analysis_results(tutorial_stock)

def show_beginner_analysis_interface():
    """Show beginner-friendly analysis interface for young investors."""
    st.markdown("### 🚀 Analyze Any Company")
    
    # Get user preferences for personalized suggestions
    user_preferences = st.session_state.get('user_preferences', {})
    primary_goal = user_preferences.get('investment_goals', {}).get('primary_goal', '')
    
    # Show personalized stock suggestions based on user profile
    if primary_goal:
        suggestions = get_personalized_stock_suggestions(user_preferences)
        if suggestions:
            st.markdown("**💡 Personalized suggestions based on your goals:**")
            suggestion_cols = st.columns(len(suggestions))
            for i, (symbol, reason) in enumerate(suggestions.items()):
                with suggestion_cols[i]:
                    if st.button(f"🎯 {symbol}", help=reason, use_container_width=True):
                        st.session_state.suggested_ticker = symbol
    
    # Stock input with enhanced help
    col1, col2 = st.columns([3, 1])
    
    with col1:
        default_ticker = st.session_state.get('suggested_ticker', 'AAPL' if st.session_state.demo_mode else '')
        ticker = st.text_input(
            "Enter Stock Symbol",
            value=default_ticker,
            placeholder="e.g., AAPL, GOOGL, TSLA",
            help="💡 Not sure what to analyze? Try the suggested stocks above!"
        ).upper()
        
        # Clear suggested ticker after use
        if 'suggested_ticker' in st.session_state:
            del st.session_state.suggested_ticker
    
    with col2:
        analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)
    
    # Educational tips for beginners
    with st.expander("🎓 New to stock analysis? Click here for tips!", expanded=False):
        st.markdown("""
        **Before you start:**
        - 📚 **Learn first**: Only invest in companies you understand
        - 💰 **Start small**: Use money you can afford to lose
        - 🎯 **Diversify**: Don't put all eggs in one basket
        - ⏰ **Think long-term**: Good companies grow over time
        
        **What our analysis shows:**
        - **Financial health** - Is the company profitable?
        - **Valuation** - Is the stock price fair?
        - **Growth potential** - What's the future outlook?
        - **Risks** - What could go wrong?
        """)
    
    # Achievement progress for engaged users
    achievements = st.session_state.get('user_preferences', {}).get('achievements', {})
    if achievements.get('unlocked'):
        st.markdown("### 🏆 Your Progress")
        show_achievement_progress(achievements)
    
    # Run analysis
    if analyze_button and ticker:
        run_ai_analysis(ticker)
    
    # Display results
    if ticker and f'analysis_result_{ticker}' in st.session_state:
        display_analysis_results(ticker)

def show_standard_analysis_interface():
    """Show standard analysis interface for experienced users."""
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
    if ticker and f'analysis_result_{ticker}' in st.session_state:
        display_analysis_results(ticker)

def get_personalized_stock_suggestions(user_preferences):
    """Get personalized stock suggestions based on user profile."""
    demographics = user_preferences.get('demographics', {})
    goals = user_preferences.get('investment_goals', {})
    risk_profile = user_preferences.get('risk_assessment', {}).get('risk_profile', 'Moderate')
    
    age_range = demographics.get('age_range', '')
    primary_goal = goals.get('primary_goal', '')
    
    suggestions = {}
    
    # Age-based suggestions
    if '16-20' in age_range or '21-25' in age_range:
        suggestions["VOO"] = "Tracks S&P 500 - perfect first investment"
        suggestions["AAPL"] = "Tech company you know and use daily"
    
    # Goal-based suggestions
    if "Learn" in primary_goal:
        suggestions["MSFT"] = "Stable tech giant - great for learning"
        suggestions["JNJ"] = "Healthcare company with steady dividends"
    elif "Long-term" in primary_goal:
        suggestions["AMZN"] = "E-commerce and cloud leader"
        suggestions["GOOGL"] = "Dominant in search and AI"
    
    # Risk-based suggestions
    if risk_profile == "Conservative":
        suggestions["KO"] = "Coca-Cola - reliable dividend stock"
    elif risk_profile == "Growth-Oriented":
        suggestions["TSLA"] = "Electric vehicle innovation"
    
    return dict(list(suggestions.items())[:4])  # Limit to 4 suggestions

def show_achievement_progress(achievements):
    """Show user achievement progress."""
    unlocked = achievements.get('unlocked', [])
    
    achievement_badges = {
        'first_analysis': '🎓 Knowledge Seeker',
        'five_analyses': '📈 Market Explorer', 
        'first_watchlist': '🧠 Wise Investor',
        'portfolio_tracking': '🚀 Portfolio Builder',
        'long_term_hold': '💎 Long-term Thinker'
    }
    
    cols = st.columns(len(achievement_badges))
    for i, (key, badge) in enumerate(achievement_badges.items()):
        with cols[i]:
            if key in unlocked:
                st.markdown(f"✅ {badge}")
            else:
                st.markdown(f"⚪ {badge}")

def run_ai_analysis_with_tutorial(ticker):
    """Run analysis with tutorial explanations."""
    st.session_state.tutorial_mode = True
    run_ai_analysis(ticker)

def display_tutorial_analysis_results(ticker):
    """Display analysis results with tutorial explanations."""
    if f'analysis_result_{ticker}' in st.session_state:
        st.markdown("### 🎉 Tutorial Analysis Complete!")
        st.success("🏆 **Achievement Unlocked: Knowledge Seeker** - You completed your first analysis!")
        
        # Track achievement
        achievements = st.session_state.get('user_preferences', {}).get('achievements', {})
        if 'unlocked' not in achievements:
            achievements['unlocked'] = []
        if 'first_analysis' not in achievements['unlocked']:
            achievements['unlocked'].append('first_analysis')
            api_client.track_event('achievement_unlocked', {
                'achievement': 'first_analysis',
                'tutorial_stock': ticker
            })
        
        # Show tutorial-enhanced results
        display_analysis_results(ticker, tutorial_mode=True)


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
    logger.info("=== load_user_preferences called ===")
    user_email = st.session_state.get('user_email')
    logger.info(f"User email: {user_email}")

    if user_email:
        logger.info(f"Fetching preferences for {user_email}")
        preferences = api_client.get_user_preferences(user_email)
        logger.info(f"Preferences retrieved: {preferences is not None}")
        if preferences:
            logger.info(f"Preferences keys: {list(preferences.keys())}")
            st.session_state.user_preferences = preferences
            return preferences
        else:
            logger.warning("No preferences returned from API")
    else:
        logger.warning("No user email in session state")

    return None


def check_user_has_portfolio():
    """Check if user has any saved portfolios."""
    user_email = st.session_state.get('user_email')
    if not user_email:
        logger.warning("check_user_has_portfolio: No user_email in session")
        return False

    # Call API to get latest portfolio
    logger.info(f"Checking for portfolios for user: {user_email}")
    latest_portfolio = api_client.get_latest_portfolio(user_email)

    logger.info(f"API returned portfolio: {latest_portfolio is not None}")
    if latest_portfolio:
        logger.info(f"Portfolio found: {latest_portfolio.get('portfolio_id', 'NO_ID')}")

    if latest_portfolio:
        st.session_state.latest_portfolio = latest_portfolio
        return True

    logger.info(f"No portfolio found for user: {user_email}")
    return False


def needs_onboarding():
    """Check if user needs to complete onboarding."""
    user_prefs = st.session_state.get('user_preferences', {})
    logger.info(f"Checking onboarding status. Preferences: {user_prefs}")

    # Check if onboarding was completed (new streamlined flow)
    if user_prefs.get('onboarding_complete'):
        logger.info("Onboarding marked as complete")
        return False

    # Fallback: Check for essential onboarding fields (old format compatibility)
    risk_assessment = user_prefs.get('risk_assessment', {})
    has_risk = risk_assessment.get('risk_profile') is not None or user_prefs.get('risk_tolerance') is not None

    investment_goals = user_prefs.get('investment_goals', {})
    has_goals = investment_goals.get('primary_goal') is not None or isinstance(user_prefs.get('investment_goals'), list)

    demographics = user_prefs.get('demographics', {})
    has_demographics = demographics.get('age_range') is not None

    logger.info(f"Onboarding check: has_risk={has_risk}, has_goals={has_goals}, has_demographics={has_demographics}")

    needs_ob = not (has_risk and has_goals)
    logger.info(f"needs_onboarding result: {needs_ob}")
    return needs_ob


def route_after_login():
    """Route user to appropriate page after login based on their data."""
    try:
        logger.info("=== route_after_login called ===")

        # Priority 1: Check for saved portfolios
        logger.info("Checking Priority 1: Saved portfolios")
        has_portfolio = check_user_has_portfolio()
        logger.info(f"Has portfolio: {has_portfolio}")

        if has_portfolio:
            logger.info("Routing to portfolio landing page")
            st.session_state.show_portfolio_landing = True
            st.session_state.show_onboarding = False
            st.session_state.show_portfolio_generation = False
            st.session_state.show_main_app = False
            logger.info(f"Set show_portfolio_landing={st.session_state.show_portfolio_landing}")
            return

        # Priority 2: Check if needs onboarding
        logger.info("Checking Priority 2: Needs onboarding")
        needs_ob = needs_onboarding()
        logger.info(f"Needs onboarding: {needs_ob}")

        if needs_ob:
            logger.info("Routing to onboarding")
            st.session_state.show_onboarding = True
            st.session_state.show_portfolio_landing = False
            st.session_state.show_portfolio_generation = False
            st.session_state.show_main_app = False
            logger.info(f"Set show_onboarding={st.session_state.show_onboarding}")
            return

        # Priority 3: Has onboarding but no portfolio - auto-generate
        logger.info("Routing to portfolio generation (Priority 3)")
        st.session_state.show_portfolio_generation = True
        st.session_state.generating_from_onboarding = True  # Show overlay instead of nav bar
        st.session_state.show_onboarding = False
        st.session_state.show_portfolio_landing = False
        st.session_state.show_main_app = False
        logger.info(f"Set show_portfolio_generation={st.session_state.show_portfolio_generation}")

    except Exception as e:
        logger.error(f"Error in route_after_login: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Fallback: send to onboarding
        logger.warning("Falling back to onboarding due to error")
        st.session_state.show_onboarding = True
        st.session_state.show_portfolio_landing = False
        st.session_state.show_portfolio_generation = False
        st.session_state.show_main_app = False


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
    
    # Default analysis depth for this simplified analysis
    depth = "Standard Analysis"
    
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
                
                # Extract user profile for personalized analysis
                user_profile = extract_user_profile_for_tutorial(ticker)
                
                # Run the actual analysis with user profile
                with st.spinner(f"AI agents working on {ticker} analysis..."):
                    result = run_analysis(ticker, user_profile)
                
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
                
                # Also add raw_result to data for tutorial access
                analysis_data['raw_result'] = result
                
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

def display_analysis_results(ticker: str, tutorial_mode: bool = False):
    """Display the analysis results in organized tabs."""
    result_data = st.session_state.get(f'analysis_result_{ticker}')
    if not result_data:
        return
    
    # Show timestamp
    timestamp = result_data['timestamp']
    st.caption(f"Analysis completed at {timestamp.strftime('%I:%M %p on %B %d, %Y')}")
    
    # Tutorial mode introduction
    if tutorial_mode:
        st.markdown("### 📚 Understanding Your Analysis")
        st.info("💡 **Tutorial Mode**: Each section below teaches you something important about investing. Take your time to read through each tab!")
    
    # Create tabs for results with tutorial enhancements
    if tutorial_mode:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Overview (Start Here!)", 
            "📈 Technical Analysis", 
            "💰 Company Finances", 
            "🤖 AI Insights"
        ])
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Technical", "💰 Fundamental", "🤖 AI Insights"])
    
    data = result_data['data']
    
    with tab1:
        if tutorial_mode:
            display_tutorial_overview_tab(ticker, data)
        else:
            display_overview_tab(ticker, data)
    
    with tab2:
        if tutorial_mode:
            display_tutorial_technical_tab(ticker, data)
        else:
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
            st.plotly_chart(fig, use_container_width=True, key=f"stock_price_chart_{ticker}")
            
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
    
    st.markdown("### 💰 Company Finances")
    
    # Check if we have real crew analysis data first
    if 'analysis' in data and data['analysis']:
        st.markdown("#### 🤖 AI Financial Analysis")
        st.markdown(data['analysis'])
        st.markdown("---")
    
    # Also check for full crew result that might contain fundamental analysis
    if 'full_result' in data and data['full_result']:
        result_text = str(data['full_result']).lower()
        if any(term in result_text for term in ['revenue', 'profit', 'margin', 'financial', 'earnings']):
            st.markdown("#### 📊 Detailed Financial Assessment")
            st.markdown(data['full_result'])
            st.markdown("---")
    
    # Show supplementary financial metrics from yfinance
    st.markdown("#### 📈 Key Financial Metrics")
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
    
    # Add dynamic investment recommendation section based on crew analysis
    st.markdown("#### 🎯 Investment Recommendation")
    
    # Extract recommendations from crew data if available
    if 'strategy' in data and data['strategy']:
        strategy_text = str(data['strategy']).lower()
        
        # Analyze strategy output for recommendations
        if 'buy' in strategy_text and 'strong' in strategy_text:
            recommendation = "STRONG BUY"
            color = "success"
        elif 'buy' in strategy_text:
            recommendation = "BUY"  
            color = "success"
        elif 'hold' in strategy_text:
            recommendation = "HOLD"
            color = "info"
        elif 'sell' in strategy_text or 'avoid' in strategy_text:
            recommendation = "AVOID"
            color = "warning"
        else:
            recommendation = "ANALYZE FURTHER"
            color = "info"
        
        if color == "success":
            st.success(f"**AI Recommendation:** {recommendation}")
        elif color == "warning":
            st.warning(f"**AI Recommendation:** {recommendation}")
        else:
            st.info(f"**AI Recommendation:** {recommendation}")
            
        # Display strategy summary
        st.markdown("**Strategy Summary:**")
        st.markdown(data['strategy'])
    else:
        st.info("**Investment recommendations are based on the AI crew analysis above. Please review all sections before making investment decisions.**")


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


# =====================================
# Tutorial Display Functions
# =====================================

def display_tutorial_overview_tab(ticker: str, data: Dict[str, Any]):
    """Display overview with educational explanations for beginners using actual analysis data."""
    st.markdown("### 📊 Company Overview - What This Tells You")
    
    # Educational introduction
    st.info("🎓 **Learning Goal**: Understand the basics of what makes a company valuable and how to read key metrics.")
    
    # First show the actual AI crew analysis if available
    if 'raw_result' in data and data['raw_result']:
        st.markdown("#### 🤖 AI Analysis Summary")
        if hasattr(data['raw_result'], 'tasks_output') and data['raw_result'].tasks_output:
            # Show the research task output (first task)
            research_output = str(data['raw_result'].tasks_output[0])
            st.markdown(research_output[:1000] + "..." if len(research_output) > 1000 else research_output)
        
        st.markdown("---")
    
    # Get real stock data
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1mo")
        
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            price_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        else:
            current_price = data.get('overview', {}).get('current_price', 100)
            price_change = data.get('overview', {}).get('price_change', 5.2)
        
        company_name = info.get('longName', f'{ticker} Corporation')
        market_cap = info.get('marketCap', 0)
        pe_ratio = info.get('trailingPE', 0)
        
    except:
        # Fallback to mock data
        current_price = data.get('overview', {}).get('current_price', 100)
        price_change = data.get('overview', {}).get('price_change', 5.2)
        company_name = f'{ticker} Corporation'
        market_cap = data.get('overview', {}).get('market_cap', 1000000000)
        pe_ratio = data.get('overview', {}).get('pe_ratio', 25)
    
    # Key metrics with educational explanations
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label="📈 Current Stock Price",
            value=f"${current_price:.2f}",
            delta=f"{price_change:.1f}%"
        )
        st.caption("💡 **What this means**: The current price investors are willing to pay for one share of the company.")
        
        if market_cap:
            market_cap_formatted = f"${market_cap/1e9:.1f}B" if market_cap > 1e9 else f"${market_cap/1e6:.0f}M"
            st.metric("🏢 Market Cap", market_cap_formatted)
            st.caption("💡 **What this means**: Total value of all company shares. Bigger usually means more stable.")
    
    with col2:
        if pe_ratio and pe_ratio > 0:
            st.metric("📊 P/E Ratio", f"{pe_ratio:.1f}")
            if pe_ratio < 15:
                st.caption("💡 **What this means**: Low P/E might mean the stock is undervalued or the company has issues.")
            elif pe_ratio > 30:
                st.caption("💡 **What this means**: High P/E might mean investors expect high growth or the stock is expensive.")
            else:
                st.caption("💡 **What this means**: Moderate P/E suggests reasonable valuation for current earnings.")
        
        # Add sector info if available
        sector = info.get('sector', 'Technology') if 'info' in locals() else 'Technology'
        st.metric("🏭 Industry", sector)
        st.caption("💡 **What this means**: The business sector helps you understand what the company does.")
    
    # Educational summary
    st.markdown("### 🧠 What You've Learned")
    with st.expander("📚 Click to review key concepts", expanded=False):
        st.markdown("""
        **Stock Price**: What investors currently think one share is worth
        **Market Cap**: Company's total value (price × number of shares)
        **P/E Ratio**: How much investors pay for each dollar of company earnings
        **Industry**: Understanding what business the company is in
        
        **Next Steps**: 
        - 📈 Check Technical Analysis to see price trends
        - 💰 Look at Company Finances to see if they make money
        - 🤖 Read AI Insights for the big picture
        """)

def display_tutorial_technical_tab(ticker: str, data: Dict[str, Any]):
    """Display technical analysis with educational explanations using actual analysis data."""
    st.markdown("### 📈 Technical Analysis - Reading Price Charts")
    
    st.info("🎓 **Learning Goal**: Understand how to read stock charts and identify trends.")
    
    # First show the actual AI crew analysis if available
    if 'raw_result' in data and data['raw_result']:
        st.markdown("#### 🤖 AI Technical Analysis")
        if hasattr(data['raw_result'], 'tasks_output') and len(data['raw_result'].tasks_output) > 0:
            # Show relevant technical analysis from research output
            research_output = str(data['raw_result'].tasks_output[0])
            # Extract technical-related sections
            if "technical" in research_output.lower() or "chart" in research_output.lower() or "trend" in research_output.lower():
                st.markdown(research_output[:800] + "..." if len(research_output) > 800 else research_output)
            else:
                st.markdown("Technical analysis data is included in the comprehensive research above.")
        
        st.markdown("---")
    
    # Get real price data for chart
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        
        if not hist.empty:
            # Create educational price chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist['Close'],
                mode='lines',
                name='Stock Price',
                line=dict(color='#FF6B35', width=2)
            ))
            
            fig.update_layout(
                title=f"{ticker} Stock Price Trend (Last 3 Months)",
                xaxis_title="Date",
                yaxis_title="Price ($)",
                height=400,
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True, key=f"tutorial_price_chart_{ticker}")
            
            # Educational interpretation
            current_price = hist['Close'].iloc[-1]
            highest_price = hist['Close'].max()
            lowest_price = hist['Close'].min()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📈 Current Price", f"${current_price:.2f}")
            with col2:
                st.metric("⬆️ 3-Month High", f"${highest_price:.2f}")
            with col3:
                st.metric("⬇️ 3-Month Low", f"${lowest_price:.2f}")
            
            # Trend analysis for beginners
            if current_price > (lowest_price + highest_price) / 2:
                st.success("📈 **Trend**: Stock is trading in the upper half of its recent range - this could indicate strength.")
            else:
                st.warning("📉 **Trend**: Stock is trading in the lower half of its recent range - this might indicate weakness.")
    
    except Exception as e:
        st.error("Unable to load chart data. This happens sometimes with market data feeds.")
    
    # Educational content about technical analysis
    st.markdown("### 🎯 Reading the Chart")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **📊 What Charts Tell You:**
        - **Upward trend**: Price is generally rising
        - **Downward trend**: Price is generally falling
        - **Sideways trend**: Price is moving in a range
        """)
    
    with col2:
        st.markdown("""
        **🎓 Beginner Tips:**
        - Don't panic over daily changes
        - Look for overall direction over months
        - Combine with company fundamentals
        """)
    
    # Simple trend explanation
    st.markdown("### 🧠 What You've Learned")
    with st.expander("📚 Click to review technical analysis basics", expanded=False):
        st.markdown("""
        **Price Charts**: Show how the stock price has moved over time
        **Trends**: The general direction of price movement
        **Support/Resistance**: Price levels where the stock tends to bounce
        
        **Remember**: 
        - Charts show what happened, not what will happen
        - Use charts WITH fundamental analysis, not instead of it
        - Short-term price moves can be very unpredictable
        
        **Next Steps**: 
        - 💰 Check Company Finances to see if the business is healthy
        - 🤖 Read AI Insights for professional analysis
        """)

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
def extract_user_profile_for_tutorial(ticker: str) -> Dict[str, str]:
    """
    Extract user profile data from session state for tutorial analysis.
    Uses the same logic as the main analysis page for consistency.
    
    Args:
        ticker: Stock ticker symbol (for potential future use)
        
    Returns:
        Dictionary with standardized user profile for crew agents
    """
    # Get user preferences from session state
    user_preferences = st.session_state.get('user_preferences', {})
    
    # Extract demographics
    demographics = user_preferences.get('demographics', {})
    age_range = demographics.get('age_range', '')
    income_range = demographics.get('income_range', '')
    
    # Extract investment goals
    investment_goals = user_preferences.get('investment_goals', {})
    primary_goal = investment_goals.get('primary_goal', '')
    timeline = investment_goals.get('timeline', '')
    
    # Extract risk assessment
    risk_assessment = user_preferences.get('risk_assessment', {})
    risk_profile = risk_assessment.get('risk_profile', '')
    
    # Extract experience level (tutorial users are typically beginners)
    experience = user_preferences.get('experience_level', 'beginner')
    
    # Map to standardized format for crew agents
    # Use user's actual profile data, with tutorial-appropriate defaults only when missing
    profile = {
        'age_range': age_range or '23-30',  # Use actual user age, not tutorial assumption
        'income_range': income_range or '50k-100k',  # Use actual user income
        'primary_goal': primary_goal or 'first_investment',  # Tutorial is educational, so default to first investment
        'timeline': timeline or '5-10 years',  # Use actual user timeline
        'risk_profile': risk_profile.lower() if risk_profile else 'moderate',  # Use actual user risk tolerance
        'experience': 'beginner'  # Tutorial mode always treats as beginner for explanation style
    }
    
    # Map goal values to consistent format
    goal_mapping = {
        'First Investment': 'first_investment',
        'Retirement Planning': 'retirement_planning', 
        'Wealth Building': 'wealth_building',
        'Passive Income': 'passive_income',
        'Education': 'education'
    }
    
    if profile['primary_goal'] in goal_mapping:
        profile['primary_goal'] = goal_mapping[profile['primary_goal']]
    
    # Map risk profile to consistent format
    risk_mapping = {
        'Conservative': 'conservative',
        'Moderate': 'moderate', 
        'Aggressive': 'aggressive'
    }
    
    if profile['risk_profile'].title() in risk_mapping:
        profile['risk_profile'] = risk_mapping[profile['risk_profile'].title()]
    
    return profile


# Main Execution
# =====================================

if __name__ == "__main__":
    # Initialize session state
    init_session_state()

    # Process URL parameters from landing page
    process_url_params()

    # Show appropriate interface
    if not st.session_state.authenticated:
        if st.session_state.get('show_forgot_password'):
            show_forgot_password()
        else:
            show_login_signup()
    else:
        # Check if showing onboarding or portfolio generation (full screen, no nav bar)
        if st.session_state.get('show_onboarding', False):
            show_onboarding()
        elif st.session_state.get('show_portfolio_generation', False):
            # Portfolio generation with overlay (no nav bar)
            generate_portfolio_with_progress()
        else:
            # Render horizontal navigation bar for authenticated users
            render_horizontal_nav()

            if st.session_state.get('show_portfolio_landing', False):
                # Show portfolio landing page
                show_portfolio_landing()
            elif st.session_state.get('show_portfolio_results', False):
                show_portfolio_results()
            elif st.session_state.get('show_main_app', False):
                # User explicitly wants stock analysis
                main_app()
            else:
                # Default fallback - should rarely hit this
                st.info("Initializing...")