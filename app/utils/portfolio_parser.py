"""
Portfolio Parser Utility
Parses CrewAI text output into structured portfolio data
"""

import re
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def parse_portfolio_output(crew_output: str, investment_amount: float) -> Dict:
    """
    Parse CrewAI portfolio text output into structured data.
    
    Args:
        crew_output: Raw text output from portfolio crew
        investment_amount: Total investment amount
        
    Returns:
        Structured portfolio data dict
    """
    try:
        # Extract raw text from crew output
        if hasattr(crew_output, 'tasks_output') and crew_output.tasks_output:
            text = crew_output.tasks_output[0].raw if crew_output.tasks_output else ""
        else:
            text = str(crew_output)
        
        portfolio_data = {
            "tickers": [],
            "weights": [],
            "amounts": [],
            "reasoning": {},
            "total_amount": investment_amount,
            "allocations": [],
            "expected_return": None,
            "key_risks": []
        }
        
        # Common patterns for parsing - enhanced to capture category
        # Pattern 1: "TICKER - XX% ($X,XXX) - Category/Sector - reasoning"
        # or "TICKER (Category) - XX% ($X,XXX) - reasoning"
        pattern1 = r'([A-Z]{2,5})(?:\s*\(([^)]+)\))?\s*[-:]\s*(\d+(?:\.\d+)?)\s*%\s*\(\$?([\d,]+(?:\.\d+)?)\)\s*(?:[-:]\s*([^-\n]+?))?(?:[-:]\s*(.+?))?(?=\n|$)'
        
        # Pattern 2: "TICKER: XX% allocation ($X,XXX) - Category"
        pattern2 = r'([A-Z]{2,5}):\s*(\d+(?:\.\d+)?)\s*%.*?\(\$?([\d,]+(?:\.\d+)?)\)(?:\s*[-:]\s*([^-\n]+))?'
        
        # Pattern 3: "XX% TICKER ($X,XXX) - Category"
        pattern3 = r'(\d+(?:\.\d+)?)\s*%\s*([A-Z]{2,5})\s*\(\$?([\d,]+(?:\.\d+)?)\)(?:\s*[-:]\s*([^-\n]+))?'
        
        # Try different patterns
        matches = re.findall(pattern1, text, re.MULTILINE | re.IGNORECASE)
        if not matches:
            matches = re.findall(pattern2, text, re.MULTILINE | re.IGNORECASE)
        if not matches:
            # Try pattern 3 and rearrange
            temp_matches = re.findall(pattern3, text, re.MULTILINE | re.IGNORECASE)
            matches = [(m[1], m[0], m[2], "") for m in temp_matches]
        
        # Process matches - use dictionary to consolidate duplicates
        ticker_data = {}
        total_percentage = 0
        
        for match in matches:
            if len(match) >= 3:
                # Handle different pattern structures
                if len(match) == 6:  # Pattern 1 with category
                    ticker = match[0].upper()
                    category_in_parens = match[1]
                    percentage = float(match[2])
                    amount_str = match[3].replace(',', '')
                    category_after = match[4]
                    reasoning = match[5]
                elif len(match) == 5:  # Pattern with category at end
                    ticker = match[0].upper()
                    percentage = float(match[1])
                    amount_str = match[2].replace(',', '')
                    category_or_reasoning = match[3]
                    extra = match[4] if len(match) > 4 else ""
                elif len(match) == 4:  # Pattern 2 or 3 with category
                    if match[0].replace('.', '').isdigit():  # Pattern 3
                        percentage = float(match[0])
                        ticker = match[1].upper()
                        amount_str = match[2].replace(',', '')
                        category_or_reasoning = match[3]
                    else:  # Pattern 2
                        ticker = match[0].upper()
                        percentage = float(match[1])
                        amount_str = match[2].replace(',', '')
                        category_or_reasoning = match[3]
                else:  # Original pattern without category
                    ticker = match[0].upper()
                    percentage = float(match[1])
                    amount_str = match[2].replace(',', '')
                    category_or_reasoning = match[3] if len(match) > 3 else ""
                    category_in_parens = ""
                    category_after = ""
                
                amount = float(amount_str)
                
                # Extract category and reasoning
                category = ""
                reasoning = ""
                
                # Priority: category in parentheses, then category after amount
                if 'category_in_parens' in locals() and category_in_parens:
                    category = category_in_parens.strip()
                elif 'category_after' in locals() and category_after:
                    # Check if this looks like a category (short, title case, common sectors)
                    category_keywords = ['Technology', 'Healthcare', 'Financial', 'Consumer', 'Energy', 
                                       'Industrial', 'ETF', 'Bond', 'Real Estate', 'Growth', 'Value',
                                       'Large Cap', 'Small Cap', 'International', 'Emerging Markets']
                    if any(keyword in category_after for keyword in category_keywords):
                        category = category_after.strip()
                        reasoning = locals().get('reasoning', '').strip()
                    else:
                        reasoning = category_after.strip()
                elif 'category_or_reasoning' in locals() and category_or_reasoning:
                    # Check if it's likely a category
                    if len(category_or_reasoning.split()) <= 3 and any(word in category_or_reasoning for word in ['ETF', 'Tech', 'Health', 'Financial', 'Consumer', 'Growth']):
                        category = category_or_reasoning.strip()
                    else:
                        reasoning = category_or_reasoning.strip()
                
                # Clean up reasoning if it exists
                if 'extra' in locals() and extra and not reasoning:
                    reasoning = extra.strip()
                
                # Validate ticker (2-5 uppercase letters)
                if 2 <= len(ticker) <= 5 and ticker.isalpha():
                    # If ticker already exists, use the highest percentage allocation
                    if ticker in ticker_data:
                        if percentage > ticker_data[ticker]['percentage']:
                            ticker_data[ticker] = {
                                'percentage': percentage,
                                'amount': amount,
                                'reasoning': reasoning,
                                'category': category
                            }
                            logger.debug(f"Updated {ticker} allocation to {percentage}%")
                    else:
                        ticker_data[ticker] = {
                            'percentage': percentage,
                            'amount': amount,
                            'reasoning': reasoning,
                            'category': category
                        }
                        logger.debug(f"Parsed allocation: {ticker} - {percentage}% (${amount}) - {category}")
        
        # Convert consolidated data to lists
        for ticker, data in ticker_data.items():
            portfolio_data["tickers"].append(ticker)
            portfolio_data["weights"].append(data['percentage'] / 100)  # Convert to decimal
            portfolio_data["amounts"].append(data['amount'])
            portfolio_data["reasoning"][ticker] = data['reasoning']
            
            portfolio_data["allocations"].append({
                "ticker": ticker,
                "percentage": data['percentage'],
                "amount": data['amount'],
                "reasoning": data['reasoning'],
                "category": data['category'] if data['category'] else "N/A"
            })
            total_percentage += data['percentage']
        
        # Extract expected return
        return_patterns = [
            r'expected.*?annual.*?return.*?(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%',
            r'annual.*?return.*?(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%',
            r'return.*?range.*?(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%'
        ]
        
        for pattern in return_patterns:
            return_match = re.search(pattern, text, re.IGNORECASE)
            if return_match:
                portfolio_data["expected_return"] = f"{return_match.group(1)}-{return_match.group(2)}%"
                break
        
        # Extract key risks
        risk_section = re.search(r'key\s+risks.*?:(.*?)(?=\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
        if risk_section:
            risk_text = risk_section.group(1)
            # Split by common delimiters
            risks = re.split(r'[•\-\*\n]+', risk_text)
            portfolio_data["key_risks"] = [risk.strip() for risk in risks if risk.strip() and len(risk.strip()) > 10]
        
        # Validate parsing results
        if not portfolio_data["tickers"]:
            logger.warning("No valid tickers found in portfolio output")
            # Fallback: try to extract any ticker-like strings
            ticker_pattern = r'\b([A-Z]{2,5})\b'
            potential_tickers = re.findall(ticker_pattern, text)
            # Filter out common words
            excluded = {'THE', 'AND', 'FOR', 'YOU', 'ETF', 'REIT', 'USD', 'API'}
            valid_tickers = [t for t in potential_tickers if t not in excluded][:5]
            
            if valid_tickers:
                # Assume equal weights if we can't parse percentages
                equal_weight = 1.0 / len(valid_tickers)
                for ticker in valid_tickers:
                    portfolio_data["tickers"].append(ticker)
                    portfolio_data["weights"].append(equal_weight)
                    portfolio_data["amounts"].append(investment_amount * equal_weight)
                    portfolio_data["allocations"].append({
                        "ticker": ticker,
                        "percentage": equal_weight * 100,
                        "amount": investment_amount * equal_weight,
                        "reasoning": "Extracted from text"
                    })
        
        # Normalize weights if they don't sum to 1
        if portfolio_data["weights"]:
            weight_sum = sum(portfolio_data["weights"])
            if abs(weight_sum - 1.0) > 0.01:  # More than 1% off
                logger.info(f"Normalizing weights (sum was {weight_sum})")
                portfolio_data["weights"] = [w / weight_sum for w in portfolio_data["weights"]]
                # Update allocations
                for i, alloc in enumerate(portfolio_data["allocations"]):
                    alloc["percentage"] = portfolio_data["weights"][i] * 100
                    alloc["amount"] = investment_amount * portfolio_data["weights"][i]
        
        logger.info(f"Successfully parsed portfolio: {len(portfolio_data['tickers'])} positions")
        return portfolio_data
        
    except Exception as e:
        logger.error(f"Error parsing portfolio output: {str(e)}")
        # Return a minimal valid structure
        return {
            "tickers": [],
            "weights": [],
            "amounts": [],
            "reasoning": {},
            "total_amount": investment_amount,
            "allocations": [],
            "expected_return": None,
            "key_risks": [],
            "error": str(e)
        }


def validate_portfolio_data(portfolio_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate parsed portfolio data.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    if not portfolio_data.get("tickers"):
        errors.append("No tickers found")
    
    if not portfolio_data.get("weights"):
        errors.append("No weights found")
    
    # Check lengths match
    if len(portfolio_data.get("tickers", [])) != len(portfolio_data.get("weights", [])):
        errors.append("Tickers and weights length mismatch")
    
    # Check weights sum to ~1
    if portfolio_data.get("weights"):
        weight_sum = sum(portfolio_data["weights"])
        if abs(weight_sum - 1.0) > 0.05:  # 5% tolerance
            errors.append(f"Weights sum to {weight_sum:.2f}, not 1.0")
    
    # Check for valid tickers
    for ticker in portfolio_data.get("tickers", []):
        if not (2 <= len(ticker) <= 5 and ticker.isalpha() and ticker.isupper()):
            errors.append(f"Invalid ticker format: {ticker}")
    
    return len(errors) == 0, errors