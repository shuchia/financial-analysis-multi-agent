import yfinance as yf
import pandas as pd
import numpy as np
from crewai.tools import tool
import pandas_ta_classic as ta
from scipy.signal import find_peaks
import logging

@tool
def yf_tech_analysis(ticker: str, period: str = "1y"):
    """
    Perform advanced technical analysis on a given stock ticker.
    
    Args:
        ticker (str): The stock ticker symbol.
        period (str): The time period for analysis (e.g., "1y" for 1 year).
    
    Returns:
        dict: Advanced technical analysis results.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Starting technical analysis for {ticker} ({period})")
    
    try:
        # Fix common period format issues
        if period == "6m":
            period = "6mo"
        
        logger.debug(f"Fetching stock data from yfinance for {ticker}")
        stock = yf.Ticker(ticker)
        history = stock.history(period=period)
        logger.debug(f"Retrieved {len(history)} data points")

        # Start with your history DataFrame
        df = history.copy()

        # Clean the data
        df = df.dropna()
        logger.debug(f"Data cleaned, {len(df)} rows remaining")

        # Add technical indicators with explicit column mapping
        logger.debug("Calculating technical indicators...")
        
        # Calculate specific indicators to avoid conflicts
        df['trend_sma_50'] = ta.sma(df['Close'], length=50)
        df['trend_sma_200'] = ta.sma(df['Close'], length=200)
        df['momentum_rsi'] = ta.rsi(df['Close'], length=14)
        
        # Calculate MACD
        macd_result = ta.macd(df['Close'])
        if isinstance(macd_result, pd.DataFrame):
            df['trend_macd_diff'] = macd_result.iloc[:, 0]  # MACD line
        else:
            df['trend_macd_diff'] = macd_result
        
        # Calculate Bollinger Bands
        bb_result = ta.bbands(df['Close'], length=20)
        if isinstance(bb_result, pd.DataFrame):
            df['volatility_bbhi'] = bb_result.iloc[:, 0]  # Upper band
            df['volatility_bbli'] = bb_result.iloc[:, 2]  # Lower band
        else:
            # Fallback calculation
            sma20 = ta.sma(df['Close'], length=20)
            std20 = df['Close'].rolling(20).std()
            df['volatility_bbhi'] = sma20 + (std20 * 2)
            df['volatility_bbli'] = sma20 - (std20 * 2)
        
        # Calculate ATR
        df['volatility_atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        logger.debug("Technical indicators calculated successfully")
        
        # Calculate additional custom indicators
        logger.debug("Computing custom indicators (volatility, momentum)...")
        df['volatility'] = df['Close'].pct_change().rolling(window=20).std() * np.sqrt(252)
        df['momentum'] = df['Close'] - df['Close'].shift(20)
        
        # Identify potential support and resistance levels
        logger.debug("Identifying support and resistance levels...")
        close_prices = df['Close'].values
        peaks, _ = find_peaks(close_prices, distance=20)
        troughs, _ = find_peaks(-close_prices, distance=20)
        support_levels = close_prices[troughs][-3:]
        resistance_levels = close_prices[peaks][-3:]
        logger.debug(f"Found {len(peaks)} peaks and {len(troughs)} troughs")
        
        # Identify chart patterns
        logger.debug("Analyzing chart patterns...")
        patterns = identify_chart_patterns(df)
        logger.debug(f"Identified patterns: {patterns}")
    
        result = {
            "ticker": ticker,
            "current_price": df['Close'].iloc[-1],
            "sma_50": df['trend_sma_50'].iloc[-1],
            "sma_200": df['trend_sma_200'].iloc[-1],
            "rsi": df['momentum_rsi'].iloc[-1],
            "macd": df['trend_macd_diff'].iloc[-1],
            "bollinger_hband": df['volatility_bbhi'].iloc[-1],
            "bollinger_lband": df['volatility_bbli'].iloc[-1],
            "atr": df['volatility_atr'].iloc[-1],
            "volatility": df['volatility'].iloc[-1],
            "momentum": df['momentum'].iloc[-1],
            "support_levels": support_levels.tolist(),
            "resistance_levels": resistance_levels.tolist(),
            "identified_patterns": patterns
        }
        
        logger.info(f"✅ Technical analysis completed for {ticker}")
        logger.debug(f"Analysis result: RSI={result['rsi']:.2f}, Current Price=${result['current_price']:.2f}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Technical analysis failed for {ticker}: {str(e)}")
        raise

def identify_chart_patterns(df):
    patterns = []
    close = df['Close'].values
    
    # Head and Shoulders pattern
    if is_head_and_shoulders(close):
        patterns.append("Head and Shoulders")
    
    # Double Top pattern
    if is_double_top(close):
        patterns.append("Double Top")
    
    # Double Bottom pattern
    if is_double_bottom(close):
        patterns.append("Double Bottom")
    
    return patterns

def is_head_and_shoulders(close):
    # Simplified head and shoulders detection
    peaks, _ = find_peaks(close, distance=20)
    if len(peaks) >= 3:
        left_shoulder, head, right_shoulder = peaks[-3], peaks[-2], peaks[-1]
        if close[head] > close[left_shoulder] and close[head] > close[right_shoulder]:
            return True
    return False

def is_double_top(close):
    # Simplified double top detection
    peaks, _ = find_peaks(close, distance=20)
    if len(peaks) >= 2:
        if abs(close[peaks[-1]] - close[peaks[-2]]) / close[peaks[-2]] < 0.03:
            return True
    return False

def is_double_bottom(close):
    # Simplified double bottom detection
    troughs, _ = find_peaks(-close, distance=20)
    if len(troughs) >= 2:
        if abs(close[troughs[-1]] - close[troughs[-2]]) / close[troughs[-2]] < 0.03:
            return True
    return False
