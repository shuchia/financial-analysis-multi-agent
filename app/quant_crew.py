# =====================================
# File: quant_crew.py
# Enhanced crew configuration with quantitative analysis
# =====================================

from crewai import Agent, Crew, Task, LLM
import os
from tools.portfolio_optimization_tool import portfolio_optimization
from tools.var_calculator_tool import var_calculator, _var_calculator_impl
# Import existing tools
from tools.yf_tech_analysis_tool import yf_tech_analysis
from tools.yf_fundamental_analysis_tool import yf_fundamental_analysis

# For now, use only the tools we know work
# TODO: Fix the other tools when needed
MonteCarloSimulationTool = None
BacktestingTool = None  
PairsTradingTool = None
OptionsPricingTool = None


class QuantitativeAnalysisCrew:
    """Enhanced crew with quantitative analysis capabilities."""

    def __init__(self):
        # Initialize LLM - use same setup as portfoliocrew.py
        self.llm = LLM(
            model="anthropic.claude-3-haiku-20240307-v1:0",
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        )

        # Initialize core tools (always available)
        self.portfolio_opt_tool = portfolio_optimization
        self.var_tool = var_calculator
        self.tech_tool = yf_tech_analysis
        self.fundamental_tool = yf_fundamental_analysis
        
        # Initialize optional tools if available
        self.monte_carlo_tool = MonteCarloSimulationTool() if MonteCarloSimulationTool else None
        self.backtesting_tool = BacktestingTool() if BacktestingTool else None
        self.pairs_trading_tool = PairsTradingTool() if PairsTradingTool else None
        self.options_tool = OptionsPricingTool() if OptionsPricingTool else None

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
        risk_tools = [self.var_tool]
        if self.monte_carlo_tool:
            risk_tools.append(self.monte_carlo_tool)
            
        self.risk_analyst = Agent(
            role="Quantitative Risk Analyst",
            goal="Analyze and quantify portfolio risk using VaR, Monte Carlo, and stress testing",
            backstory="""You are a risk management expert specializing in quantitative risk 
            assessment. You use statistical methods and simulations to measure potential losses 
            and help investors understand their risk exposure.""",
            verbose=True,
            allow_delegation=False,
            tools=risk_tools,
            llm=self.llm
        )

        # Algorithmic Trader (only create if tools are available)
        algo_tools = [self.tech_tool]
        if self.backtesting_tool:
            algo_tools.append(self.backtesting_tool)
        if self.pairs_trading_tool:
            algo_tools.append(self.pairs_trading_tool)
            
        self.algo_trader = Agent(
            role="Algorithmic Trading Strategist",
            goal="Develop and backtest systematic trading strategies",
            backstory="""You are an algorithmic trading expert who develops, tests, and 
            validates trading strategies using historical data. You identify profitable 
            trading opportunities using quantitative methods.""",
            verbose=True,
            allow_delegation=False,
            tools=algo_tools,
            llm=self.llm
        )

        # Derivatives Specialist (only create if options tool is available)
        if self.options_tool:
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
        else:
            self.derivatives_specialist = None

        # Return only available agents
        agents = [self.portfolio_manager, self.risk_analyst, self.algo_trader]
        if self.derivatives_specialist:
            agents.append(self.derivatives_specialist)
        return agents

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
                agent=self.portfolio_manager,  # Use portfolio_manager as default
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

    def optimize_portfolio(self, tickers, current_weights=None, user_profile=None, investment_amount=None):
        """Specific function for portfolio optimization using quant crew."""

        # Create portfolio manager agent
        self.create_agents()

        # Format tickers as comma-separated string for the tool
        tickers_string = ','.join(tickers) if isinstance(tickers, list) else str(tickers)

        # Format current weights if provided
        current_weights_string = None
        if current_weights:
            if isinstance(current_weights, list):
                current_weights_string = ','.join([str(w) for w in current_weights])
            else:
                current_weights_string = str(current_weights)

        portfolio_value = investment_amount if investment_amount else 10000
        user_risk = user_profile.get('risk_profile', 'moderate') if user_profile else 'moderate'

        # Create specific task for portfolio optimization
        optimization_task = Task(
            description=f"""Optimize the given portfolio allocation:

            PORTFOLIO DATA:
            - Tickers: {tickers_string}
            - Current Weights: {current_weights if current_weights else 'Equal weight'}
            - Investment Amount: ${portfolio_value:,.0f}
            - User Risk Profile: {user_risk}

            OPTIMIZATION REQUIREMENTS:
            1. Use the portfolio_optimization tool with these EXACT parameters:
               - tickers_string="{tickers_string}"
               - current_weights_string="{current_weights_string if current_weights_string else ''}"
               - investment_amount={portfolio_value}
               - user_risk_profile_string="{user_risk}"
            2. Consider the user's risk tolerance and constraints
            3. Provide before/after comparison if current weights provided
            4. Analyze the max_sharpe_portfolio and min_volatility_portfolio results
            5. Review the correlation matrix and efficient frontier data
            6. Suggest specific allocation changes with reasoning

            OUTPUT FORMAT:
            Provide a clear, structured report with:
            - Recommended Portfolio: Specific weights for each ticker
            - Expected Metrics: Return, volatility, and Sharpe ratio
            - Comparison: If current weights provided, show before/after metrics
            - Diversification Analysis: Review correlation matrix insights
            - Specific Recommendations: 3-5 actionable suggestions for improvements
            """,
            agent=self.portfolio_manager,
            expected_output="Portfolio optimization results with specific weights and metrics"
        )
        
        # Run optimization
        crew = Crew(
            agents=[self.portfolio_manager],
            tasks=[optimization_task],
            verbose=True
        )
        
        return crew.kickoff()
    
    def analyze_portfolio_risk(self, tickers, weights=None, user_profile=None, investment_amount=None):
        """Specific function for portfolio risk analysis using quant crew."""

        # BETTER APPROACH: Call the tool directly for structured data
        # Then optionally use AI for narrative interpretation

        # Format tickers as comma-separated string for the VaR tool
        tickers_string = ','.join(tickers) if isinstance(tickers, list) else str(tickers)
        portfolio_value = investment_amount if investment_amount else 10000
        user_risk = user_profile.get('risk_profile', 'moderate') if user_profile else 'moderate'

        # Call VaR calculator tool directly to get structured data
        tool_result = _var_calculator_impl(
            tickers_string=tickers_string,
            portfolio_value=portfolio_value,
            holding_period=10,
            confidence_levels_string="0.95,0.99"
        )

        # Check if tool returned an error
        if 'error' in tool_result:
            return {
                'raw': f"Error calculating risk metrics: {tool_result['error']}",
                'tool_output': tool_result,
                'tasks_output': []
            }

        # Create agents for narrative interpretation
        self.create_agents()

        # Create task that uses the tool output for narrative
        risk_task = Task(
            description=f"""Provide risk analysis narrative based on these calculated metrics:

            PORTFOLIO DATA:
            - Tickers: {tickers_string}
            - Portfolio Value: ${portfolio_value:,.0f}
            - User Risk Profile: {user_risk}

            CALCULATED RISK METRICS (from VaR calculator):
            {tool_result}

            YOUR TASK:
            Interpret these metrics and provide:
            1. Executive Summary: Overall risk level (Low/Moderate/High) based on the metrics
            2. Risk Alignment: Does this match the user's {user_risk} profile?
            3. Recommendations: 3-5 specific actions to optimize risk based on the actual metrics

            DO NOT recalculate metrics. Use the values provided above.
            """,
            agent=self.risk_analyst,
            expected_output="Risk interpretation and recommendations based on calculated metrics"
        )

        # Run narrative generation
        crew = Crew(
            agents=[self.risk_analyst],
            tasks=[risk_task],
            verbose=True
        )

        narrative_result = crew.kickoff()

        # Return both structured tool output AND narrative
        return {
            'tool_output': tool_result,  # Structured data
            'narrative': narrative_result,  # AI interpretation
            'tasks_output': narrative_result.tasks_output if hasattr(narrative_result, 'tasks_output') else []
        }

