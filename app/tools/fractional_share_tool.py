import yfinance as yf
from crewai.tools import tool
from typing import Dict, Any, List
import numpy as np

@tool
def calculate_fractional_shares(dollar_amount: float, ticker: str) -> Dict[str, Any]:
    """
    Calculate fractional shares for a given dollar amount and stock ticker.
    
    Args:
        dollar_amount (float): The dollar amount to invest ($10-$10,000)
        ticker (str): The stock ticker symbol (e.g., AAPL, TSLA)
    
    Returns:
        dict: Fractional share calculation results including shares, percentage ownership, 
              current price, exact cost, and broker compatibility.
    """
    try:
        # Validate input
        if dollar_amount < 10 or dollar_amount > 10000:
            return {
                "error": "Investment amount must be between $10 and $10,000",
                "ticker": ticker,
                "dollar_amount": dollar_amount
            }
        
        # Get current stock price
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1d")
        
        if hist.empty:
            return {
                "error": f"Unable to fetch price data for {ticker}",
                "ticker": ticker,
                "dollar_amount": dollar_amount
            }
        
        current_price = hist['Close'].iloc[-1]
        company_name = info.get('longName', ticker)
        
        # Calculate fractional shares (to 4 decimal places)
        shares = round(dollar_amount / current_price, 4)
        exact_cost = round(shares * current_price, 2)
        percentage_of_share = round(shares * 100, 4)
        
        # Check if broker supports fractional trading for this stock
        broker_support = check_fractional_broker_support(ticker, info)
        
        # Calculate potential dividend income (if applicable)
        dividend_yield = info.get('dividendYield', 0)
        annual_dividend_income = round(exact_cost * (dividend_yield or 0), 2) if dividend_yield else 0
        
        return {
            "ticker": ticker,
            "company_name": company_name,
            "dollar_amount": dollar_amount,
            "current_price": round(current_price, 2),
            "shares": shares,
            "exact_cost": exact_cost,
            "percentage_of_share": percentage_of_share,
            "broker_support": broker_support,
            "annual_dividend_income": annual_dividend_income,
            "dividend_yield": dividend_yield,
            "market_cap": info.get('marketCap'),
            "sector": info.get('sector'),
            "error": None
        }
        
    except Exception as e:
        return {
            "error": f"Error calculating fractional shares for {ticker}: {str(e)}",
            "ticker": ticker,
            "dollar_amount": dollar_amount
        }


@tool  
def get_fractional_portfolio_suggestions(total_amount: float, user_profile: Dict[str, str] = None) -> List[Dict[str, Any]]:
    """
    Generate fractional share portfolio suggestions based on investment amount and user profile.
    
    Args:
        total_amount (float): Total dollar amount to invest
        user_profile (dict): User profile with age_range, risk_profile, primary_goal, etc.
        
    Returns:
        list: List of suggested fractional share allocations
    """
    try:
        if total_amount < 25:
            return {
                "error": "Minimum amount for portfolio diversification is $25",
                "suggestions": []
            }
        
        # Get user preferences or use defaults
        if not user_profile:
            user_profile = {
                'age_range': '25-35',
                'risk_profile': 'moderate',
                'primary_goal': 'wealth_building'
            }
        
        age_range = user_profile.get('age_range', '25-35')
        risk_profile = user_profile.get('risk_profile', 'moderate').lower()
        primary_goal = user_profile.get('primary_goal', 'wealth_building')
        
        # Base stock suggestions based on user profile
        suggestions = get_personalized_stock_suggestions(age_range, risk_profile, primary_goal)
        
        # Calculate allocations based on total amount
        if total_amount < 100:
            # 2-3 positions for small amounts
            num_positions = 2 if total_amount < 50 else 3
            allocations = [0.5, 0.5] if num_positions == 2 else [0.4, 0.35, 0.25]
        elif total_amount < 500:
            # 3-5 positions for medium amounts  
            num_positions = 4
            allocations = [0.35, 0.25, 0.25, 0.15]
        else:
            # 5-8 positions for larger amounts
            num_positions = 6
            allocations = [0.25, 0.20, 0.20, 0.15, 0.10, 0.10]
        
        # Create portfolio suggestions
        portfolio = []
        for i in range(min(num_positions, len(suggestions))):
            ticker = suggestions[i]
            allocation_pct = allocations[i]
            allocation_amount = total_amount * allocation_pct
            
            # Calculate fractional shares for this allocation
            calc_result = calculate_fractional_shares(allocation_amount, ticker)
            
            if not calc_result.get('error'):
                portfolio.append({
                    'ticker': ticker,
                    'allocation_percentage': round(allocation_pct * 100, 1),
                    'allocation_amount': round(allocation_amount, 2),
                    'shares': calc_result['shares'],
                    'company_name': calc_result['company_name'],
                    'rationale': get_allocation_rationale(ticker, risk_profile, primary_goal)
                })
        
        return {
            "total_amount": total_amount,
            "num_positions": len(portfolio),
            "portfolio": portfolio,
            "diversification_score": calculate_diversification_score(portfolio),
            "risk_level": risk_profile,
            "error": None
        }
        
    except Exception as e:
        return {
            "error": f"Error generating portfolio suggestions: {str(e)}",
            "suggestions": []
        }


def check_fractional_broker_support(ticker: str, info: Dict) -> Dict[str, bool]:
    """Check which brokers support fractional trading for this stock."""
    
    # List of popular fractional trading stocks (this would be expanded with real data)
    popular_fractional_stocks = {
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 
        'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'BAC', 'XOM', 'ABBV', 'PFE',
        'AVGO', 'LLY', 'KO', 'PEP', 'TMO', 'COST', 'WMT', 'MRK', 'DIS'
    }
    
    # Market cap threshold (usually $1B+ for fractional trading)
    market_cap = info.get('marketCap', 0)
    large_cap = market_cap and market_cap > 1_000_000_000
    
    is_supported = ticker.upper() in popular_fractional_stocks or large_cap
    
    return {
        'robinhood': is_supported,
        'fidelity': is_supported and large_cap,
        'schwab': is_supported and large_cap,
        'webull': is_supported,
        'sofi': is_supported,
        'general_support': is_supported
    }


def get_personalized_stock_suggestions(age_range: str, risk_profile: str, primary_goal: str) -> List[str]:
    """Get personalized stock suggestions based on user profile."""
    
    # Base suggestions for different profiles
    conservative_stocks = ['AAPL', 'MSFT', 'JNJ', 'PG', 'KO', 'PEP', 'WMT', 'V']
    moderate_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'V', 'MA', 'JPM', 'UNH']
    aggressive_stocks = ['TSLA', 'NVDA', 'META', 'GOOGL', 'AMZN', 'AVGO', 'AMD', 'CRM']
    
    # Young investor focus
    young_investor_stocks = ['AAPL', 'TSLA', 'GOOGL', 'META', 'NVDA', 'AMZN', 'DIS', 'MSFT']
    
    # Goal-based adjustments
    dividend_stocks = ['JNJ', 'PG', 'KO', 'PEP', 'ABBV', 'MRK', 'XOM', 'T']
    growth_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'CRM']
    
    # Select base stocks based on risk profile
    if risk_profile == 'conservative':
        base_stocks = conservative_stocks
    elif risk_profile == 'aggressive':
        base_stocks = aggressive_stocks
    else:
        base_stocks = moderate_stocks
    
    # Adjust for age
    if any(age in age_range for age in ['16-20', '21-25', '26-30']):
        # Young investors - add growth focus
        base_stocks = list(set(base_stocks + young_investor_stocks[:4]))
    
    # Adjust for goals
    if 'income' in primary_goal.lower() or 'dividend' in primary_goal.lower():
        base_stocks = list(set(base_stocks[:4] + dividend_stocks[:4]))
    elif 'growth' in primary_goal.lower() or 'wealth' in primary_goal.lower():
        base_stocks = list(set(base_stocks[:4] + growth_stocks[:4]))
    
    return base_stocks[:8]  # Return top 8 suggestions


def get_allocation_rationale(ticker: str, risk_profile: str, primary_goal: str) -> str:
    """Get rationale for including a stock in the portfolio."""
    
    rationales = {
        'AAPL': f"Apple provides stable growth suitable for {risk_profile} investors seeking {primary_goal}",
        'MSFT': f"Microsoft offers reliable returns and dividend growth for {primary_goal}",
        'GOOGL': f"Google provides strong growth potential aligned with {primary_goal} objectives",
        'AMZN': f"Amazon offers exposure to e-commerce and cloud computing growth",
        'TSLA': f"Tesla provides exposure to electric vehicle and clean energy trends",
        'META': f"Meta offers exposure to social media and metaverse technologies",
        'NVDA': f"NVIDIA provides exposure to AI and semiconductor growth",
        'JNJ': f"Johnson & Johnson offers stability and consistent dividends",
        'V': f"Visa provides exposure to digital payments growth",
        'JPM': f"JPMorgan offers exposure to financial sector with dividend income"
    }
    
    return rationales.get(ticker, f"{ticker} provides diversification for your {risk_profile} risk portfolio")


def calculate_diversification_score(portfolio: List[Dict]) -> float:
    """Calculate a simple diversification score for the portfolio."""
    
    if len(portfolio) < 2:
        return 0.0
    
    # Basic diversification score based on number of positions and allocation balance
    num_positions = len(portfolio)
    
    # Calculate allocation balance (lower is more balanced)
    allocations = [pos['allocation_percentage'] for pos in portfolio]
    allocation_variance = np.var(allocations)
    
    # Score from 0-100
    position_score = min(num_positions * 15, 60)  # Up to 60 points for positions
    balance_score = max(40 - allocation_variance, 0)  # Up to 40 points for balance
    
    return round(position_score + balance_score, 1)