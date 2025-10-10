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
    
    # Enhanced fields for portfolio analysis
    current_weights: Optional[List[float]] = Field(default=None, description="Current portfolio weights")
    optimization_mode: Optional[str] = Field(default="full", description="full|enhance|rebalance")
    constraints: Optional[Dict] = Field(default=None, description="User constraints")
    user_risk_profile: Optional[Dict] = Field(default=None, description="User risk preferences")
    investment_amount: Optional[float] = Field(default=None, description="Total investment amount")


class PortfolioOptimizationTool(BaseTool):
    name: str = "portfolio_optimization"
    description: str = """
    Optimizes portfolio allocation using Modern Portfolio Theory (Markowitz).
    Returns optimal weights, expected return, volatility, and Sharpe ratio.
    """
    args_schema: type[BaseModel] = PortfolioOptimizationInput

    def _run(self, tickers: List[str], start_date: Optional[str] = None,
             target_return: Optional[float] = None, current_weights: Optional[List[float]] = None,
             optimization_mode: Optional[str] = "full", constraints: Optional[Dict] = None,
             user_risk_profile: Optional[Dict] = None, investment_amount: Optional[float] = None) -> Dict:
        """Execute portfolio optimization with multiple modes."""

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

        # Handle different optimization modes
        if optimization_mode == "enhance" and current_weights is not None:
            return self._enhance_existing_portfolio(
                tickers, current_weights, mean_returns, cov_matrix, 
                user_risk_profile, investment_amount
            )
        elif optimization_mode == "rebalance" and current_weights is not None:
            return self._rebalance_portfolio(
                tickers, current_weights, mean_returns, cov_matrix,
                user_risk_profile, constraints
            )
        
        # Default full optimization
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
    
    def _enhance_existing_portfolio(self, tickers, current_weights, mean_returns, cov_matrix, 
                                    user_risk_profile, investment_amount):
        """Enhance existing portfolio with minimal changes."""
        current_weights = np.array(current_weights)
        n_assets = len(tickers)
        
        # Calculate current portfolio stats
        current_return = np.dot(current_weights, mean_returns)
        current_std = np.sqrt(np.dot(current_weights.T, np.dot(cov_matrix, current_weights)))
        current_sharpe = current_return / current_std if current_std > 0 else 0
        
        # Define objective: minimize tracking error while improving Sharpe
        def enhanced_objective(weights):
            # Portfolio stats
            port_return = np.dot(weights, mean_returns)
            port_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            sharpe = port_return / port_std if port_std > 0 else 0
            
            # Tracking error (penalize large deviations from current)
            tracking_error = np.sqrt(np.sum((weights - current_weights) ** 2))
            
            # Objective: maximize Sharpe improvement while minimizing changes
            # Higher alpha = more emphasis on Sharpe improvement
            alpha = 0.7 if user_risk_profile and user_risk_profile.get('risk_profile') == 'aggressive' else 0.5
            return -alpha * sharpe + (1 - alpha) * tracking_error
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # weights sum to 1
        ]
        
        # Add risk constraint based on user profile
        if user_risk_profile:
            risk_tolerance = user_risk_profile.get('risk_score', 0.5)
            max_volatility = current_std * (1 + risk_tolerance * 0.2)  # Allow up to 20% increase
            constraints.append({
                'type': 'ineq',
                'fun': lambda x: max_volatility - np.sqrt(np.dot(x.T, np.dot(cov_matrix, x)))
            })
        
        # Bounds - allow limited deviation from current weights
        max_change = 0.15  # Maximum 15% change per position
        bounds = []
        for i in range(n_assets):
            lower = max(0, current_weights[i] - max_change)
            upper = min(1, current_weights[i] + max_change)
            bounds.append((lower, upper))
        
        # Optimize
        result = minimize(enhanced_objective, current_weights, method='SLSQP',
                         bounds=bounds, constraints=constraints)
        
        # Calculate enhanced portfolio stats
        enhanced_weights = result.x
        enhanced_return = np.dot(enhanced_weights, mean_returns)
        enhanced_std = np.sqrt(np.dot(enhanced_weights.T, np.dot(cov_matrix, enhanced_weights)))
        enhanced_sharpe = enhanced_return / enhanced_std if enhanced_std > 0 else 0
        
        # Calculate changes
        weight_changes = enhanced_weights - current_weights
        
        return {
            'optimization_mode': 'enhance',
            'current_portfolio': {
                'weights': dict(zip(tickers, current_weights.round(4))),
                'expected_return': round(current_return, 4),
                'volatility': round(current_std, 4),
                'sharpe_ratio': round(current_sharpe, 4)
            },
            'enhanced_portfolio': {
                'weights': dict(zip(tickers, enhanced_weights.round(4))),
                'expected_return': round(enhanced_return, 4),
                'volatility': round(enhanced_std, 4),
                'sharpe_ratio': round(enhanced_sharpe, 4),
                'weight_changes': dict(zip(tickers, weight_changes.round(4)))
            },
            'improvements': {
                'return_increase': round((enhanced_return - current_return) * 100, 2),
                'sharpe_increase': round(enhanced_sharpe - current_sharpe, 4),
                'risk_change': round((enhanced_std - current_std) * 100, 2)
            },
            'recommendations': self._generate_enhancement_recommendations(
                tickers, current_weights, enhanced_weights, investment_amount
            )
        }
    
    def _rebalance_portfolio(self, tickers, current_weights, mean_returns, cov_matrix,
                            user_risk_profile, constraints):
        """Rebalance portfolio to match user risk profile."""
        current_weights = np.array(current_weights)
        n_assets = len(tickers)
        
        # Determine target risk level based on user profile
        if user_risk_profile:
            risk_score = user_risk_profile.get('risk_score', 0.5)
            risk_profile = user_risk_profile.get('risk_profile', 'moderate')
        else:
            risk_score = 0.5
            risk_profile = 'moderate'
        
        # Define target volatility based on risk profile
        # Conservative: 8-12%, Moderate: 12-18%, Aggressive: 18-25%
        if risk_profile == 'conservative':
            target_volatility = 0.10 + risk_score * 0.04
        elif risk_profile == 'aggressive':
            target_volatility = 0.18 + risk_score * 0.07
        else:  # moderate
            target_volatility = 0.12 + risk_score * 0.06
        
        # Objective: minimize distance to target volatility
        def rebalance_objective(weights):
            port_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            volatility_diff = abs(port_std - target_volatility)
            
            # Also consider return (secondary objective)
            port_return = np.dot(weights, mean_returns)
            
            # Combined objective
            return volatility_diff - 0.1 * port_return
        
        # Constraints
        opt_constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # weights sum to 1
        ]
        
        # Apply user constraints if provided
        if constraints:
            if 'min_positions' in constraints:
                # Ensure minimum number of positions have meaningful weight
                min_weight = 0.05
                opt_constraints.append({
                    'type': 'ineq',
                    'fun': lambda x: np.sum(x >= min_weight) - constraints['min_positions']
                })
        
        # Bounds
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        # Optimize
        result = minimize(rebalance_objective, current_weights, method='SLSQP',
                         bounds=bounds, constraints=opt_constraints)
        
        # Calculate rebalanced portfolio stats
        rebalanced_weights = result.x
        rebalanced_return = np.dot(rebalanced_weights, mean_returns)
        rebalanced_std = np.sqrt(np.dot(rebalanced_weights.T, np.dot(cov_matrix, rebalanced_weights)))
        rebalanced_sharpe = rebalanced_return / rebalanced_std if rebalanced_std > 0 else 0
        
        # Calculate current portfolio stats
        current_std = np.sqrt(np.dot(current_weights.T, np.dot(cov_matrix, current_weights)))
        
        return {
            'optimization_mode': 'rebalance',
            'target_risk_profile': risk_profile,
            'target_volatility': round(target_volatility * 100, 2),
            'rebalanced_portfolio': {
                'weights': dict(zip(tickers, rebalanced_weights.round(4))),
                'expected_return': round(rebalanced_return, 4),
                'volatility': round(rebalanced_std, 4),
                'sharpe_ratio': round(rebalanced_sharpe, 4)
            },
            'risk_alignment': {
                'current_volatility': round(current_std * 100, 2),
                'target_volatility': round(target_volatility * 100, 2),
                'rebalanced_volatility': round(rebalanced_std * 100, 2),
                'alignment_score': round(100 - abs(rebalanced_std - target_volatility) * 1000, 2)
            },
            'rebalancing_trades': self._calculate_rebalancing_trades(
                tickers, current_weights, rebalanced_weights
            )
        }
    
    def _generate_enhancement_recommendations(self, tickers, current_weights, enhanced_weights, investment_amount):
        """Generate specific recommendations for portfolio enhancement."""
        recommendations = []
        
        for i, ticker in enumerate(tickers):
            change = enhanced_weights[i] - current_weights[i]
            if abs(change) > 0.01:  # More than 1% change
                if change > 0:
                    action = "increase"
                    amount = change * investment_amount if investment_amount else 0
                    recommendations.append({
                        'ticker': ticker,
                        'action': action,
                        'percentage_change': round(change * 100, 2),
                        'dollar_amount': round(amount, 2),
                        'reason': f"Improves portfolio efficiency"
                    })
                else:
                    action = "decrease"
                    amount = abs(change) * investment_amount if investment_amount else 0
                    recommendations.append({
                        'ticker': ticker,
                        'action': action,
                        'percentage_change': round(change * 100, 2),
                        'dollar_amount': round(amount, 2),
                        'reason': f"Reduces portfolio risk"
                    })
        
        return recommendations
    
    def _calculate_rebalancing_trades(self, tickers, current_weights, target_weights):
        """Calculate specific trades needed for rebalancing."""
        trades = []
        
        for i, ticker in enumerate(tickers):
            current = current_weights[i]
            target = target_weights[i]
            diff = target - current
            
            if abs(diff) > 0.001:  # More than 0.1% change
                trades.append({
                    'ticker': ticker,
                    'current_weight': round(current * 100, 2),
                    'target_weight': round(target * 100, 2),
                    'change_percentage': round(diff * 100, 2),
                    'action': 'BUY' if diff > 0 else 'SELL'
                })
        
        return sorted(trades, key=lambda x: abs(x['change_percentage']), reverse=True)