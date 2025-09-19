import yfinance as yf
from crewai.tools import tool
import logging

logger = logging.getLogger(__name__)

@tool
def competitor_analysis(ticker: str, num_competitors: int = 3):
    """
    Perform competitor analysis for a given stock.
    
    Args:
        ticker (str): The stock ticker symbol.
        num_competitors (int): Number of top competitors to analyze.
    
    Returns:
        dict: Competitor analysis results.
    """
    logger.debug(f"Starting competitor analysis for ticker: {ticker}, num_competitors: {num_competitors}")
    
    try:
        stock = yf.Ticker(ticker)
        logger.debug(f"Created yfinance Ticker object for: {ticker}")
        
        info = stock.info
        logger.debug(f"Retrieved stock info for {ticker}: {len(info)} fields")
        
        sector = info.get('sector')
        industry = info.get('industry')
        logger.debug(f"Stock sector: {sector}, industry: {industry}")
    
        # Get competitors in the same industry
        logger.debug(f"Attempting to get industry components for sector: {sector}")
        try:
            industry_stocks = yf.Ticker(f"^{sector}").info.get('components', [])
            logger.debug(f"Found {len(industry_stocks)} stocks in sector {sector}")
        except Exception as e:
            logger.warning(f"Failed to get sector components: {e}. Using empty list.")
            industry_stocks = []
        
        competitors = [comp for comp in industry_stocks if comp != ticker][:num_competitors]
        logger.debug(f"Selected {len(competitors)} competitors: {competitors}")
    
        competitor_data = []
        for i, comp in enumerate(competitors):
            logger.debug(f"Analyzing competitor {i+1}/{len(competitors)}: {comp}")
            try:
                comp_stock = yf.Ticker(comp)
                comp_info = comp_stock.info
                logger.debug(f"Retrieved info for {comp}: {len(comp_info)} fields")
                
                comp_data = {
                    "ticker": comp,
                    "name": comp_info.get('longName'),
                    "market_cap": comp_info.get('marketCap'),
                    "pe_ratio": comp_info.get('trailingPE'),
                    "revenue_growth": comp_info.get('revenueGrowth'),
                    "profit_margins": comp_info.get('profitMargins')
                }
                competitor_data.append(comp_data)
                logger.debug(f"Added competitor data for {comp}: {comp_data}")
            except Exception as e:
                logger.error(f"Failed to get data for competitor {comp}: {e}")
                continue
    
        result = {
            "main_stock": ticker,
            "industry": industry,
            "competitors": competitor_data
        }
        logger.debug(f"Competitor analysis complete. Found {len(competitor_data)} valid competitors")
        return result
    
    except Exception as e:
        logger.error(f"Error in competitor_analysis for {ticker}: {e}")
        return {
            "main_stock": ticker,
            "industry": None,
            "competitors": [],
            "error": str(e)
        }
