import yfinance as yf
import numpy as np
from scipy import stats
from scipy.stats import norm
from crewai.tools import tool
import logging
import pandas as pd

@tool
def risk_assessment(ticker: str = None, portfolio: dict = None, benchmark: str = "^GSPC", period: str = "5y"):
    """
    Perform risk assessment for a given stock or portfolio.
    
    Args:
        ticker (str): The stock ticker symbol (for single stock analysis).
        portfolio (dict): Portfolio data with tickers, weights, and user_profile.
        benchmark (str): Benchmark index for comparison (default: S&P 500).
        period (str): Time period for analysis.
    
    Returns:
        dict: Risk assessment results.
    """
    logger = logging.getLogger(__name__)
    
    # Handle portfolio vs single stock analysis
    if portfolio:
        logger.info(f"⚠️ Starting portfolio risk assessment vs {benchmark} ({period})")
        return _portfolio_risk_assessment(portfolio, benchmark, period)
    elif ticker:
        logger.info(f"⚠️ Starting risk assessment for {ticker} vs {benchmark} ({period})")
        return _single_stock_risk_assessment(ticker, benchmark, period)
    else:
        raise ValueError("Either ticker or portfolio must be provided")


def _single_stock_risk_assessment(ticker: str, benchmark: str, period: str):
    """Original single stock risk assessment logic."""
    logger = logging.getLogger(__name__)
    
    try:
        # Fix common period format issues
        if period == "6m":
            period = "6mo"
            
        logger.debug(f"Fetching stock data for {ticker} and benchmark {benchmark}")
        stock = yf.Ticker(ticker)
        benchmark_index = yf.Ticker(benchmark)
        
        stock_data = stock.history(period=period)['Close']
        benchmark_data = benchmark_index.history(period=period)['Close']
        logger.debug(f"Retrieved {len(stock_data)} stock data points and {len(benchmark_data)} benchmark points")
        
        # Calculate returns
        logger.debug("Calculating returns...")
        stock_returns = stock_data.pct_change().dropna()
        benchmark_returns = benchmark_data.pct_change().dropna()
        
        # Calculate beta
        logger.debug("Computing beta coefficient...")
        covariance = np.cov(stock_returns, benchmark_returns)[0][1]
        benchmark_variance = np.var(benchmark_returns)
        beta = covariance / benchmark_variance
        
        # Calculate Sharpe ratio
        logger.debug("Computing Sharpe ratio...")
        risk_free_rate = 0.02  # Assume 2% risk-free rate
        excess_returns = stock_returns - risk_free_rate
        sharpe_ratio = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        
        # Calculate Value at Risk (VaR)
        logger.debug("Computing Value at Risk (95%)...")
        var_95 = np.percentile(stock_returns, 5)
        
        # Calculate Maximum Drawdown
        logger.debug("Computing maximum drawdown...")
        cumulative_returns = (1 + stock_returns).cumprod()
        max_drawdown = (cumulative_returns.cummax() - cumulative_returns).max()
        
        volatility = stock_returns.std() * np.sqrt(252)
        
        result = {
            "ticker": ticker,
            "beta": beta,
            "sharpe_ratio": sharpe_ratio,
            "value_at_risk_95": var_95,
            "max_drawdown": max_drawdown,
            "volatility": volatility
        }
        
        logger.info(f"✅ Risk assessment completed for {ticker}")
        logger.debug(f"Results: Beta={beta:.3f}, Sharpe={sharpe_ratio:.3f}, VaR={var_95:.3f}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Risk assessment failed for {ticker}: {str(e)}")
        raise


def _portfolio_risk_assessment(portfolio: dict, benchmark: str, period: str):
    """Perform risk assessment for entire portfolio."""
    logger = logging.getLogger(__name__)
    
    try:
        # Extract portfolio data
        tickers = portfolio.get('tickers', [])
        weights = portfolio.get('weights', [])
        user_profile = portfolio.get('user_profile', {})
        total_amount = portfolio.get('total_amount', 10000)
        
        if not tickers or not weights:
            raise ValueError("Portfolio must contain tickers and weights")
        
        # Fix period format
        if period == "6m":
            period = "6mo"
        
        # Download data for all tickers
        logger.debug(f"Fetching data for portfolio tickers: {tickers}")
        stock_data = {}
        for ticker in tickers:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)['Close']
            if not hist.empty:
                stock_data[ticker] = hist
        
        # Get benchmark data
        benchmark_index = yf.Ticker(benchmark)
        benchmark_data = benchmark_index.history(period=period)['Close']
        
        # Calculate individual returns
        returns_data = {}
        for ticker, data in stock_data.items():
            returns_data[ticker] = data.pct_change().dropna()
        
        benchmark_returns = benchmark_data.pct_change().dropna()
        
        # Calculate portfolio returns (weighted average)
        aligned_returns = []
        for i, ticker in enumerate(tickers):
            if ticker in returns_data:
                ticker_returns = returns_data[ticker]
                weighted_returns = ticker_returns * weights[i]
                aligned_returns.append(weighted_returns)
        
        # Sum weighted returns
        portfolio_returns = np.zeros(len(aligned_returns[0]))
        for returns in aligned_returns:
            portfolio_returns = portfolio_returns + returns.values
        
        # Portfolio metrics
        portfolio_beta = np.cov(portfolio_returns, benchmark_returns.values)[0][1] / np.var(benchmark_returns)
        
        # Sharpe ratio
        risk_free_rate = 0.02
        excess_returns = portfolio_returns - risk_free_rate / 252
        portfolio_sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        
        # Value at Risk
        portfolio_var_95 = np.percentile(portfolio_returns, 5)
        portfolio_var_99 = np.percentile(portfolio_returns, 1)
        
        # Maximum Drawdown
        cumulative_returns = (1 + portfolio_returns).cumprod()
        portfolio_max_drawdown = ((cumulative_returns.cummax() - cumulative_returns) / cumulative_returns.cummax()).max()
        
        # Annual volatility
        portfolio_volatility = portfolio_returns.std() * np.sqrt(252)
        
        # Individual stock contributions to risk
        risk_contributions = {}
        for i, ticker in enumerate(tickers):
            if ticker in returns_data:
                # Calculate marginal contribution to portfolio volatility
                ticker_vol = returns_data[ticker].std() * np.sqrt(252)
                risk_contributions[ticker] = {
                    'weight': weights[i],
                    'volatility': ticker_vol,
                    'weighted_vol': ticker_vol * weights[i],
                    'percentage_of_risk': round((ticker_vol * weights[i]) / portfolio_volatility * 100, 2)
                }
        
        # Risk alignment with user profile
        user_risk = user_profile.get('risk_profile', 'moderate')
        risk_score = user_profile.get('risk_score', 0.5)
        
        # Expected volatility ranges by profile
        risk_ranges = {
            'conservative': (0.08, 0.12),
            'moderate': (0.12, 0.18),
            'aggressive': (0.18, 0.25)
        }
        
        expected_range = risk_ranges.get(user_risk, (0.12, 0.18))
        risk_alignment = "aligned"
        
        if portfolio_volatility < expected_range[0]:
            risk_alignment = "too_conservative"
            adjustment_needed = f"Consider increasing equity allocation by {(expected_range[0] - portfolio_volatility) * 100:.1f}%"
        elif portfolio_volatility > expected_range[1]:
            risk_alignment = "too_aggressive"
            adjustment_needed = f"Consider reducing equity allocation by {(portfolio_volatility - expected_range[1]) * 100:.1f}%"
        else:
            adjustment_needed = None
        
        result = {
            "portfolio_metrics": {
                "beta": round(portfolio_beta, 3),
                "sharpe_ratio": round(portfolio_sharpe, 3),
                "value_at_risk_95": round(portfolio_var_95 * 100, 2),
                "value_at_risk_99": round(portfolio_var_99 * 100, 2),
                "max_drawdown": round(portfolio_max_drawdown * 100, 2),
                "annual_volatility": round(portfolio_volatility * 100, 2),
                "expected_annual_return": round(portfolio_returns.mean() * 252 * 100, 2)
            },
            "risk_contributions": risk_contributions,
            "risk_alignment": {
                "user_profile": user_risk,
                "risk_score": risk_score,
                "portfolio_risk_level": risk_alignment,
                "expected_volatility_range": f"{expected_range[0]*100:.0f}%-{expected_range[1]*100:.0f}%",
                "actual_volatility": f"{portfolio_volatility*100:.1f}%",
                "adjustment_recommendation": adjustment_needed
            },
            "diversification_metrics": {
                "number_of_positions": len(tickers),
                "effective_number_of_stocks": 1 / sum([w**2 for w in weights]),  # Herfindahl index
                "concentration_risk": "high" if max(weights) > 0.4 else "moderate" if max(weights) > 0.25 else "low"
            },
            "value_at_risk_interpretation": {
                "95%": f"5% chance of losing more than ${abs(portfolio_var_95) * total_amount:.2f} in a day",
                "99%": f"1% chance of losing more than ${abs(portfolio_var_99) * total_amount:.2f} in a day"
            }
        }
        
        logger.info(f"✅ Portfolio risk assessment completed")
        logger.debug(f"Portfolio Beta={portfolio_beta:.3f}, Sharpe={portfolio_sharpe:.3f}, Vol={portfolio_volatility:.3f}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Portfolio risk assessment failed: {str(e)}")
        raise
