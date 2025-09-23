import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class PortfolioOptimizationInput(BaseModel):
    """Input schema for portfolio optimization."""
    tickers: List[str] = Field(description="List of stock tickers")
    start_date: Optional[str] = Field(default=None, description="Start date for historical data")
    target_return: Optional[float] = Field(default=None, description="Target annual return")


class PortfolioOptimizationTool(BaseTool):
    name: str = "portfolio_optimization"
    description: str = """
    Optimizes portfolio allocation using Modern Portfolio Theory (Markowitz).
    Returns optimal weights, expected return, volatility, and Sharpe ratio.
    """
    args_schema: type[BaseModel] = PortfolioOptimizationInput

    def _run(self, tickers: List[str], start_date: Optional[str] = None,
             target_return: Optional[float] = None) -> Dict:
        """Execute portfolio optimization."""

        # Set default start date if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        # Download historical data
        data = yf.download(tickers, start=start_date, end=datetime.now().strftime('%Y-%m-%d'))['Adj Close']

        # Calculate returns
        returns = data.pct_change().dropna()

        # Calculate expected returns and covariance
        mean_returns = returns.mean() * 252  # Annualized
        cov_matrix = returns.cov() * 252  # Annualized

        # Number of assets
        n_assets = len(tickers)

        # Define optimization functions
        def portfolio_stats(weights):
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            sharpe_ratio = portfolio_return / portfolio_std
            return portfolio_return, portfolio_std, sharpe_ratio

        def negative_sharpe(weights):
            return -portfolio_stats(weights)[2]

        def portfolio_variance(weights):
            return np.dot(weights.T, np.dot(cov_matrix, weights))

        # Constraints
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]  # weights sum to 1

        # Add target return constraint if specified
        if target_return:
            constraints.append({
                'type': 'eq',
                'fun': lambda x: np.dot(x, mean_returns) - target_return
            })

        # Bounds (0 to 1 for each weight - no short selling)
        bounds = tuple((0, 1) for _ in range(n_assets))

        # Initial guess (equal weights)
        init_weights = np.array([1 / n_assets] * n_assets)

        # Optimize for maximum Sharpe ratio
        max_sharpe = minimize(negative_sharpe, init_weights, method='SLSQP',
                              bounds=bounds, constraints=constraints)

        # Optimize for minimum volatility
        min_vol = minimize(portfolio_variance, init_weights, method='SLSQP',
                           bounds=bounds, constraints=constraints)

        # Calculate efficient frontier
        target_returns = np.linspace(mean_returns.min(), mean_returns.max(), 50)
        efficient_frontier = []

        for target in target_returns:
            constraints_ef = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                {'type': 'eq', 'fun': lambda x, target=target: np.dot(x, mean_returns) - target}
            ]
            result = minimize(portfolio_variance, init_weights, method='SLSQP',
                              bounds=bounds, constraints=constraints_ef)
            if result.success:
                ret, std, _ = portfolio_stats(result.x)
                efficient_frontier.append({'return': ret, 'volatility': std})

        # Prepare results
        max_sharpe_stats = portfolio_stats(max_sharpe.x)
        min_vol_stats = portfolio_stats(min_vol.x)

        return {
            'max_sharpe_portfolio': {
                'weights': dict(zip(tickers, max_sharpe.x.round(4))),
                'expected_return': round(max_sharpe_stats[0], 4),
                'volatility': round(max_sharpe_stats[1], 4),
                'sharpe_ratio': round(max_sharpe_stats[2], 4)
            },
            'min_volatility_portfolio': {
                'weights': dict(zip(tickers, min_vol.x.round(4))),
                'expected_return': round(min_vol_stats[0], 4),
                'volatility': round(min_vol_stats[1], 4),
                'sharpe_ratio': round(min_vol_stats[2], 4)
            },
            'efficient_frontier': efficient_frontier,
            'individual_returns': dict(zip(tickers, mean_returns.round(4))),
            'correlation_matrix': returns.corr().round(4).to_dict()
        }