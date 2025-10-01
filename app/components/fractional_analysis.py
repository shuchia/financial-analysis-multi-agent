"""
Fractional share analysis component for InvestForge - integrates with existing crew system.
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

# Import existing systems
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from tools.fractional_share_tool import calculate_fractional_shares, get_fractional_portfolio_suggestions
from utils.fractional_calculator import (
    get_real_time_price, FRACTIONAL_ELIGIBLE_STOCKS, BROKER_INFO,
    get_comparison_table, calculate_growth_projections, get_dividend_projections,
    get_fractional_education_content, validate_investment_amount
)
from utils.metrics import track_feature_usage
from utils.constants import PLANS


def render_fractional_analysis_page():
    """Render the fractional share analysis page with user profile integration."""
    # Use Streamlit session state for compatibility with app.py
    if 'user_data' not in st.session_state:
        st.error("Please log in to access fractional share features.")
        return
    
    user = st.session_state.user_data
    user_plan = user.get('plan', 'free')
    usage = user.get('usage', {})
    
    # Page header
    st.title("💰 Fractional Share Analysis")
    st.markdown("Invest in expensive stocks with small amounts using fractional shares")
    
    # Check usage limits for free users
    if user_plan == 'free':
        calculations_used = st.session_state.get('fractional_calculations_count', 0)
        calculations_limit = PLANS['free']['fractional_calculations_limit']
        
        if calculations_used >= calculations_limit:
            st.error("🚫 Fractional calculation limit reached for your free plan.")
            st.markdown("**Upgrade to Growth plan for unlimited calculations!**")
            if st.button("🚀 Upgrade Now", type="primary"):
                st.session_state.show_upgrade_modal = True
                st.rerun()
            return
        
        remaining = calculations_limit - calculations_used
        progress = calculations_used / calculations_limit
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(progress)
        with col2:
            st.markdown(f"**{remaining}/{calculations_limit}** left")
    
    # Educational banner for new users
    if st.session_state.get('fractional_calculations_count', 0) == 0:
        with st.expander("🎓 New to Fractional Shares? Click to learn!", expanded=False):
            education_content = get_fractional_education_content()
            st.markdown(f"### {education_content['basics']['title']}")
            st.markdown(education_content['basics']['content'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Benefits:**")
                for benefit in education_content['basics']['benefits']:
                    st.markdown(f"✅ {benefit}")
            
            with col2:
                st.markdown("**How it works:**")
                for i, step in enumerate(education_content['how_it_works']['steps'][:3], 1):
                    st.markdown(f"{i}. {step}")
    
    # Create tabs for different features
    tab1, tab2, tab3, tab4 = st.tabs([
        "🧮 Calculator", 
        "📊 Portfolio Builder", 
        "📈 Growth Projections",
        "🎓 Education"
    ])
    
    with tab1:
        render_fractional_calculator()
    
    with tab2:
        render_portfolio_builder()
    
    with tab3:
        render_growth_projections()
    
    with tab4:
        render_education_section()


def render_fractional_calculator():
    """Render the main fractional share calculator."""
    st.markdown("### 🧮 Fractional Share Calculator")
    st.markdown("Calculate exactly how much of any stock you can buy with your investment amount.")
    
    # Input section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        investment_amount = st.number_input(
            "Investment Amount ($)",
            min_value=1.0,
            max_value=50000.0,
            value=100.0,
            step=1.0,
            help="Enter the dollar amount you want to invest"
        )
    
    with col2:
        calculation_type = st.selectbox(
            "Calculation Type",
            ["Single Stock", "Compare Multiple"],
            help="Calculate for one stock or compare several"
        )
    
    # Stock selection
    if calculation_type == "Single Stock":
        render_single_stock_calculator(investment_amount)
    else:
        render_comparison_calculator(investment_amount)


def render_single_stock_calculator(investment_amount: float):
    """Render calculator for a single stock."""
    
    # Stock input methods
    input_method = st.radio(
        "How would you like to select a stock?",
        ["Popular Stocks", "Enter Symbol"],
        horizontal=True
    )
    
    if input_method == "Popular Stocks":
        # Create a nice grid of popular stocks
        st.markdown("**Choose from popular fractional-eligible stocks:**")
        
        popular_stocks = list(FRACTIONAL_ELIGIBLE_STOCKS.keys())[:12]  # Top 12
        
        # Create 4 columns for stock selection
        cols = st.columns(4)
        selected_ticker = None
        
        for i, ticker in enumerate(popular_stocks):
            col_idx = i % 4
            with cols[col_idx]:
                company_name = FRACTIONAL_ELIGIBLE_STOCKS[ticker]
                # Truncate long company names
                display_name = company_name if len(company_name) <= 20 else company_name[:17] + "..."
                if st.button(f"{ticker}\n{display_name}", key=f"stock_{ticker}"):
                    selected_ticker = ticker
    else:
        selected_ticker = st.text_input(
            "Stock Symbol",
            placeholder="Enter ticker (e.g., AAPL, TSLA)",
            help="Enter any valid stock symbol"
        ).upper()
    
    # Perform calculation if we have a ticker
    if selected_ticker:
        with st.spinner(f"Calculating fractional shares for {selected_ticker}..."):
            # Get user profile for personalized context
            user_profile = extract_user_profile_for_fractional()
            
            # Calculate fractional shares
            result = calculate_fractional_shares(investment_amount, selected_ticker)
            
            if result.get('error'):
                st.error(f"❌ {result['error']}")
                return
            
            # Track usage
            track_fractional_calculation()
            
            # Display results
            display_single_stock_results(result, user_profile)


def render_comparison_calculator(investment_amount: float):
    """Render calculator for comparing multiple stocks."""
    
    st.markdown("**Select stocks to compare:**")
    
    # Multi-select for comparison
    available_stocks = list(FRACTIONAL_ELIGIBLE_STOCKS.keys())
    selected_stocks = st.multiselect(
        "Choose stocks to compare",
        available_stocks,
        default=['AAPL', 'MSFT', 'GOOGL', 'TSLA'][:4],
        help="Select 2-6 stocks to compare fractional share purchases"
    )
    
    if len(selected_stocks) < 2:
        st.warning("Please select at least 2 stocks to compare.")
        return
    
    if len(selected_stocks) > 6:
        st.warning("Please select no more than 6 stocks for optimal comparison.")
        selected_stocks = selected_stocks[:6]
    
    if st.button("🔍 Compare Fractional Shares", type="primary"):
        with st.spinner("Calculating fractional shares for all selected stocks..."):
            comparison_data = get_comparison_table(selected_stocks, investment_amount)
            
            if comparison_data:
                track_fractional_calculation()
                display_comparison_results(comparison_data, investment_amount)


def render_portfolio_builder():
    """Render the fractional portfolio builder."""
    st.markdown("### 📊 Fractional Share Portfolio Builder")
    st.markdown("Build a diversified portfolio using fractional shares based on your profile.")
    
    # Get user profile for personalized recommendations
    user_profile = extract_user_profile_for_fractional()
    
    # Portfolio inputs
    col1, col2 = st.columns(2)
    
    with col1:
        total_portfolio_amount = st.number_input(
            "Total Portfolio Amount ($)",
            min_value=25.0,
            max_value=50000.0,
            value=500.0,
            step=25.0,
            help="Minimum $25 recommended for diversification"
        )
    
    with col2:
        portfolio_style = st.selectbox(
            "Portfolio Style",
            ["Balanced", "Growth Focused", "Dividend Focused", "Conservative"],
            help="Choose based on your investment goals"
        )
    
    # Display user profile context
    if user_profile:
        with st.expander("👤 Your Investment Profile", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Age Range", user_profile.get('age_range', 'Not set'))
                st.metric("Experience", user_profile.get('experience', 'Beginner'))
            with col2:
                st.metric("Risk Profile", user_profile.get('risk_profile', 'Moderate').title())
                st.metric("Timeline", user_profile.get('timeline', '5-10 years'))
            with col3:
                st.metric("Primary Goal", user_profile.get('primary_goal', 'Wealth building').replace('_', ' ').title())
                st.metric("Income Range", user_profile.get('income_range', 'Not set'))
    
    if st.button("🎯 Generate Portfolio Suggestions", type="primary"):
        with st.spinner("Creating personalized fractional portfolio..."):
            # Adjust user profile based on portfolio style selection
            adjusted_profile = user_profile.copy() if user_profile else {}
            
            if portfolio_style == "Growth Focused":
                adjusted_profile['risk_profile'] = 'aggressive'
            elif portfolio_style == "Conservative":
                adjusted_profile['risk_profile'] = 'conservative'
            elif portfolio_style == "Dividend Focused":
                adjusted_profile['primary_goal'] = 'passive_income'
            
            # Get portfolio suggestions
            portfolio_result = get_fractional_portfolio_suggestions(total_portfolio_amount, adjusted_profile)
            
            if portfolio_result.get('error'):
                st.error(f"❌ {portfolio_result['error']}")
                return
            
            track_fractional_calculation()
            display_portfolio_results(portfolio_result)


def render_growth_projections():
    """Render growth projection analysis."""
    st.markdown("### 📈 Growth Projections for Fractional Investments")
    st.markdown("See how your fractional share investments could grow over time.")
    
    # Inputs for projection
    col1, col2, col3 = st.columns(3)
    
    with col1:
        projection_amount = st.number_input(
            "Investment Amount ($)",
            min_value=10.0,
            max_value=10000.0,
            value=100.0,
            step=10.0
        )
    
    with col2:
        projection_ticker = st.selectbox(
            "Select Stock",
            ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM'],
            help="Choose a stock for growth projection"
        )
    
    with col3:
        projection_years = st.selectbox(
            "Projection Period",
            [1, 3, 5, 10],
            index=2,
            help="Years to project growth"
        )
    
    if st.button("📊 Calculate Growth Projections", type="primary"):
        with st.spinner(f"Calculating growth projections for {projection_ticker}..."):
            growth_data = calculate_growth_projections(projection_ticker, projection_amount, projection_years)
            
            if growth_data.get('error'):
                st.error(f"❌ {growth_data['error']}")
                return
            
            display_growth_projections(growth_data)


def render_education_section():
    """Render educational content about fractional shares."""
    st.markdown("### 🎓 Fractional Share Education")
    
    education_content = get_fractional_education_content()
    
    # Education tabs
    edu_tab1, edu_tab2, edu_tab3, edu_tab4 = st.tabs([
        "📚 Basics", 
        "⚙️ How It Works", 
        "💡 Best Practices",
        "🏦 Brokers"
    ])
    
    with edu_tab1:
        st.markdown(f"## {education_content['basics']['title']}")
        st.markdown(education_content['basics']['content'])
        
        st.markdown("### Key Benefits")
        for benefit in education_content['basics']['benefits']:
            st.markdown(f"✅ **{benefit}**")
    
    with edu_tab2:
        st.markdown(f"## {education_content['how_it_works']['title']}")
        
        for i, step in enumerate(education_content['how_it_works']['steps'], 1):
            st.markdown(f"**{i}.** {step}")
        
        # Example calculation
        st.markdown("### Example Calculation")
        st.code("""
Example: Buying Apple (AAPL) with $50

If AAPL = $150 per share:
• Your fractional shares: $50 ÷ $150 = 0.3333 shares
• You own: 33.33% of one share
• If AAPL pays $0.25 quarterly dividend:
  Your dividend: 0.3333 × $0.25 = $0.083 per quarter
        """)
    
    with edu_tab3:
        st.markdown(f"## {education_content['best_practices']['title']}")
        
        for tip in education_content['best_practices']['tips']:
            st.markdown(f"💡 {tip}")
        
        st.markdown("### Fractional Share Strategies")
        strategies = [
            "**Dollar-Cost Averaging**: Invest the same amount regularly",
            "**Core-Satellite**: Use fractional shares for expensive 'core' positions",
            "**Thematic Investing**: Build themes (tech, healthcare) with fractional shares",
            "**Dividend Reinvestment**: Automatically reinvest dividends into fractional shares"
        ]
        
        for strategy in strategies:
            st.markdown(f"🎯 {strategy}")
    
    with edu_tab4:
        st.markdown("## 🏦 Broker Comparison")
        st.markdown("Choose the right broker for fractional share investing:")
        
        broker_df = pd.DataFrame([
            {
                'Broker': info['name'],
                'Commission': f"${info['commission']:.2f}",
                'Min Investment': f"${info['min_investment']:.2f}",
                'Fractional Fee': f"${info['fractional_fee']:.2f}",
                'Coverage': 'Most Stocks' if info['supports_most_stocks'] else 'Limited'
            }
            for info in BROKER_INFO.values()
        ])
        
        st.dataframe(broker_df, use_container_width=True)


def display_single_stock_results(result: Dict[str, Any], user_profile: Dict):
    """Display results for single stock fractional calculation."""
    
    # Main results
    st.markdown("---")
    st.markdown(f"### 📊 Results for {result['ticker']} - {result['company_name']}")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Fractional Shares",
            f"{result['shares']}",
            help="Number of shares you can buy (to 4 decimal places)"
        )
    
    with col2:
        st.metric(
            "Ownership %",
            f"{result['percentage_of_share']}%",
            help="Percentage of one full share you'll own"
        )
    
    with col3:
        st.metric(
            "Current Price",
            f"${result['current_price']}",
            help="Current stock price per share"
        )
    
    with col4:
        st.metric(
            "Exact Cost",
            f"${result['exact_cost']}",
            help="Precise cost of your fractional shares"
        )
    
    # Visual representation
    render_ownership_chart(result)
    
    # Dividend information
    if result['annual_dividend_income'] > 0:
        st.markdown("### 💰 Dividend Information")
        div_col1, div_col2 = st.columns(2)
        
        with div_col1:
            st.metric("Annual Dividend Income", f"${result['annual_dividend_income']:.2f}")
        with div_col2:
            st.metric("Dividend Yield", f"{result['dividend_yield']*100:.2f}%" if result['dividend_yield'] else "0%")
    
    # Broker compatibility
    st.markdown("### 🏦 Broker Compatibility")
    broker_support = result['broker_support']
    
    broker_cols = st.columns(len(BROKER_INFO))
    for i, (broker_key, broker_info) in enumerate(BROKER_INFO.items()):
        with broker_cols[i]:
            supported = broker_support.get(broker_key, False)
            status = "✅ Supported" if supported else "❌ Not Supported"
            st.markdown(f"**{broker_info['name']}**\n{status}")
    
    # Personalized insights
    if user_profile:
        render_personalized_insights(result, user_profile)


def display_comparison_results(comparison_data: List[Dict], investment_amount: float):
    """Display comparison results for multiple stocks."""
    
    st.markdown("---")
    st.markdown(f"### 📊 Fractional Share Comparison - ${investment_amount:.0f} Investment")
    
    # Create comparison DataFrame
    df = pd.DataFrame(comparison_data)
    
    # Display table
    display_df = df[['ticker', 'company_name', 'current_price', 'shares', 'percentage_of_share', 'annual_dividend']].copy()
    display_df.columns = ['Symbol', 'Company', 'Price', 'Shares', 'Ownership %', 'Annual Dividend']
    
    # Format columns
    display_df['Price'] = display_df['Price'].apply(lambda x: f"${x:.2f}")
    display_df['Ownership %'] = display_df['Ownership %'].apply(lambda x: f"{x:.2f}%")
    display_df['Annual Dividend'] = display_df['Annual Dividend'].apply(lambda x: f"${x:.2f}")
    
    st.dataframe(display_df, use_container_width=True)
    
    # Visual comparison
    render_comparison_charts(comparison_data, investment_amount)


def display_portfolio_results(portfolio_result: Dict):
    """Display portfolio builder results."""
    
    st.markdown("---")
    st.markdown(f"### 🎯 Your Fractional Share Portfolio - ${portfolio_result['total_amount']:.0f}")
    
    portfolio = portfolio_result['portfolio']
    
    # Portfolio overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Number of Positions", portfolio_result['num_positions'])
    with col2:
        st.metric("Diversification Score", f"{portfolio_result['diversification_score']}/100")
    with col3:
        st.metric("Risk Level", portfolio_result['risk_level'].title())
    
    # Portfolio breakdown
    st.markdown("### 📋 Portfolio Breakdown")
    
    portfolio_df = pd.DataFrame([
        {
            'Symbol': pos['ticker'],
            'Company': pos['company_name'],
            'Allocation': f"{pos['allocation_percentage']}%",
            'Amount': f"${pos['allocation_amount']:.2f}",
            'Shares': pos['shares'],
            'Rationale': pos['rationale']
        }
        for pos in portfolio
    ])
    
    st.dataframe(portfolio_df, use_container_width=True)
    
    # Portfolio visualization
    render_portfolio_chart(portfolio)


def display_growth_projections(growth_data: Dict):
    """Display growth projection results."""
    
    st.markdown("---")
    st.markdown(f"### 📈 Growth Projections for {growth_data['ticker']}")
    
    projections = growth_data['projections']
    
    # Historical context
    st.metric(
        "Historical Annual Return", 
        f"{growth_data['historical_annual_return']:.1f}%",
        help="Based on historical performance"
    )
    
    # Projection scenarios
    st.markdown(f"#### Projections for ${growth_data['investment_amount']:.0f} over {growth_data['projection_years']} years")
    
    scenario_cols = st.columns(3)
    
    for i, (scenario, data) in enumerate(projections.items()):
        with scenario_cols[i]:
            st.markdown(f"**{scenario.title()} Scenario**")
            st.metric("Future Value", f"${data['future_value']:.2f}")
            st.metric("Total Gain", f"${data['total_gain']:.2f}")
            st.metric("Annual Return", f"{data['annualized_return']:.1f}%")
    
    # Growth chart
    render_growth_chart(growth_data)


def render_ownership_chart(result: Dict):
    """Render a pie chart showing fractional ownership."""
    
    ownership_pct = result['percentage_of_share']
    remaining_pct = 100 - ownership_pct
    
    fig = go.Figure(data=[go.Pie(
        labels=['Your Ownership', 'Other Shareholders'],
        values=[ownership_pct, remaining_pct],
        hole=.3,
        marker_colors=['#FF6B35', '#E8E8E8']
    )])
    
    fig.update_layout(
        title=f"Your Ownership of {result['ticker']}",
        showlegend=True,
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_comparison_charts(comparison_data: List[Dict], investment_amount: float):
    """Render comparison charts for multiple stocks."""
    
    # Extract data for charts
    tickers = [item['ticker'] for item in comparison_data]
    shares = [item['shares'] for item in comparison_data]
    prices = [item['current_price'] for item in comparison_data]
    ownership_pcts = [item['percentage_of_share'] for item in comparison_data]
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Fractional Shares Purchased',
            'Stock Prices',
            'Ownership Percentage',
            'Annual Dividends'
        ),
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Shares purchased
    fig.add_trace(
        go.Bar(x=tickers, y=shares, name="Shares", marker_color='#FF6B35'),
        row=1, col=1
    )
    
    # Stock prices
    fig.add_trace(
        go.Bar(x=tickers, y=prices, name="Price", marker_color='#1A759F'),
        row=1, col=2
    )
    
    # Ownership percentages
    fig.add_trace(
        go.Bar(x=tickers, y=ownership_pcts, name="Ownership %", marker_color='#00BA6D'),
        row=2, col=1
    )
    
    # Annual dividends
    dividends = [item['annual_dividend'] for item in comparison_data]
    fig.add_trace(
        go.Bar(x=tickers, y=dividends, name="Dividend", marker_color='#F5B800'),
        row=2, col=2
    )
    
    fig.update_layout(
        title=f"Fractional Share Comparison - ${investment_amount:.0f} Investment",
        showlegend=False,
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_portfolio_chart(portfolio: List[Dict]):
    """Render portfolio allocation chart."""
    
    tickers = [pos['ticker'] for pos in portfolio]
    allocations = [pos['allocation_percentage'] for pos in portfolio]
    
    fig = go.Figure(data=[go.Pie(
        labels=tickers,
        values=allocations,
        hole=.3
    )])
    
    fig.update_layout(
        title="Portfolio Allocation",
        showlegend=True,
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_growth_chart(growth_data: Dict):
    """Render growth projection chart."""
    
    years = list(range(growth_data['projection_years'] + 1))
    initial_amount = growth_data['investment_amount']
    
    scenarios = {}
    for scenario, data in growth_data['projections'].items():
        annual_return = data['annualized_return'] / 100
        values = [initial_amount * ((1 + annual_return) ** year) for year in years]
        scenarios[scenario] = values
    
    fig = go.Figure()
    
    colors = {'conservative': '#00BA6D', 'moderate': '#FF6B35', 'optimistic': '#1A759F'}
    
    for scenario, values in scenarios.items():
        fig.add_trace(go.Scatter(
            x=years,
            y=values,
            mode='lines+markers',
            name=scenario.title(),
            line=dict(color=colors.get(scenario, '#000000'))
        ))
    
    fig.update_layout(
        title=f"Growth Projections for {growth_data['ticker']}",
        xaxis_title="Years",
        yaxis_title="Portfolio Value ($)",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_personalized_insights(result: Dict, user_profile: Dict):
    """Render personalized insights based on user profile."""
    
    st.markdown("### 🎯 Personalized Insights")
    
    age_range = user_profile.get('age_range', '')
    risk_profile = user_profile.get('risk_profile', 'moderate')
    primary_goal = user_profile.get('primary_goal', 'wealth_building')
    timeline = user_profile.get('timeline', '5-10 years')
    
    insights = []
    
    # Age-based insights
    if any(age in age_range for age in ['16-20', '21-25']):
        insights.append(f"💡 As a young investor, fractional shares in {result['ticker']} let you start building wealth early with small amounts.")
    
    # Risk-based insights
    if risk_profile == 'conservative' and result['annual_dividend_income'] > 0:
        insights.append(f"💰 With your conservative approach, the ${result['annual_dividend_income']:.2f} annual dividend from this position provides steady income.")
    elif risk_profile == 'aggressive':
        insights.append(f"🚀 Your aggressive risk profile aligns well with fractional investing - you can diversify across multiple growth stocks.")
    
    # Goal-based insights
    if 'wealth' in primary_goal:
        insights.append(f"📈 For wealth building, consider dollar-cost averaging into {result['ticker']} fractional shares monthly.")
    elif 'income' in primary_goal and result['annual_dividend_income'] > 0:
        insights.append(f"💵 This position would generate ${result['annual_dividend_income']:.2f} annually - good for your income goal.")
    
    # Timeline-based insights
    if 'long' in timeline.lower():
        insights.append(f"⏰ With your long-term timeline, fractional shares allow you to start early and benefit from compound growth.")
    
    for insight in insights:
        st.markdown(insight)


def extract_user_profile_for_fractional() -> Dict[str, str]:
    """Extract user profile data for fractional share personalization."""
    
    # Get user preferences from session state (same as analysis.py pattern)
    user_preferences = st.session_state.get('user_preferences', {})
    
    if not user_preferences:
        return {}
    
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
    
    # Extract experience level
    experience = user_preferences.get('experience_level', 'beginner')
    
    # Map to standardized format
    profile = {
        'age_range': age_range or '25-35',
        'income_range': income_range or '50k-100k',
        'primary_goal': primary_goal or 'wealth_building',
        'timeline': timeline or '5-10 years',
        'risk_profile': risk_profile.lower() if risk_profile else 'moderate',
        'experience': experience
    }
    
    return profile


def track_fractional_calculation():
    """Track fractional share calculation usage."""
    
    # Update session state counter
    current_count = st.session_state.get('fractional_calculations_count', 0)
    st.session_state.fractional_calculations_count = current_count + 1
    
    # Track in analytics
    user_id = st.session_state.get('user_email', 'anonymous')
    track_feature_usage(user_id, 'fractional_calculation')