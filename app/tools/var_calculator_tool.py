import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
from datetime import datetime, timedelta
from typing import List, Dict
from langchain.tools import BaseTool

class VaRCalculatorTool(BaseTool):
    name: str = "var_calculator"
    description: str = """
    Calculates Value at Risk (VaR) and Conditional VaR (CVaR) using multiple methods.
    Provides risk metrics at different confidence levels.
    """

    def _run(self, tickers: List[str], portfolio_value: float = 100000,
             holding_period: int = 10, confidence_levels: List[float] = None) -> Dict:
        """Calculate VaR and CVaR for a portfolio."""

        if confidence_levels is None:
            confidence_levels = [0.90, 0.95, 0.99]

        # Download historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 2)  # 2 years

        # Equal weights for simplicity (can be modified)
        weights = np.array([1 / len(tickers)] * len(tickers))

        # Get price data
        data = yf.download(tickers, start=start_date, end=end_date)['Adj Close']
        if len(tickers) == 1:
            data = pd.DataFrame(data, columns=tickers)

        # Calculate returns
        returns = data.pct_change().dropna()

        # Portfolio returns
        portfolio_returns = returns.dot(weights)

        # Scale returns to holding period
        holding_period_returns = portfolio_returns * np.sqrt(holding_period)

        results = {}

        # 1. Historical Method
        historical_var = {}
        historical_cvar = {}

        for conf in confidence_levels:
            var_threshold = np.percentile(holding_period_returns, (1 - conf) * 100)
            historical_var[f'{int(conf * 100)}%'] = abs(var_threshold * portfolio_value)

            # CVaR (Expected Shortfall)
            cvar_returns = holding_period_returns[holding_period_returns <= var_threshold]
            if len(cvar_returns) > 0:
                historical_cvar[f'{int(conf * 100)}%'] = abs(cvar_returns.mean() * portfolio_value)
            else:
                historical_cvar[f'{int(conf * 100)}%'] = historical_var[f'{int(conf * 100)}%']

        # 2. Parametric Method (assumes normal distribution)
        mean_return = portfolio_returns.mean() * holding_period
        std_return = portfolio_returns.std() * np.sqrt(holding_period)

        parametric_var = {}
        parametric_cvar = {}

        for conf in confidence_levels:
            z_score = norm.ppf(1 - conf)
            parametric_var[f'{int(conf * 100)}%'] = abs(z_score * std_return * portfolio_value)

            # CVaR for normal distribution
            cvar_multiplier = norm.pdf(norm.ppf(1 - conf)) / (1 - conf)
            parametric_cvar[f'{int(conf * 100)}%'] = abs(std_return * cvar_multiplier * portfolio_value)

        # 3. Monte Carlo Method
        n_simulations = 10000
        simulated_returns = np.random.normal(
            mean_return, std_return, n_simulations
        )

        mc_var = {}
        mc_cvar = {}

        for conf in confidence_levels:
            var_threshold = np.percentile(simulated_returns, (1 - conf) * 100)
            mc_var[f'{int(conf * 100)}%'] = abs(var_threshold * portfolio_value)

            cvar_returns = simulated_returns[simulated_returns <= var_threshold]
            mc_cvar[f'{int(conf * 100)}%'] = abs(cvar_returns.mean() * portfolio_value)

        # Additional risk metrics
        annual_volatility = portfolio_returns.std() * np.sqrt(252)
        annual_return = portfolio_returns.mean() * 252
        sharpe_ratio = annual_return / annual_volatility if annual_volatility != 0 else 0

        # Downside deviation
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0

        # Maximum drawdown
        cumulative_returns = (1 + portfolio_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(drawdown.min())

        return {
            'portfolio_composition': {
                'tickers': tickers,
                'weights': dict(zip(tickers, weights.round(4))),
                'portfolio_value': portfolio_value,
                'holding_period_days': holding_period
            },
            'var_historical': {k: round(v, 2) for k, v in historical_var.items()},
            'cvar_historical': {k: round(v, 2) for k, v in historical_cvar.items()},
            'var_parametric': {k: round(v, 2) for k, v in parametric_var.items()},
            'cvar_parametric': {k: round(v, 2) for k, v in parametric_cvar.items()},
            'var_monte_carlo': {k: round(v, 2) for k, v in mc_var.items()},
            'cvar_monte_carlo': {k: round(v, 2) for k, v in mc_cvar.items()},
            'portfolio_metrics': {
                'annual_return': round(annual_return * 100, 2),
                'annual_volatility': round(annual_volatility * 100, 2),
                'sharpe_ratio': round(sharpe_ratio, 4),
                'downside_deviation': round(downside_deviation * 100, 2),
                'max_drawdown': round(max_drawdown * 100, 2),
                'skewness': round(portfolio_returns.skew(), 4),
                'kurtosis': round(portfolio_returns.kurtosis(), 4)
            },
            'interpretation': {
                '95%_var_interpretation': f"There's a 5% chance of losing more than ${historical_var['95%']:,.2f} over {holding_period} days",
                'cvar_interpretation': f"If losses exceed VaR, average loss would be ${historical_cvar['95%']:,.2f}"
            }
        }