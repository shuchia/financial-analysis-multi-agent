import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from langchain.tools import BaseTool
from statsmodels.tsa.stattools import coint
import warnings

warnings.filterwarnings('ignore')


class PairsTradingTool(BaseTool):
    name: str = "pairs_trading"
    description: str = """
    Identifies pairs trading opportunities using cointegration analysis.
    Finds stocks that move together for statistical arbitrage.
    """

    def _run(self, sector_tickers: List[str], test_ticker: Optional[str] = None) -> Dict:
        """Find pairs trading opportunities."""

        # Download data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        # Download with robust MultiIndex handling
        raw_data = yf.download(sector_tickers, start=start_date, end=end_date, progress=False)

        if raw_data.empty:
            return {'error': 'No data found for the provided tickers'}

        # Check if 'Adj Close' exists in multi-level columns
        if isinstance(raw_data.columns, pd.MultiIndex):
            if 'Adj Close' in raw_data.columns.levels[0]:
                data = raw_data['Adj Close']
            elif 'Close' in raw_data.columns.levels[0]:
                data = raw_data['Close']
            else:
                # Use the first price column available
                data = raw_data.iloc[:, :len(sector_tickers)]
        else:
            data = raw_data

        # Drop any rows with NaN values
        data = data.dropna()

        # If single ticker provided, find best pairs
        if test_ticker and test_ticker in sector_tickers:
            pairs = []
            for ticker in sector_tickers:
                if ticker != test_ticker:
                    # Test for cointegration
                    score, pvalue, _ = coint(data[test_ticker], data[ticker])

                    if pvalue < 0.05:  # Statistically significant
                        # Calculate spread
                        spread = data[test_ticker] - data[ticker]
                        spread_mean = spread.mean()
                        spread_std = spread.std()
                        current_spread = spread.iloc[-1]
                        z_score = (current_spread - spread_mean) / spread_std

                        pairs.append({
                            'pair': f"{test_ticker}-{ticker}",
                            'pvalue': round(pvalue, 4),
                            'correlation': round(data[test_ticker].corr(data[ticker]), 4),
                            'spread_mean': round(spread_mean, 2),
                            'spread_std': round(spread_std, 2),
                            'current_spread': round(current_spread, 2),
                            'z_score': round(z_score, 2),
                            'signal': 'BUY' if z_score < -2 else 'SELL' if z_score > 2 else 'HOLD'
                        })

            pairs.sort(key=lambda x: x['pvalue'])

        else:
            # Find all cointegrated pairs
            pairs = []
            n = len(sector_tickers)
            for i in range(n):
                for j in range(i + 1, n):
                    ticker1 = sector_tickers[i]
                    ticker2 = sector_tickers[j]

                    # Test for cointegration
                    score, pvalue, _ = coint(data[ticker1], data[ticker2])

                    if pvalue < 0.05:
                        # Calculate spread statistics
                        spread = data[ticker1] - data[ticker2]
                        spread_mean = spread.mean()
                        spread_std = spread.std()
                        current_spread = spread.iloc[-1]
                        z_score = (current_spread - spread_mean) / spread_std

                        pairs.append({
                            'pair': f"{ticker1}-{ticker2}",
                            'pvalue': round(pvalue, 4),
                            'correlation': round(data[ticker1].corr(data[ticker2]), 4),
                            'spread_mean': round(spread_mean, 2),
                            'spread_std': round(spread_std, 2),
                            'current_spread': round(current_spread, 2),
                            'z_score': round(z_score, 2),
                            'signal': 'BUY_FIRST' if z_score < -2 else 'BUY_SECOND' if z_score > 2 else 'HOLD'
                        })

            pairs.sort(key=lambda x: abs(x['z_score']), reverse=True)

        return {
            'cointegrated_pairs': pairs[:10],  # Top 10 pairs
            'total_pairs_tested': len(sector_tickers) * (len(sector_tickers) - 1) // 2,
            'significant_pairs_found': len(pairs),
            'trading_signals': [p for p in pairs if p['signal'] != 'HOLD'][:5]
        }