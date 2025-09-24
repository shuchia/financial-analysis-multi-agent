# =====================================
# File: enhanced_app.py - Full AI Integration with Usage Tracking
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

# Custom CSS for better UI
st.markdown("""
<style>
    /* Loading animation */
    .stSpinner > div {
        text-align: center;
        margin-top: 20px;
    }
    
    /* Error boundary styling */
    .error-container {
        background-color: #ffebee;
        border: 1px solid #ef5350;
        border-radius: 4px;
        padding: 16px;
        margin: 16px 0;
    }
    
    /* Success animation */
    .success-container {
        background-color: #e8f5e9;
        border: 1px solid #4caf50;
        border-radius: 4px;
        padding: 16px;
        margin: 16px 0;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 16px;
        font-weight: 500;
    }
    
    /* Usage counter styling */
    .usage-counter {
        background-color: #f5f5f5;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

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
# Main Application Functions
# =====================================

def show_analysis_page():
    """Stock analysis page with real AI integration."""
    st.title("📊 AI-Powered Stock Analysis")
    
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
    
    # Analysis options
    with st.expander("⚙️ Analysis Options", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            analysis_depth = st.selectbox(
                "Analysis Depth",
                ["Standard", "Comprehensive", "Quick"],
                help="Choose the depth of analysis"
            )
        with col2:
            include_competitors = st.checkbox("Include Competitor Analysis", value=True)
            include_sentiment = st.checkbox("Include Sentiment Analysis", value=True)
    
    # Run analysis
    if analyze_button and ticker:
        run_ai_analysis(ticker, analysis_depth, include_competitors, include_sentiment)
    
    # Display stored results
    if f'analysis_result_{ticker}' in st.session_state:
        display_analysis_results(ticker)

def run_ai_analysis(ticker: str, depth: str, include_competitors: bool, include_sentiment: bool):
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
                from app.crew import create_crew, run_analysis
                
                # Phase 1: Create crew
                status_text.text("🔧 Creating specialized AI crew...")
                progress_bar.progress(20)
                
                # Phase 2: Run analysis
                status_text.text(f"📊 Analyzing {ticker}...")
                progress_bar.progress(30)
                
                # Track analysis start
                user_id = st.session_state.user_data.get('user_id')
                if user_id:
                    api_client.track_analysis_event(user_id, ticker, depth)
                
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

# =====================================
# Import existing functions from app.py
# =====================================

# Import all the authentication and helper functions from the original app.py
from app import (
    init_session_state as original_init_session_state,
    process_url_params,
    show_login_signup,
    show_onboarding,
    authenticate_user,
    create_user_account,
    save_user_preferences,
    load_user_preferences,
    track_signup,
    track_referral,
    initiate_payment,
    show_upgrade_modal,
    save_session_cookie,
    send_magic_link,
    initiate_google_auth,
    initiate_apple_auth,
    show_portfolio_page,
    show_backtesting_page,
    show_risk_page,
    show_education_page,
    show_settings_page
)

# =====================================
# Main Application
# =====================================

def main_app():
    """Main application interface with enhanced features."""
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### ⚒️ InvestForge")
        st.markdown(f"**User:** {st.session_state.user_email}")
        st.markdown(f"**Plan:** {st.session_state.user_plan.title()}")
        
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

# =====================================
# Main Execution
# =====================================

if __name__ == "__main__":
    # Initialize session state
    init_session_state()
    original_init_session_state()
    
    # Process URL parameters from landing page
    process_url_params()
    
    # Show appropriate interface
    if not st.session_state.authenticated:
        show_login_signup()
    elif st.session_state.get('show_onboarding') and not st.session_state.onboarding_complete:
        show_onboarding()
    else:
        main_app()