import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class MonteCarloSimulationTool(BaseTool):
    name: str = "monte_carlo_simulation"
    description: str = """
    Performs Monte Carlo simulation for portfolio risk modeling.
    Simulates thousands of possible price paths to estimate risk metrics.
    """

    def _run(self, ticker: str, investment_amount: float = 10000,
             days: int = 252, simulations: int = 1000) -> Dict:
        """Run Monte Carlo simulation for risk analysis."""

        # Download historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 2)  # 2 years of data

        # Download with robust MultiIndex handling
        raw_data = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if raw_data.empty:
            return {'error': f'No data found for ticker {ticker}'}

        # Handle different column structures
        if 'Adj Close' in raw_data.columns:
            stock = raw_data['Adj Close']
        elif 'Close' in raw_data.columns:
            stock = raw_data['Close']
        else:
            # Sometimes yfinance returns data without column names for single tickers
            stock = raw_data.iloc[:, -1] if len(raw_data.columns) > 0 else raw_data

        returns = stock.pct_change().dropna()

        # Calculate parameters
        mean_return = returns.mean()
        std_dev = returns.std()

        # Setup simulation
        last_price = stock.iloc[-1]
        simulation_df = pd.DataFrame()

        # Run simulations
        for sim in range(simulations):
            prices = []
            price = last_price

            for day in range(days):
                # Generate random return using normal distribution
                daily_return = np.random.normal(mean_return, std_dev)
                price = price * (1 + daily_return)
                prices.append(price)

            simulation_df[sim] = prices

        # Calculate statistics
        final_prices = simulation_df.iloc[-1]
        investment_values = (final_prices / last_price) * investment_amount

        # Calculate VaR and CVaR
        confidence_levels = [0.95, 0.99]
        var_cvar_results = {}

        for confidence in confidence_levels:
            var_threshold = np.percentile(investment_values, (1 - confidence) * 100)
            cvar = investment_values[investment_values <= var_threshold].mean()

            var_cvar_results[f'{int(confidence * 100)}%'] = {
                'VaR': round(investment_amount - var_threshold, 2),
                'CVaR': round(investment_amount - cvar, 2) if not np.isnan(cvar) else 0,
                'threshold_value': round(var_threshold, 2)
            }

        # Probability calculations
        prob_profit = (investment_values > investment_amount).mean()
        prob_loss_10 = (investment_values < investment_amount * 0.9).mean()
        prob_gain_20 = (investment_values > investment_amount * 1.2).mean()

        return {
            'simulation_parameters': {
                'ticker': ticker,
                'initial_investment': investment_amount,
                'trading_days': days,
                'simulations_run': simulations,
                'historical_mean_return': round(mean_return * 252, 4),  # Annualized
                'historical_volatility': round(std_dev * np.sqrt(252), 4)  # Annualized
            },
            'results': {
                'expected_value': round(investment_values.mean(), 2),
                'median_value': round(investment_values.median(), 2),
                'std_deviation': round(investment_values.std(), 2),
                'min_value': round(investment_values.min(), 2),
                'max_value': round(investment_values.max(), 2),
                'percentile_25': round(np.percentile(investment_values, 25), 2),
                'percentile_75': round(np.percentile(investment_values, 75), 2)
            },
            'risk_metrics': var_cvar_results,
            'probabilities': {
                'profit': round(prob_profit, 4),
                'loss_over_10%': round(prob_loss_10, 4),
                'gain_over_20%': round(prob_gain_20, 4)
            },
            'price_paths_sample': simulation_df.iloc[:, :5].to_dict()  # First 5 simulations
        }