import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
from datetime import datetime, timedelta
from typing import List, Dict
from crewai.tools import tool


def _var_calculator_impl(tickers_string: str, portfolio_value: float = 100000,
                         holding_period: int = 10, confidence_levels_string: str = "0.90,0.95,0.99") -> Dict:
    """
    Internal implementation of VaR calculator (non-decorated version for direct calls).

    Calculates Value at Risk (VaR) and Conditional VaR (CVaR) using multiple methods.

    Args:
        tickers_string (str): Comma-separated list of stock tickers
        portfolio_value (float): Total portfolio value
        holding_period (int): Holding period in days
        confidence_levels_string (str): Comma-separated confidence levels (e.g., "0.90,0.95,0.99")

    Returns:
        dict: VaR and CVaR results using historical, parametric, and Monte Carlo methods
    """

    try:
        # Parse input strings
        tickers = [t.strip().upper() for t in tickers_string.split(',')]

        confidence_levels = None
        if confidence_levels_string:
            confidence_levels = [float(c.strip()) for c in confidence_levels_string.split(',')]

        if confidence_levels is None:
            confidence_levels = [0.90, 0.95, 0.99]

        # Download historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 2)  # 2 years

        # Equal weights for simplicity (can be modified)
        weights = np.array([1 / len(tickers)] * len(tickers))

        # Get price data with better error handling
        print(f"Fetching data for: {tickers}")

        if len(tickers) == 1:
            # Single ticker - handle differently
            ticker = tickers[0]
            try:
                data = yf.download(ticker, start=start_date, end=end_date, progress=False)

                if data.empty:
                    return {
                        'error': f'No data found for ticker {ticker}',
                        'suggestion': 'Please verify the ticker symbol is correct and try again.'
                    }

                # Handle different column structures
                if 'Adj Close' in data.columns:
                    prices = data['Adj Close']
                elif 'Close' in data.columns:
                    prices = data['Close']
                else:
                    # Sometimes yfinance returns data without column names for single tickers
                    prices = data.iloc[:, -1] if len(data.columns) > 0 else data

                # Create DataFrame with ticker as column name
                data = pd.DataFrame({ticker: prices})

            except Exception as e:
                return {
                    'error': f'Failed to fetch data for {ticker}: {str(e)}',
                    'suggestion': 'Please check if the ticker symbol is valid.'
                }
        else:
            # Multiple tickers
            try:
                download_result = yf.download(tickers, start=start_date, end=end_date, progress=False)

                if download_result.empty:
                    return {
                        'error': 'No data found for the provided tickers',
                        'suggestion': 'Please verify the ticker symbols are correct.'
                    }

                # Check if 'Adj Close' exists in multi-level columns
                if isinstance(download_result.columns, pd.MultiIndex):
                    if 'Adj Close' in download_result.columns.levels[0]:
                        data = download_result['Adj Close']
                    elif 'Close' in download_result.columns.levels[0]:
                        data = download_result['Close']
                    else:
                        # Use the first price column available
                        data = download_result.iloc[:, :len(tickers)]
                else:
                    data = download_result

                # Ensure we have all tickers
                missing_tickers = [t for t in tickers if t not in data.columns]
                if missing_tickers:
                    print(f"Warning: Missing data for tickers: {missing_tickers}")

            except Exception as e:
                return {
                    'error': f'Failed to fetch data: {str(e)}',
                    'suggestion': 'Please verify all ticker symbols are correct.'
                }

        # Drop any rows with NaN values
        data = data.dropna()

        if len(data) < 30:  # Minimum data points for reliable calculation
            return {
                'error': 'Insufficient historical data',
                'suggestion': 'Need at least 30 days of price history for reliable VaR calculation.'
            }

        # Calculate returns
        returns = data.pct_change().dropna()

        # Portfolio returns
        if len(tickers) == 1:
            portfolio_returns = returns.iloc[:, 0]
        else:
            # Adjust weights if some tickers are missing
            available_tickers = data.columns.tolist()
            if len(available_tickers) < len(tickers):
                weights = np.array([1 / len(available_tickers)] * len(available_tickers))
            portfolio_returns = returns.dot(weights[:len(available_tickers)])

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

        # Get actual tickers used (in case some were missing)
        actual_tickers = data.columns.tolist() if len(tickers) > 1 else tickers
        actual_weights = weights[:len(actual_tickers)]

        # Calculate individual stock volatilities and risk contributions
        individual_volatilities = {}
        risk_contributions = {}

        for i, ticker in enumerate(actual_tickers):
            # Get individual stock returns
            if len(tickers) == 1:
                stock_returns = returns.iloc[:, 0]
            else:
                stock_returns = returns[ticker]

            # Calculate annual volatility for this stock
            stock_volatility = stock_returns.std() * np.sqrt(252)
            individual_volatilities[ticker] = stock_volatility

            # Calculate risk contribution (weight * volatility / portfolio volatility)
            if annual_volatility > 0:
                risk_contribution_pct = (actual_weights[i] * stock_volatility) / annual_volatility * 100
            else:
                risk_contribution_pct = 0

            risk_contributions[ticker] = {
                'weight': float(actual_weights[i]),
                'volatility': float(stock_volatility),
                'percentage_of_risk': float(risk_contribution_pct)
            }

        return {
            'portfolio_composition': {
                'tickers': actual_tickers,
                'weights': dict(zip(actual_tickers, actual_weights.round(4))),
                'portfolio_value': portfolio_value,
                'holding_period_days': holding_period
            },
            'var_historical': {k: round(v, 2) for k, v in historical_var.items()},
            'cvar_historical': {k: round(v, 2) for k, v in historical_cvar.items()},
            'var_parametric': {k: round(v, 2) for k, v in parametric_var.items()},
            'cvar_parametric': {k: round(v, 2) for k, v in parametric_cvar.items()},
            'var_monte_carlo': {k: round(v, 2) for k, v in mc_var.items()},
            'cvar_monte_carlo': {k: round(v, 2) for k, v in mc_cvar.items()},
            'risk_contributions': risk_contributions,
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
                'cvar_interpretation': f"If losses exceed VaR, average loss would be ${historical_cvar['95%']:,.2f}",
                'risk_level': _interpret_risk_level(annual_volatility, sharpe_ratio, max_drawdown)
            },
            'data_quality': {
                'data_points': len(returns),
                'start_date': returns.index[0].strftime('%Y-%m-%d'),
                'end_date': returns.index[-1].strftime('%Y-%m-%d')
            }
        }

    except Exception as e:
        return {
            'error': f'Calculation failed: {str(e)}',
            'suggestion': 'Please verify your inputs and try again. Common issues include invalid ticker symbols or network connectivity problems.',
            'debug_info': {
                'tickers': tickers_string,
                'portfolio_value': portfolio_value,
                'holding_period': holding_period
            }
        }


@tool
def var_calculator(tickers_string: str, portfolio_value: float = 100000,
                   holding_period: int = 10, confidence_levels_string: str = "0.90,0.95,0.99") -> Dict:
    """
    Calculates Value at Risk (VaR) and Conditional VaR (CVaR) using multiple methods.

    Args:
        tickers_string (str): Comma-separated list of stock tickers
        portfolio_value (float): Total portfolio value
        holding_period (int): Holding period in days
        confidence_levels_string (str): Comma-separated confidence levels (e.g., "0.90,0.95,0.99")

    Returns:
        dict: VaR and CVaR results using historical, parametric, and Monte Carlo methods
    """
    return _var_calculator_impl(tickers_string, portfolio_value, holding_period, confidence_levels_string)


def _interpret_risk_level(volatility: float, sharpe: float, max_dd: float) -> str:
    """Helper function to interpret risk level"""
    risk_score = 0

    # Volatility contribution
    if volatility > 0.40:
        risk_score += 3
    elif volatility > 0.25:
        risk_score += 2
    elif volatility > 0.15:
        risk_score += 1

    # Sharpe ratio contribution (inverse)
    if sharpe < 0.5:
        risk_score += 2
    elif sharpe < 1.0:
        risk_score += 1

    # Max drawdown contribution
    if max_dd > 0.30:
        risk_score += 3
    elif max_dd > 0.20:
        risk_score += 2
    elif max_dd > 0.10:
        risk_score += 1

    # Interpret total risk score
    if risk_score >= 6:
        return "High Risk - Consider diversification or risk reduction"
    elif risk_score >= 3:
        return "Moderate Risk - Acceptable for growth-oriented investors"
    else:
        return "Low Risk - Conservative portfolio suitable for risk-averse investors"


# Legacy class wrapper for backward compatibility
class VaRCalculatorTool:
    """Legacy wrapper for the VaR calculator tool."""

    def __init__(self):
        self.name = "var_calculator"
        self.description = "Calculates Value at Risk (VaR) and Conditional VaR (CVaR)"

    def _run(self, *args, **kwargs):
        # Convert to string format expected by the @tool function
        if 'tickers' in kwargs and isinstance(kwargs['tickers'], list):
            kwargs['tickers_string'] = ','.join(kwargs['tickers'])
            del kwargs['tickers']
        if 'confidence_levels' in kwargs and isinstance(kwargs['confidence_levels'], list):
            kwargs['confidence_levels_string'] = ','.join(map(str, kwargs['confidence_levels']))
            del kwargs['confidence_levels']
        return var_calculator(*args, **kwargs)


# Test function for debugging
def test_var_calculator():
    """Test function to verify the calculator works with various inputs"""

    print("Testing VaR Calculator...")
    print("-" * 50)

    # Test 1: Single ticker (QGRO - the problematic one)
    print("\nTest 1: Single ETF (QGRO)")
    result1 = var_calculator("QGRO", 25.0, 10, "0.95,0.99")
    if 'error' in result1:
        print(f"Error: {result1['error']}")
    else:
        print(f"95% VaR: ${result1['var_historical']['95%']:,.2f}")
        print(f"99% VaR: ${result1['var_historical']['99%']:,.2f}")

    # Test 2: Popular stock
    print("\nTest 2: Single Stock (AAPL)")
    result2 = var_calculator("AAPL", 10000.0, 10, "0.95")
    if 'error' in result2:
        print(f"Error: {result2['error']}")
    else:
        print(f"95% VaR: ${result2['var_historical']['95%']:,.2f}")
        print(f"Sharpe Ratio: {result2['portfolio_metrics']['sharpe_ratio']}")

    # Test 3: Multiple tickers
    print("\nTest 3: Portfolio (AAPL,MSFT,GOOGL)")
    result3 = var_calculator("AAPL,MSFT,GOOGL", 50000.0, 5, "0.90,0.95,0.99")
    if 'error' in result3:
        print(f"Error: {result3['error']}")
    else:
        print(f"Portfolio composition: {result3['portfolio_composition']['tickers']}")
        print(f"95% VaR: ${result3['var_historical']['95%']:,.2f}")
        print(f"Annual Volatility: {result3['portfolio_metrics']['annual_volatility']}%")

    print("\n" + "-" * 50)
    print("Testing complete!")


if __name__ == "__main__":
    # Run tests if script is executed directly
    test_var_calculator()