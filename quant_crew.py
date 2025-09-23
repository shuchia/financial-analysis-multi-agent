# =====================================
# File: quant_crew.py
# Enhanced crew configuration with quantitative analysis
# =====================================

from crewai import Agent, Crew, Task
from langchain_aws import BedrockChat
from tools.portfolio_optimization_tool import PortfolioOptimizationTool
from tools.monte_carlo_tool import MonteCarloSimulationTool
from tools.backtesting_tool import BacktestingTool
from tools.pairs_trading_tool import PairsTradingTool
from tools.options_pricing_tool import OptionsPricingTool
from tools.var_calculator_tool import VaRCalculatorTool
# Import existing tools
from tools.yf_tech_analysis_tool import YFinanceTechAnalysisTool
from tools.yf_fundamental_analysis_tool import YFinanceFundamentalAnalysisTool


class QuantitativeAnalysisCrew:
    """Enhanced crew with quantitative analysis capabilities."""

    def __init__(self):
        # Initialize LLM
        self.llm = BedrockChat(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            model_kwargs={"temperature": 0.1}
        )

        # Initialize all tools
        self.portfolio_opt_tool = PortfolioOptimizationTool()
        self.monte_carlo_tool = MonteCarloSimulationTool()
        self.backtesting_tool = BacktestingTool()
        self.pairs_trading_tool = PairsTradingTool()
        self.options_tool = OptionsPricingTool()
        self.var_tool = VaRCalculatorTool()
        self.tech_tool = YFinanceTechAnalysisTool()
        self.fundamental_tool = YFinanceFundamentalAnalysisTool()

    def create_agents(self):
        """Create specialized agents for quantitative analysis."""

        # Quantitative Portfolio Manager
        self.portfolio_manager = Agent(
            role="Quantitative Portfolio Manager",
            goal="Optimize portfolio allocation using Modern Portfolio Theory and advanced risk metrics",
            backstory="""You are a seasoned quantitative portfolio manager with expertise in 
            MPT, risk management, and portfolio optimization. You use mathematical models 
            to create efficient portfolios that maximize returns for given risk levels.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.portfolio_opt_tool, self.var_tool],
            llm=self.llm
        )

        # Risk Analyst
        self.risk_analyst = Agent(
            role="Quantitative Risk Analyst",
            goal="Analyze and quantify portfolio risk using VaR, Monte Carlo, and stress testing",
            backstory="""You are a risk management expert specializing in quantitative risk 
            assessment. You use statistical methods and simulations to measure potential losses 
            and help investors understand their risk exposure.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.monte_carlo_tool, self.var_tool],
            llm=self.llm
        )

        # Algorithmic Trader
        self.algo_trader = Agent(
            role="Algorithmic Trading Strategist",
            goal="Develop and backtest systematic trading strategies",
            backstory="""You are an algorithmic trading expert who develops, tests, and 
            validates trading strategies using historical data. You identify profitable 
            trading opportunities using quantitative methods.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.backtesting_tool, self.pairs_trading_tool, self.tech_tool],
            llm=self.llm
        )

        # Derivatives Specialist
        self.derivatives_specialist = Agent(
            role="Options and Derivatives Analyst",
            goal="Analyze options strategies and calculate fair values using pricing models",
            backstory="""You are a derivatives expert specializing in options pricing, 
            Greeks analysis, and hedging strategies. You help investors understand and 
            utilize options for both speculation and risk management.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.options_tool],
            llm=self.llm
        )

        # Keep existing agents
        self.researcher = Agent(
            role="Senior Stock Market Researcher",
            goal="Conduct comprehensive research on stocks and market conditions",
            backstory="""You are an experienced stock market researcher with deep knowledge 
            of financial markets, technical analysis, and fundamental analysis.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.tech_tool, self.fundamental_tool],
            llm=self.llm
        )

        return [
            self.portfolio_manager,
            self.risk_analyst,
            self.algo_trader,
            self.derivatives_specialist,
            self.researcher
        ]

    def create_tasks(self, user_input):
        """Create tasks based on user input."""

        tasks = []

        # Parse user input to determine task type
        input_lower = user_input.lower()

        # Portfolio Optimization Task
        if "portfolio" in input_lower or "optimize" in input_lower:
            tasks.append(Task(
                description=f"""Analyze and optimize portfolio allocation for: {user_input}
                1. Calculate efficient frontier
                2. Find maximum Sharpe ratio portfolio
                3. Determine minimum variance portfolio
                4. Provide allocation recommendations
                5. Include correlation analysis""",
                agent=self.portfolio_manager,
                expected_output="Detailed portfolio optimization report with weights and metrics"
            ))

        # Risk Analysis Task
        if "risk" in input_lower or "var" in input_lower:
            tasks.append(Task(
                description=f"""Perform comprehensive risk analysis for: {user_input}
                1. Calculate VaR at multiple confidence levels
                2. Run Monte Carlo simulation for risk assessment
                3. Calculate CVaR (Expected Shortfall)
                4. Analyze downside risk metrics
                5. Provide risk mitigation recommendations""",
                agent=self.risk_analyst,
                expected_output="Complete risk assessment report with VaR, CVaR, and simulations"
            ))

        # Backtesting Task
        if "backtest" in input_lower or "strategy" in input_lower:
            tasks.append(Task(
                description=f"""Backtest trading strategies for: {user_input}
                1. Test moving average crossover strategy
                2. Evaluate RSI-based strategy
                3. Compare with buy-and-hold
                4. Calculate Sharpe ratio and maximum drawdown
                5. Provide strategy recommendations""",
                agent=self.algo_trader,
                expected_output="Backtesting results with performance metrics and trade history"
            ))

        # Pairs Trading Task
        if "pairs" in input_lower or "arbitrage" in input_lower:
            tasks.append(Task(
                description=f"""Identify pairs trading opportunities for: {user_input}
                1. Find cointegrated pairs
                2. Calculate spread statistics
                3. Identify current trading signals
                4. Analyze correlation patterns
                5. Provide entry/exit recommendations""",
                agent=self.algo_trader,
                expected_output="Pairs trading analysis with identified opportunities"
            ))

        # Options Analysis Task
        if "option" in input_lower or "calls" in input_lower or "puts" in input_lower:
            tasks.append(Task(
                description=f"""Analyze options strategies for: {user_input}
                1. Calculate theoretical option prices
                2. Compute all Greeks (Delta, Gamma, Theta, Vega, Rho)
                3. Analyze different strike prices and expirations
                4. Evaluate risk/reward profiles
                5. Suggest optimal strategies""",
                agent=self.derivatives_specialist,
                expected_output="Options analysis with pricing, Greeks, and strategy recommendations"
            ))

        # Default comprehensive analysis if no specific task detected
        if not tasks:
            tasks.append(Task(
                description=f"""Perform comprehensive quantitative analysis for: {user_input}
                1. Technical and fundamental analysis
                2. Risk assessment
                3. Portfolio optimization suggestions
                4. Trading strategy evaluation""",
                agent=self.researcher,
                expected_output="Complete market analysis with actionable insights"
            ))

        return tasks

    def analyze(self, user_input):
        """Run the quantitative analysis crew."""

        # Create agents and tasks
        agents = self.create_agents()
        tasks = self.create_tasks(user_input)

        # Create and run crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            verbose=True
        )

        result = crew.kickoff()
        return result


# =====================================
# File: enhanced_app.py
# Enhanced Streamlit app with quantitative features
# =====================================

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from quant_crew import QuantitativeAnalysisCrew

# Page configuration
st.set_page_config(
    page_title="Advanced Financial Analysis Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Header
    st.title("🚀 Advanced Financial Analysis Platform")
    st.markdown("### Powered by Quantitative Analysis & AI")

    # Sidebar for configuration
    with st.sidebar:
        st.header("Analysis Configuration")

        analysis_type = st.selectbox(
            "Select Analysis Type",
            ["Portfolio Optimization", "Risk Analysis", "Backtesting",
             "Pairs Trading", "Options Analysis", "Comprehensive Analysis"]
        )

        # Input method
        input_method = st.radio(
            "Input Method",
            ["Single Stock", "Multiple Stocks", "Sector Analysis"]
        )

        if input_method == "Single Stock":
            ticker = st.text_input("Enter Stock Symbol", value="AAPL")
            tickers = [ticker]
        elif input_method == "Multiple Stocks":
            tickers_input = st.text_input(
                "Enter Stock Symbols (comma-separated)",
                value="AAPL,GOOGL,MSFT,AMZN"
            )
            tickers = [t.strip() for t in tickers_input.split(",")]
        else:
            sector = st.selectbox(
                "Select Sector",
                ["Technology", "Healthcare", "Finance", "Energy", "Consumer"]
            )
            # Predefined sector stocks
            sector_stocks = {
                "Technology": ["AAPL", "GOOGL", "MSFT", "NVDA", "META"],
                "Healthcare": ["JNJ", "PFE", "UNH", "CVS", "ABBV"],
                "Finance": ["JPM", "BAC", "WFC", "GS", "MS"],
                "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
                "Consumer": ["AMZN", "TSLA", "HD", "WMT", "NKE"]
            }
            tickers = sector_stocks[sector]

        # Advanced parameters
        with st.expander("Advanced Parameters"):
            if analysis_type == "Portfolio Optimization":
                target_return = st.slider("Target Annual Return (%)", 0, 50, 15) / 100
                st.session_state['target_return'] = target_return

            elif analysis_type == "Risk Analysis":
                portfolio_value = st.number_input("Portfolio Value ($)", value=100000)
                holding_period = st.slider("Holding Period (days)", 1, 30, 10)
                st.session_state['portfolio_value'] = portfolio_value
                st.session_state['holding_period'] = holding_period

            elif analysis_type == "Backtesting":
                strategy = st.selectbox(
                    "Strategy Type",
                    ["Moving Average", "RSI", "Mean Reversion"]
                )
                initial_capital = st.number_input("Initial Capital ($)", value=10000)
                st.session_state['strategy'] = strategy
                st.session_state['initial_capital'] = initial_capital

            elif analysis_type == "Options Analysis":
                strike_price = st.number_input("Strike Price", value=150.0)
                expiry_days = st.slider("Days to Expiry", 1, 365, 30)
                option_type = st.radio("Option Type", ["Call", "Put"])
                st.session_state['strike_price'] = strike_price
                st.session_state['expiry_days'] = expiry_days
                st.session_state['option_type'] = option_type.lower()

    # Main content area with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Analysis", "📈 Visualizations", "📋 Report", "🎓 Education"])

    with tab1:
        col1, col2 = st.columns([2, 1])

        with col1:
            if st.button("🔍 Run Analysis", type="primary", use_container_width=True):
                with st.spinner("Running quantitative analysis..."):
                    # Initialize crew
                    crew = QuantitativeAnalysisCrew()

                    # Prepare input based on analysis type
                    if analysis_type == "Portfolio Optimization":
                        user_input = f"Optimize portfolio for stocks: {','.join(tickers)}"
                    elif analysis_type == "Risk Analysis":
                        user_input = f"Calculate risk metrics for: {','.join(tickers)}"
                    elif analysis_type == "Backtesting":
                        user_input = f"Backtest strategy for: {tickers[0]}"
                    elif analysis_type == "Pairs Trading":
                        user_input = f"Find pairs trading opportunities in: {','.join(tickers)}"
                    elif analysis_type == "Options Analysis":
                        user_input = f"Analyze options for: {tickers[0]}"
                    else:
                        user_input = f"Comprehensive analysis for: {','.join(tickers)}"

                    # Run analysis
                    result = crew.analyze(user_input)

                    # Store result in session state
                    st.session_state['analysis_result'] = result
                    st.session_state['tickers'] = tickers
                    st.session_state['analysis_type'] = analysis_type

        # Display results
        if 'analysis_result' in st.session_state:
            st.markdown("### Analysis Results")

            # Format and display based on analysis type
            if st.session_state['analysis_type'] == "Portfolio Optimization":
                display_portfolio_optimization_results()
            elif st.session_state['analysis_type'] == "Risk Analysis":
                display_risk_analysis_results()
            elif st.session_state['analysis_type'] == "Backtesting":
                display_backtesting_results()
            elif st.session_state['analysis_type'] == "Pairs Trading":
                display_pairs_trading_results()
            elif st.session_state['analysis_type'] == "Options Analysis":
                display_options_analysis_results()
            else:
                st.write(st.session_state['analysis_result'])

    with tab2:
        if 'tickers' in st.session_state:
            create_interactive_visualizations(st.session_state['tickers'])

    with tab3:
        if 'analysis_result' in st.session_state:
            generate_report()

    with tab4:
        display_educational_content()


def display_portfolio_optimization_results():
    """Display portfolio optimization results with metrics."""
    st.markdown("#### Optimal Portfolio Allocation")

    col1, col2, col3 = st.columns(3)

    # Mock results (replace with actual crew output parsing)
    with col1:
        st.metric("Expected Return", "15.2%", "2.3%")
    with col2:
        st.metric("Volatility", "18.5%", "-1.2%")
    with col3:
        st.metric("Sharpe Ratio", "0.82", "0.15")

    # Allocation pie chart
    fig = go.Figure(data=[go.Pie(
        labels=['AAPL', 'GOOGL', 'MSFT', 'AMZN'],
        values=[30, 25, 25, 20],
        hole=.3
    )])
    fig.update_layout(title="Portfolio Allocation")
    st.plotly_chart(fig, use_container_width=True)


def display_risk_analysis_results():
    """Display risk analysis results."""
    st.markdown("#### Risk Metrics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Value at Risk (VaR)")
        var_data = pd.DataFrame({
            'Confidence Level': ['90%', '95%', '99%'],
            'Historical VaR': [8500, 12000, 18000],
            'Parametric VaR': [8800, 12500, 19000],
            'Monte Carlo VaR': [8600, 12200, 18500]
        })
        st.dataframe(var_data)

    with col2:
        st.markdown("##### Conditional VaR (CVaR)")
        cvar_data = pd.DataFrame({
            'Confidence Level': ['90%', '95%', '99%'],
            'Historical CVaR': [10500, 15000, 22000],
            'Parametric CVaR': [10800, 15500, 23000],
            'Monte Carlo CVaR': [10600, 15200, 22500]
        })
        st.dataframe(cvar_data)


def display_backtesting_results():
    """Display backtesting results."""
    st.markdown("#### Strategy Performance")

    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

    with metrics_col1:
        st.metric("Total Return", "32.5%", "12.3%")
    with metrics_col2:
        st.metric("Sharpe Ratio", "1.24", "0.35")
    with metrics_col3:
        st.metric("Max Drawdown", "-15.2%", "3.1%")
    with metrics_col4:
        st.metric("Win Rate", "58%", "5%")


def display_pairs_trading_results():
    """Display pairs trading opportunities."""
    st.markdown("#### Cointegrated Pairs")

    pairs_data = pd.DataFrame({
        'Pair': ['AAPL-MSFT', 'GOOGL-META', 'NVDA-AMD'],
        'Correlation': [0.85, 0.78, 0.82],
        'P-Value': [0.012, 0.023, 0.018],
        'Z-Score': [-2.3, 1.8, -2.1],
        'Signal': ['BUY', 'HOLD', 'BUY']
    })

    st.dataframe(pairs_data, use_container_width=True)


def display_options_analysis_results():
    """Display options analysis results."""
    st.markdown("#### Option Pricing & Greeks")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Option Value")
        st.metric("Theoretical Price", "$12.45")
        st.metric("Intrinsic Value", "$8.00")
        st.metric("Time Value", "$4.45")

    with col2:
        st.markdown("##### Greeks")
        greeks = pd.DataFrame({
            'Greek': ['Delta', 'Gamma', 'Theta', 'Vega', 'Rho'],
            'Value': [0.65, 0.023, -0.045, 0.182, 0.095]
        })
        st.dataframe(greeks)


def create_interactive_visualizations(tickers):
    """Create interactive visualizations for the selected stocks."""
    st.markdown("### Interactive Charts")

    # Download data for visualization
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    data = yf.download(tickers, start=start_date, end=end_date)

    # Price chart
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3]
    )

    for ticker in tickers:
        if len(tickers) > 1:
            prices = data['Adj Close'][ticker]
        else:
            prices = data['Adj Close']

        fig.add_trace(
            go.Scatter(x=data.index, y=prices, name=ticker),
            row=1, col=1
        )

    # Volume
    if len(tickers) == 1:
        fig.add_trace(
            go.Bar(x=data.index, y=data['Volume'], name='Volume'),
            row=2, col=1
        )

    fig.update_layout(
        title="Price History",
        xaxis_title="Date",
        yaxis_title="Price",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)


def generate_report():
    """Generate a downloadable report."""
    st.markdown("### Analysis Report")

    report_content = f"""
    # Financial Analysis Report
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

    ## Analysis Type: {st.session_state.get('analysis_type', 'N/A')}
    ## Securities Analyzed: {', '.join(st.session_state.get('tickers', []))}

    ## Key Findings:
    {st.session_state.get('analysis_result', 'No results available')}
    """

    st.text_area("Report Preview", report_content, height=400)

    st.download_button(
        label="📥 Download Report",
        data=report_content,
        file_name=f"financial_analysis_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain"
    )


def display_educational_content():
    """Display educational content for users."""
    st.markdown("### Learn About Quantitative Analysis")

    with st.expander("📚 Modern Portfolio Theory"):
        st.markdown("""
        **Modern Portfolio Theory (MPT)** is a mathematical framework for assembling a portfolio 
        of assets to maximize expected return for a given level of risk.

        Key concepts:
        - **Efficient Frontier**: The set of optimal portfolios offering the highest expected return for each risk level
        - **Sharpe Ratio**: Measures risk-adjusted returns (Return - Risk Free Rate) / Standard Deviation
        - **Diversification**: Reducing risk by investing in uncorrelated assets
        """)

    with st.expander("📊 Value at Risk (VaR)"):
        st.markdown("""
        **Value at Risk (VaR)** estimates the potential loss in value of a portfolio over a defined period 
        for a given confidence interval.

        - **95% VaR of $10,000**: There's a 5% chance of losing more than $10,000
        - **CVaR (Conditional VaR)**: The expected loss when losses exceed the VaR threshold
        - **Methods**: Historical, Parametric, Monte Carlo simulation
        """)

    with st.expander("🎯 Options Greeks"):
        st.markdown("""
        **Greeks** measure sensitivities of option prices to various factors:

        - **Delta (Δ)**: Price change per $1 stock move
        - **Gamma (Γ)**: Rate of change of Delta
        - **Theta (Θ)**: Time decay per day
        - **Vega (ν)**: Sensitivity to volatility
        - **Rho (ρ)**: Sensitivity to interest rates
        """)


if __name__ == "__main__":
    main()