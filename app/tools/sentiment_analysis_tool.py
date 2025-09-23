import yfinance as yf
from crewai.tools import tool
from textblob import TextBlob
import requests
from bs4 import BeautifulSoup
import logging

@tool
def sentiment_analysis(ticker: str):
    """
    Perform sentiment analysis on recent news articles about the given stock.
    
    Args:
        ticker (str): The stock ticker symbol.
    
    Returns:
        dict: Sentiment analysis results.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"📰 Starting sentiment analysis for {ticker}")
    
    try:
        # Fetch recent news articles
        logger.debug(f"Fetching news articles for {ticker}")
        stock = yf.Ticker(ticker)
        news = stock.news
        logger.debug(f"Retrieved {len(news)} news articles")
        
        sentiments = []
        for i, article in enumerate(news[:5]):  # Analyze the 5 most recent articles
            title = article['content']['title']
            blob = TextBlob(title)
            sentiment = blob.sentiment.polarity
            sentiments.append(sentiment)
            logger.debug(f"Article {i+1}: '{title[:50]}...' - Sentiment: {sentiment:.3f}")
        
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        logger.debug(f"Average news sentiment: {avg_sentiment:.3f}")
        
        # Fetch social media sentiment (simulated)
        logger.debug("Computing social media sentiment...")
        social_sentiment = simulate_social_sentiment(ticker)
        logger.debug(f"Social media sentiment: {social_sentiment:.3f}")
        
        overall_sentiment = (avg_sentiment + social_sentiment) / 2
        
        result = {
            "ticker": ticker,
            "news_sentiment": avg_sentiment,
            "social_sentiment": social_sentiment,
            "overall_sentiment": overall_sentiment
        }
        
        logger.info(f"✅ Sentiment analysis completed for {ticker} - Overall: {overall_sentiment:.3f}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Sentiment analysis failed for {ticker}: {str(e)}")
        raise

def simulate_social_sentiment(ticker):
    # This is a placeholder for actual social media sentiment analysis
    # In a real-world scenario, you would use APIs from Twitter, StockTwits, etc.
    import random
    return random.uniform(-1, 1)
