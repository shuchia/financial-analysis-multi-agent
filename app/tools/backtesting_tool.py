import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class BacktestingTool(BaseTool):
    name: str = "backtesting"
    description: str = """
    Backtests trading strategies using historical data.
    Evaluates strategy performance with various metrics.
    """

    def _run(self, ticker: str, strategy_type: str = "moving_average",
             initial_capital: float = 10000, **strategy_params) -> Dict:
        """Backtest a trading strategy."""

        # Download data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 3)  # 3 years

        data = yf.download(ticker, start=start_date, end=end_date)

        # Initialize backtest variables
        position = 0
        cash = initial_capital
        portfolio_value = []
        trades = []

        if strategy_type == "moving_average":
            # Moving Average Crossover Strategy
            short_window = strategy_params.get('short_window', 50)
            long_window = strategy_params.get('long_window', 200)

            data['SMA_short'] = data['Close'].rolling(window=short_window).mean()
            data['SMA_long'] = data['Close'].rolling(window=long_window).mean()
            data['Signal'] = 0
            data.loc[data['SMA_short'] > data['SMA_long'], 'Signal'] = 1
            data.loc[data['SMA_short'] <= data['SMA_long'], 'Signal'] = -1
            data['Position'] = data['Signal'].diff()

        elif strategy_type == "rsi":
            # RSI Strategy
            rsi_period = strategy_params.get('rsi_period', 14)
            oversold = strategy_params.get('oversold', 30)
            overbought = strategy_params.get('overbought', 70)

            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))

            data['Signal'] = 0
            data.loc[data['RSI'] < oversold, 'Signal'] = 1
            data.loc[data['RSI'] > overbought, 'Signal'] = -1
            data['Position'] = data['Signal'].diff()

        # Simulate trading
        shares = 0
        for index, row in data.iterrows():
            if not pd.isna(row.get('Position', 0)):
                if row['Position'] == 2:  # Buy signal
                    if cash > row['Close']:
                        shares_to_buy = int(cash / row['Close'])
                        shares += shares_to_buy
                        cash -= shares_to_buy * row['Close']
                        trades.append({
                            'date': index,
                            'type': 'BUY',
                            'price': row['Close'],
                            'shares': shares_to_buy
                        })
                elif row['Position'] == -2:  # Sell signal
                    if shares > 0:
                        cash += shares * row['Close']
                        trades.append({
                            'date': index,
                            'type': 'SELL',
                            'price': row['Close'],
                            'shares': shares
                        })
                        shares = 0

            # Calculate portfolio value
            portfolio_value.append(cash + shares * row['Close'])

        # Calculate metrics
        portfolio_df = pd.DataFrame(portfolio_value, index=data.index, columns=['Value'])
        total_return = (portfolio_df['Value'].iloc[-1] - initial_capital) / initial_capital

        # Calculate daily returns
        portfolio_df['Returns'] = portfolio_df['Value'].pct_change()

        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = portfolio_df['Returns'].mean() / portfolio_df['Returns'].std() * np.sqrt(252)

        # Maximum drawdown
        portfolio_df['Cumulative'] = (1 + portfolio_df['Returns']).cumprod()
        portfolio_df['Running_Max'] = portfolio_df['Cumulative'].cummax()
        portfolio_df['Drawdown'] = (portfolio_df['Cumulative'] - portfolio_df['Running_Max']) / portfolio_df[
            'Running_Max']
        max_drawdown = portfolio_df['Drawdown'].min()

        # Buy and hold comparison
        buy_hold_return = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0]

        return {
            'strategy': {
                'type': strategy_type,
                'parameters': strategy_params
            },
            'performance': {
                'total_return': round(total_return * 100, 2),
                'final_value': round(portfolio_df['Value'].iloc[-1], 2),
                'sharpe_ratio': round(sharpe_ratio, 4),
                'max_drawdown': round(max_drawdown * 100, 2),
                'number_of_trades': len(trades),
                'buy_hold_return': round(buy_hold_return * 100, 2),
                'alpha': round((total_return - buy_hold_return) * 100, 2)
            },
            'trades': trades[-10:],  # Last 10 trades
            'current_position': {
                'shares': shares,
                'value': round(shares * data['Close'].iloc[-1], 2),
                'cash': round(cash, 2)
            }
        }