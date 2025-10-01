"""
Stock analysis component for InvestForge - integrates with existing crew system.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import time
import json

# Import existing crew systems
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from crew import create_crew, run_analysis
from utils.metrics import track_analysis, track_feature_usage
from utils.constants import PLANS


def render_analysis_page():
    """Render the main analysis page with multi-agent crew integration."""
    # Use Streamlit session state instead of SessionManager for compatibility with app.py
    if 'user_data' not in st.session_state:
        st.error("Please log in to access analysis features.")
        return
    
    user = st.session_state.user_data
    user_plan = user.get('plan', 'free')
    usage = user.get('usage', {})
    
    # Page header
    st.title("📊 AI-Powered Stock Analysis")
    st.markdown("Comprehensive financial analysis powered by multi-agent AI crew")
    
    # Check usage limits for free users
    if user_plan == 'free':
        analyses_used = usage.get('analyses_count', 0)
        analyses_limit = PLANS['free']['analyses_limit']
        
        if analyses_used >= analyses_limit:
            st.error("🚫 Analysis limit reached for your free plan.")
            st.markdown("**Upgrade to Growth plan for unlimited analyses!**")
            if st.button("🚀 Upgrade Now", type="primary"):
                st.session_state.show_upgrade_modal = True
                st.rerun()
            return
        
        remaining = analyses_limit - analyses_used
        progress = analyses_used / analyses_limit
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(progress)
        with col2:
            st.markdown(f"**{remaining}/{analyses_limit}** left")
    
    # Analysis configuration section
    st.markdown("### 🔧 Analysis Configuration")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        symbol = st.text_input(
            "Stock Symbol",
            placeholder="Enter ticker symbol (e.g., AAPL, TSLA, MSFT)",
            help="Enter a valid stock ticker symbol"
        ).upper()
    
    with col2:
        analysis_depth = st.selectbox(
            "Analysis Depth",
            ["Quick Analysis", "Standard Analysis", "Deep Analysis", "Quantitative Analysis"],
            index=1,
            help="Choose analysis complexity and depth"
        )
    
    with col3:
        timeframe = st.selectbox(
            "Time Horizon",
            ["Short-term (1-3 months)", "Medium-term (3-12 months)", "Long-term (1+ years)"],
            index=1,
            help="Investment time horizon"
        )
    
    # Advanced options
    with st.expander("🎛️ Advanced Options"):
        col1, col2 = st.columns(2)
        
        with col1:
            include_sentiment = st.checkbox("Include Sentiment Analysis", value=True)
            include_competitors = st.checkbox("Include Competitor Analysis", value=True)
            include_technical = st.checkbox("Include Technical Analysis", value=True)
        
        with col2:
            include_fundamental = st.checkbox("Include Fundamental Analysis", value=True)
            include_risk = st.checkbox("Include Risk Assessment", value=True)
            include_strategy = st.checkbox("Include Investment Strategy", value=True)
        
        compare_symbols = st.text_input(
            "Compare With (Optional)",
            placeholder="SPY, QQQ, sector ETF",
            help="Enter comma-separated symbols for comparison"
        )
    
    # Analysis execution
    analysis_col1, analysis_col2 = st.columns([3, 1])
    
    with analysis_col1:
        if st.button("🚀 Run AI Analysis", type="primary", use_container_width=True):
            if not symbol:
                st.error("Please enter a stock symbol")
                return
            
            run_crew_analysis(
                symbol=symbol,
                analysis_depth=analysis_depth,
                timeframe=timeframe,
                options={
                    'include_sentiment': include_sentiment,
                    'include_competitors': include_competitors,
                    'include_technical': include_technical,
                    'include_fundamental': include_fundamental,
                    'include_risk': include_risk,
                    'include_strategy': include_strategy,
                    'compare_symbols': compare_symbols
                },
                user=user,
                session_manager=session_manager
            )
    
    with analysis_col2:
        if st.button("📊 Quick Stats", use_container_width=True):
            if symbol:
                display_quick_stats(symbol)
    
    # Display results if available
    if f'analysis_result_{symbol}' in st.session_state:
        display_analysis_results(
            st.session_state[f'analysis_result_{symbol}'],
            symbol,
            analysis_depth
        )


def run_crew_analysis(symbol: str, analysis_depth: str, timeframe: str, options: Dict, user: Dict, session_manager):
    """Execute the multi-agent crew analysis."""
    
    start_time = time.time()
    
    # Create progress indicators
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Phase 1: Initialize crew
        status_text.text("🤖 Initializing AI agent crew...")
        progress_bar.progress(10)
        
        # Configure analysis based on depth
        if analysis_depth == "Quick Analysis":
            agents_to_use = ["researcher", "analyst"]
        elif analysis_depth == "Standard Analysis":
            agents_to_use = ["researcher", "analyst", "sentiment_analyst"]
        elif analysis_depth == "Deep Analysis":
            agents_to_use = ["researcher", "analyst", "sentiment_analyst", "strategist"]
        else:  # Quantitative Analysis
            # Use the advanced quantitative crew
            return run_quantitative_analysis(symbol, options, user, session_manager)
        
        # Phase 2: Data gathering
        status_text.text("📊 Agent 1: Gathering market data...")
        progress_bar.progress(25)
        time.sleep(1)  # Simulate processing time
        
        # Phase 3: Technical analysis
        if options['include_technical']:
            status_text.text("📈 Agent 2: Performing technical analysis...")
            progress_bar.progress(40)
            time.sleep(1)
        
        # Phase 4: Fundamental analysis
        if options['include_fundamental']:
            status_text.text("💰 Agent 2: Analyzing fundamentals...")
            progress_bar.progress(55)
            time.sleep(1)
        
        # Phase 5: Sentiment analysis
        if options['include_sentiment'] and analysis_depth in ["Standard Analysis", "Deep Analysis"]:
            status_text.text("🎭 Agent 3: Analyzing market sentiment...")
            progress_bar.progress(70)
            time.sleep(1)
        
        # Phase 6: Strategy formulation
        if options['include_strategy'] and analysis_depth == "Deep Analysis":
            status_text.text("🎯 Agent 4: Formulating investment strategy...")
            progress_bar.progress(85)
            time.sleep(1)
        
        # Phase 7: Execute crew analysis
        status_text.text("🚀 Running multi-agent analysis...")
        progress_bar.progress(90)
        
        # Extract user profile for personalized analysis
        user_profile = extract_user_profile_for_crew(user)
        
        # Run the actual crew analysis with user profile
        result = run_analysis(symbol, user_profile)
        
        # Phase 8: Complete
        progress_bar.progress(100)
        status_text.text("✅ Analysis complete!")
        
        # Track the analysis
        duration = time.time() - start_time
        user_id = user.get('id', st.session_state.get('user_email', 'anonymous'))
        track_analysis(user_id, symbol, analysis_depth, duration)
        
        # Update usage for free users
        if user.get('plan', 'free') == 'free':
            # Update session state instead of using session manager
            st.session_state.analyses_count = st.session_state.get('analyses_count', 0) + 1
        
        # Store results
        analysis_data = {
            'result': result,
            'symbol': symbol,
            'analysis_depth': analysis_depth,
            'timeframe': timeframe,
            'options': options,
            'timestamp': datetime.now().isoformat(),
            'duration': duration
        }
        
        st.session_state[f'analysis_result_{symbol}'] = analysis_data
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        st.success(f"✅ Analysis complete for {symbol}! Duration: {duration:.1f}s")
        st.rerun()
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Analysis failed: {str(e)}")
        st.error("Please try again or contact support if the issue persists.")


def run_quantitative_analysis(symbol: str, options: Dict, user: Dict, session_manager):
    """Run advanced quantitative analysis using the quant crew."""
    try:
        # Import the quantitative crew
        from quant_crew import QuantitativeAnalysisCrew
        
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        status_text.text("🔬 Initializing quantitative analysis crew...")
        progress_bar.progress(20)
        
        crew = QuantitativeAnalysisCrew()
        
        status_text.text("📊 Running advanced quantitative models...")
        progress_bar.progress(60)
        
        # Prepare comprehensive analysis input
        user_input = f"Comprehensive quantitative analysis for {symbol} including portfolio optimization, risk metrics, and strategy backtesting"
        
        result = crew.analyze(user_input)
        
        progress_bar.progress(100)
        status_text.text("✅ Quantitative analysis complete!")
        
        # Store results
        analysis_data = {
            'result': result,
            'symbol': symbol,
            'analysis_depth': "Quantitative Analysis",
            'timestamp': datetime.now().isoformat(),
            'type': 'quantitative'
        }
        
        st.session_state[f'analysis_result_{symbol}'] = analysis_data
        
        progress_bar.empty()
        status_text.empty()
        
        st.success(f"✅ Quantitative analysis complete for {symbol}!")
        st.rerun()
        
    except ImportError:
        st.warning("Quantitative analysis crew not available. Running standard analysis instead.")
        # Fallback to standard analysis
        run_crew_analysis(symbol, "Deep Analysis", "Medium-term", options, user, session_manager)
    except Exception as e:
        st.error(f"Quantitative analysis failed: {str(e)}")


def display_analysis_results(analysis_data: Dict[str, Any], symbol: str, analysis_depth: str):
    """Display comprehensive analysis results."""
    
    st.markdown("---")
    st.subheader(f"🎯 {symbol} Analysis Results")
    
    # Header with metadata
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Symbol", symbol)
    with col2:
        st.metric("Analysis Type", analysis_depth)
    with col3:
        timestamp = datetime.fromisoformat(analysis_data['timestamp'])
        st.metric("Completed", timestamp.strftime("%H:%M:%S"))
    with col4:
        if 'duration' in analysis_data:
            st.metric("Duration", f"{analysis_data['duration']:.1f}s")
    
    # Results display
    result = analysis_data['result']
    
    if analysis_data.get('type') == 'quantitative':
        display_quantitative_results(result, symbol)
    else:
        display_crew_results(result, symbol, analysis_data)


def display_crew_results(result, symbol: str, analysis_data: Dict):
    """Display results from the standard crew analysis."""
    
    # Create tabs for different aspects of the analysis
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Executive Summary", 
        "📊 Research Report", 
        "🎭 Sentiment Analysis", 
        "📈 Technical Analysis",
        "🎯 Investment Strategy"
    ])
    
    with tab1:
        st.markdown("### 📋 Executive Summary")
        
        # Parse the crew result to extract key insights
        if hasattr(result, 'tasks_output') and result.tasks_output:
            # Display summary of all task outputs
            for i, task_output in enumerate(result.tasks_output):
                agent_name = get_agent_name_from_task(i, analysis_data['analysis_depth'])
                
                with st.expander(f"🤖 {agent_name} Summary", expanded=(i==0)):
                    st.markdown(str(task_output))
        else:
            st.markdown(str(result))
    
    with tab2:
        st.markdown("### 📊 Research Report")
        
        # Display research findings
        if hasattr(result, 'tasks_output') and len(result.tasks_output) > 0:
            research_output = result.tasks_output[0]  # First task is usually research
            st.markdown(str(research_output))
        else:
            st.info("Research data not available in this analysis.")
        
        # Add quick stats
        display_quick_stats(symbol)
    
    with tab3:
        st.markdown("### 🎭 Sentiment Analysis")
        
        # Display sentiment findings
        if hasattr(result, 'tasks_output') and len(result.tasks_output) > 2:
            sentiment_output = result.tasks_output[1]  # Second task is usually sentiment
            st.markdown(str(sentiment_output))
        else:
            st.info("Sentiment analysis not included in this analysis level.")
    
    with tab4:
        st.markdown("### 📈 Technical Analysis")
        
        # Display technical analysis from research task output
        if hasattr(result, 'tasks_output') and len(result.tasks_output) > 0:
            research_output = str(result.tasks_output[0])  # Research task includes technical analysis
            
            # Extract technical analysis sections from research output
            if "technical" in research_output.lower() or "chart" in research_output.lower():
                st.markdown(research_output)
            else:
                st.markdown("Technical analysis data is included in the Research Report section.")
                
            # Add quick stats for visual context
            display_quick_stats(symbol)
        else:
            st.info("Technical analysis data not available in this analysis level.")
    
    with tab5:
        st.markdown("### 🎯 Investment Strategy")
        
        # Strategy recommendations
        if hasattr(result, 'tasks_output') and len(result.tasks_output) > 3:
            strategy_output = result.tasks_output[-1]  # Last task is usually strategy
            st.markdown(str(strategy_output))
        else:
            st.info("Investment strategy not included in this analysis level.")
        
        # Generate dynamic action items based on analysis results
        st.markdown("#### 📝 Action Items")
        action_items = generate_action_items_from_analysis(result, analysis_data)
        for item in action_items:
            st.markdown(f"- [ ] {item}")


def display_quantitative_results(result, symbol: str):
    """Display results from quantitative analysis."""
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Portfolio Metrics",
        "⚠️ Risk Analysis", 
        "📈 Backtesting",
        "🎯 Strategy"
    ])
    
    with tab1:
        st.markdown("### 📊 Portfolio Optimization")
        st.markdown(str(result))
    
    with tab2:
        st.markdown("### ⚠️ Risk Assessment")
        # Extract risk assessment from quantitative analysis output
        if result and "risk" in str(result).lower():
            st.markdown(str(result))
        else:
            st.info("Risk metrics not available in this quantitative analysis.")
    
    with tab3:
        st.markdown("### 📈 Strategy Backtesting")
        # Extract backtesting from quantitative analysis output
        if result and ("backtest" in str(result).lower() or "performance" in str(result).lower()):
            st.markdown(str(result))
        else:
            st.info("Backtesting results not available in this analysis.")
    
    with tab4:
        st.markdown("### 🎯 Investment Strategy")
        # Display quantitative strategy recommendations
        if result:
            st.markdown(str(result))
        else:
            st.info("Strategy recommendations not available.")


def display_quick_stats(symbol: str):
    """Display quick statistics for a stock."""
    try:
        import yfinance as yf
        
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="1mo")
        
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            price_change = hist['Close'].iloc[-1] - hist['Close'].iloc[-2]
            price_change_pct = (price_change / hist['Close'].iloc[-2]) * 100
            
            st.markdown("#### 📈 Quick Stats")
            
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
                    if market_cap > 1e9:
                        cap_display = f"${market_cap/1e9:.1f}B"
                    else:
                        cap_display = f"${market_cap/1e6:.1f}M"
                    st.metric("Market Cap", cap_display)
                else:
                    st.metric("Market Cap", "N/A")
            
            with col3:
                pe_ratio = info.get('trailingPE', 'N/A')
                if pe_ratio != 'N/A':
                    st.metric("P/E Ratio", f"{pe_ratio:.2f}")
                else:
                    st.metric("P/E Ratio", "N/A")
            
            with col4:
                volume = hist['Volume'].iloc[-1]
                if volume > 1e6:
                    vol_display = f"{volume/1e6:.1f}M"
                else:
                    vol_display = f"{volume/1e3:.1f}K"
                st.metric("Volume", vol_display)
        
    except Exception as e:
        st.error(f"Unable to fetch quick stats: {str(e)}")


def get_agent_name_from_task(task_index: int, analysis_depth: str) -> str:
    """Get agent name based on task index and analysis depth."""
    agent_names = {
        0: "🔍 Market Researcher",
        1: "🎭 Sentiment Analyst", 
        2: "💼 Financial Analyst",
        3: "🎯 Investment Strategist"
    }
    
    if analysis_depth == "Quick Analysis":
        if task_index == 0:
            return "🔍 Market Researcher"
        else:
            return "💼 Financial Analyst"
    
    return agent_names.get(task_index, f"Agent {task_index + 1}")


def generate_action_items_from_analysis(result, analysis_data: Dict) -> List[str]:
    """
    Generate dynamic action items based on crew analysis results.
    
    Args:
        result: Crew analysis result
        analysis_data: Analysis metadata
        
    Returns:
        List of action items tailored to the analysis
    """
    action_items = []
    
    # Extract key information from crew outputs
    has_strategy = False
    has_risk_assessment = False
    has_sentiment = False
    
    if hasattr(result, 'tasks_output') and result.tasks_output:
        for i, task_output in enumerate(result.tasks_output):
            output_str = str(task_output).lower()
            
            # Check for strategy recommendations
            if i == len(result.tasks_output) - 1:  # Last task is usually strategy
                has_strategy = True
                if "buy" in output_str or "strong buy" in output_str:
                    action_items.append("Consider initiating a position based on positive AI assessment")
                elif "sell" in output_str or "avoid" in output_str:
                    action_items.append("Exercise caution - AI analysis suggests potential risks")
                else:
                    action_items.append("Review the investment strategy recommendations carefully")
            
            # Check for risk information
            if "risk" in output_str or "volatility" in output_str:
                has_risk_assessment = True
                action_items.append("Assess the risk metrics against your risk tolerance")
            
            # Check for sentiment information
            if "sentiment" in output_str or "news" in output_str:
                has_sentiment = True
                action_items.append("Monitor ongoing news and sentiment changes")
    
    # Add standard action items based on analysis depth
    analysis_depth = analysis_data.get('analysis_depth', 'Standard Analysis')
    
    if analysis_depth in ['Deep Analysis', 'Quantitative Analysis']:
        action_items.append("Review the comprehensive technical and fundamental metrics")
        action_items.append("Consider position sizing based on the detailed risk assessment")
    
    # Add action items based on user profile if available
    options = analysis_data.get('options', {})
    if options.get('include_competitors'):
        action_items.append("Compare with competitor analysis to validate investment thesis")
    
    # Default action items if none generated
    if not action_items:
        action_items = [
            "Review the key metrics highlighted in the analysis",
            "Consider your personal risk tolerance and investment timeline",
            "Monitor the stock's performance over the coming weeks",
            "Set up price alerts at key support and resistance levels"
        ]
    
    # Add essential final items
    action_items.append("Consult with a financial advisor if needed")
    action_items.append("Never invest more than you can afford to lose")
    
    return action_items


def create_analysis_chart(symbol: str, period: str = "1y"):
    """Create an interactive analysis chart."""
    try:
        import yfinance as yf
        
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        
        if hist.empty:
            st.error("No data available for this symbol.")
            return
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=[f'{symbol} Price Chart', 'Volume']
        )
        
        # Price chart
        fig.add_trace(
            go.Candlestick(
                x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'],
                name='Price'
            ),
            row=1, col=1
        )
        
        # Moving averages
        hist['SMA_20'] = hist['Close'].rolling(20).mean()
        hist['SMA_50'] = hist['Close'].rolling(50).mean()
        
        fig.add_trace(
            go.Scatter(
                x=hist.index,
                y=hist['SMA_20'],
                mode='lines',
                name='SMA 20',
                line=dict(color='orange', width=1)
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=hist.index,
                y=hist['SMA_50'],
                mode='lines',
                name='SMA 50',
                line=dict(color='red', width=1)
            ),
            row=1, col=1
        )
        
        # Volume
        fig.add_trace(
            go.Bar(
                x=hist.index,
                y=hist['Volume'],
                name='Volume',
                marker_color='lightblue'
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title=f"{symbol} - Technical Analysis",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            height=600,
            showlegend=True,
            template="plotly_white"
        )
        
        fig.update_xaxes(rangeslider_visible=False)
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Unable to create chart: {str(e)}")


def extract_user_profile_for_crew(user: Dict) -> Dict[str, str]:
    """
    Extract user profile data from session state for crew personalization.
    
    Args:
        user: User data dictionary
        
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
    
    # Extract experience level (if available from other sources)
    experience = user_preferences.get('experience_level', 'beginner')
    
    # Map to standardized format for crew agents
    profile = {
        'age_range': age_range or '25-35',
        'income_range': income_range or '50k-100k', 
        'primary_goal': primary_goal or 'wealth_building',
        'timeline': timeline or '5-10 years',
        'risk_profile': risk_profile.lower() if risk_profile else 'moderate',
        'experience': experience
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