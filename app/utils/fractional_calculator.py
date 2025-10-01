"""
Fractional share calculation utilities and helpers.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta

# List of stocks commonly available for fractional trading
FRACTIONAL_ELIGIBLE_STOCKS = {
    # Large Cap Tech
    'AAPL': 'Apple Inc.',
    'MSFT': 'Microsoft Corporation', 
    'GOOGL': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.',
    'META': 'Meta Platforms Inc.',
    'TSLA': 'Tesla Inc.',
    'NVDA': 'NVIDIA Corporation',
    'NFLX': 'Netflix Inc.',
    
    # Large Cap Financial
    'JPM': 'JPMorgan Chase & Co.',
    'BAC': 'Bank of America Corp.',
    'WFC': 'Wells Fargo & Company',
    'GS': 'Goldman Sachs Group Inc.',
    'V': 'Visa Inc.',
    'MA': 'Mastercard Inc.',
    
    # Large Cap Consumer
    'WMT': 'Walmart Inc.',
    'HD': 'Home Depot Inc.',
    'PG': 'Procter & Gamble Co.',
    'KO': 'Coca-Cola Company',
    'PEP': 'PepsiCo Inc.',
    'COST': 'Costco Wholesale Corp.',
    'NKE': 'Nike Inc.',
    'SBUX': 'Starbucks Corporation',
    
    # Large Cap Healthcare
    'JNJ': 'Johnson & Johnson',
    'UNH': 'UnitedHealth Group Inc.',
    'PFE': 'Pfizer Inc.',
    'ABBV': 'AbbVie Inc.',
    'LLY': 'Eli Lilly and Company',
    'MRK': 'Merck & Co. Inc.',
    
    # Large Cap Industrial/Energy
    'XOM': 'Exxon Mobil Corporation',
    'CVX': 'Chevron Corporation',
    'BA': 'Boeing Company',
    'CAT': 'Caterpillar Inc.',
    'GE': 'General Electric Company',
    
    # Popular ETFs
    'SPY': 'SPDR S&P 500 ETF',
    'QQQ': 'Invesco QQQ Trust',
    'VTI': 'Vanguard Total Stock Market ETF',
    'VTV': 'Vanguard Value ETF',
    'VUG': 'Vanguard Growth ETF',
    'VOO': 'Vanguard S&P 500 ETF'
}

# Broker information for fractional trading
BROKER_INFO = {
    'robinhood': {
        'name': 'Robinhood',
        'commission': 0.0,
        'min_investment': 1.0,
        'fractional_fee': 0.0,
        'supports_most_stocks': True
    },
    'fidelity': {
        'name': 'Fidelity',
        'commission': 0.0,
        'min_investment': 1.0,
        'fractional_fee': 0.0,
        'supports_most_stocks': True
    },
    'schwab': {
        'name': 'Charles Schwab',
        'commission': 0.0,
        'min_investment': 5.0,
        'fractional_fee': 0.0,
        'supports_most_stocks': True
    },
    'webull': {
        'name': 'Webull',
        'commission': 0.0,
        'min_investment': 5.0,
        'fractional_fee': 0.0,
        'supports_most_stocks': False
    },
    'sofi': {
        'name': 'SoFi Invest',
        'commission': 0.0,
        'min_investment': 1.0,
        'fractional_fee': 0.0,
        'supports_most_stocks': False
    }
}


def get_real_time_price(ticker: str) -> Dict[str, Any]:
    """Get real-time price data for a stock."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        info = stock.info
        
        if hist.empty:
            return {'error': f'No price data available for {ticker}'}
        
        current_price = hist['Close'].iloc[-1]
        prev_close = info.get('previousClose', current_price)
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0
        
        return {
            'ticker': ticker,
            'current_price': round(current_price, 2),
            'change': round(change, 2),
            'change_percent': round(change_pct, 2),
            'previous_close': round(prev_close, 2),
            'market_cap': info.get('marketCap'),
            'company_name': info.get('longName', ticker),
            'last_updated': datetime.now().isoformat()
        }
    except Exception as e:
        return {'error': f'Error fetching price for {ticker}: {str(e)}'}


def calculate_precision_shares(dollar_amount: float, price: float) -> Dict[str, float]:
    """Calculate fractional shares with high precision."""
    shares = dollar_amount / price
    
    return {
        'shares_4_decimal': round(shares, 4),
        'shares_6_decimal': round(shares, 6),
        'exact_shares': shares,
        'percentage_of_share': round(shares * 100, 4),
        'exact_cost': round(shares * price, 2)
    }


def get_dividend_projections(ticker: str, shares: float) -> Dict[str, float]:
    """Calculate dividend projections for fractional shares."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        dividend_yield = info.get('dividendYield', 0)
        dividend_rate = info.get('dividendRate', 0)
        
        if not dividend_yield and not dividend_rate:
            return {
                'has_dividend': False,
                'annual_dividend': 0,
                'quarterly_dividend': 0,
                'monthly_dividend': 0
            }
        
        # Calculate annual dividend income
        annual_dividend = shares * dividend_rate if dividend_rate else 0
        quarterly_dividend = annual_dividend / 4
        monthly_dividend = annual_dividend / 12
        
        return {
            'has_dividend': True,
            'dividend_yield': round(dividend_yield * 100, 2) if dividend_yield else 0,
            'annual_dividend': round(annual_dividend, 2),
            'quarterly_dividend': round(quarterly_dividend, 2),
            'monthly_dividend': round(monthly_dividend, 2),
            'shares': shares
        }
    except Exception:
        return {'has_dividend': False, 'annual_dividend': 0}


def calculate_growth_projections(ticker: str, investment_amount: float, years: int = 5) -> Dict[str, Any]:
    """Calculate potential growth projections for fractional investment."""
    try:
        stock = yf.Ticker(ticker)
        
        # Get historical data for growth calculation
        hist = stock.history(period="5y")
        if len(hist) < 252:  # Less than 1 year of data
            hist = stock.history(period="max")
        
        if hist.empty:
            return {'error': 'Insufficient historical data'}
        
        # Calculate annualized return
        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        periods = len(hist) / 252  # Approximate years
        
        if periods > 0:
            annual_return = ((end_price / start_price) ** (1 / periods)) - 1
        else:
            annual_return = 0
        
        # Project future values (conservative, moderate, optimistic)
        conservative_rate = max(annual_return * 0.5, 0.03)  # At least 3%
        moderate_rate = annual_return
        optimistic_rate = annual_return * 1.5
        
        projections = {}
        for scenario, rate in [('conservative', conservative_rate), 
                              ('moderate', moderate_rate), 
                              ('optimistic', optimistic_rate)]:
            future_value = investment_amount * ((1 + rate) ** years)
            gain = future_value - investment_amount
            
            projections[scenario] = {
                'future_value': round(future_value, 2),
                'total_gain': round(gain, 2),
                'annualized_return': round(rate * 100, 2)
            }
        
        return {
            'ticker': ticker,
            'investment_amount': investment_amount,
            'projection_years': years,
            'historical_annual_return': round(annual_return * 100, 2),
            'projections': projections
        }
        
    except Exception as e:
        return {'error': f'Error calculating projections: {str(e)}'}


def get_comparison_table(tickers: List[str], dollar_amount: float) -> List[Dict[str, Any]]:
    """Get a comparison table of fractional shares for multiple stocks."""
    comparison = []
    
    for ticker in tickers:
        price_data = get_real_time_price(ticker)
        
        if 'error' not in price_data:
            current_price = price_data['current_price']
            precision_calc = calculate_precision_shares(dollar_amount, current_price)
            dividend_data = get_dividend_projections(ticker, precision_calc['shares_4_decimal'])
            
            comparison.append({
                'ticker': ticker,
                'company_name': price_data['company_name'],
                'current_price': current_price,
                'shares': precision_calc['shares_4_decimal'],
                'percentage_of_share': precision_calc['percentage_of_share'],
                'exact_cost': precision_calc['exact_cost'],
                'annual_dividend': dividend_data.get('annual_dividend', 0),
                'dividend_yield': dividend_data.get('dividend_yield', 0),
                'market_cap': price_data.get('market_cap'),
                'change_percent': price_data.get('change_percent', 0)
            })
    
    return comparison


def validate_investment_amount(amount: float) -> Tuple[bool, str]:
    """Validate investment amount for fractional shares."""
    if amount < 1:
        return False, "Minimum investment amount is $1"
    elif amount > 50000:
        return False, "Maximum investment amount is $50,000"
    elif amount < 10:
        return True, "Warning: Very small amounts may have limited diversification options"
    else:
        return True, "Valid investment amount"


def get_portfolio_rebalancing_suggestions(current_portfolio: List[Dict], target_allocation: Dict) -> List[Dict]:
    """Generate rebalancing suggestions for fractional portfolio."""
    suggestions = []
    
    total_value = sum(pos['current_value'] for pos in current_portfolio)
    
    for position in current_portfolio:
        ticker = position['ticker']
        current_allocation = (position['current_value'] / total_value) * 100
        target_pct = target_allocation.get(ticker, 0)
        
        difference = target_pct - current_allocation
        
        if abs(difference) > 5:  # Only suggest if difference > 5%
            action = "Buy" if difference > 0 else "Sell"
            amount = abs(difference) / 100 * total_value
            
            suggestions.append({
                'ticker': ticker,
                'action': action,
                'amount': round(amount, 2),
                'current_allocation': round(current_allocation, 1),
                'target_allocation': target_pct,
                'difference': round(difference, 1)
            })
    
    return suggestions


def calculate_cost_averaging_schedule(total_amount: float, frequency: str, duration_months: int) -> List[Dict]:
    """Calculate dollar cost averaging schedule for fractional investing."""
    
    frequency_map = {
        'weekly': 52 / 12,  # weeks per month
        'bi-weekly': 26 / 12,  # bi-weeks per month  
        'monthly': 1,
        'quarterly': 1/3
    }
    
    investments_per_month = frequency_map.get(frequency, 1)
    total_investments = int(duration_months * investments_per_month)
    amount_per_investment = total_amount / total_investments
    
    schedule = []
    current_date = datetime.now()
    
    for i in range(total_investments):
        if frequency == 'weekly':
            investment_date = current_date + timedelta(weeks=i)
        elif frequency == 'bi-weekly':
            investment_date = current_date + timedelta(weeks=i*2)
        elif frequency == 'monthly':
            investment_date = current_date + timedelta(days=i*30)
        else:  # quarterly
            investment_date = current_date + timedelta(days=i*90)
        
        schedule.append({
            'investment_number': i + 1,
            'date': investment_date.strftime('%Y-%m-%d'),
            'amount': round(amount_per_investment, 2),
            'cumulative_invested': round((i + 1) * amount_per_investment, 2)
        })
    
    return schedule


def get_fractional_education_content() -> Dict[str, Any]:
    """Get educational content about fractional shares."""
    return {
        'basics': {
            'title': 'What are Fractional Shares?',
            'content': 'Fractional shares let you buy a portion of a stock rather than a whole share. For example, if Apple costs $150 per share and you have $50, you can buy 0.33 shares (33.3% of one share).',
            'benefits': [
                'Start investing with small amounts',
                'Diversify with expensive stocks',
                'Dollar-cost averaging made easy',
                'Proportional dividend payments'
            ]
        },
        'how_it_works': {
            'title': 'How Fractional Trading Works',
            'steps': [
                'Choose your investment amount ($1-$10,000)',
                'Select the stock you want to buy',
                'The broker calculates your fractional share (to 4 decimals)',
                'You own that percentage of the company',
                'Receive proportional dividends and voting rights'
            ]
        },
        'best_practices': {
            'title': 'Fractional Investing Best Practices',
            'tips': [
                'Start with well-known, large companies',
                'Diversify across 3-5 different stocks',
                'Consider dollar-cost averaging',
                'Reinvest dividends automatically',
                'Monitor your portfolio regularly'
            ]
        },
        'broker_comparison': BROKER_INFO
    }