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
        
        # Common patterns for parsing
        # Pattern 1: "TICKER - XX% ($X,XXX) - reasoning"
        pattern1 = r'([A-Z]{2,5})\s*[-:]\s*(\d+(?:\.\d+)?)\s*%\s*\(\$?([\d,]+(?:\.\d+)?)\)\s*[-:]?\s*(.+?)(?=\n|$)'
        
        # Pattern 2: "TICKER: XX% allocation ($X,XXX)"
        pattern2 = r'([A-Z]{2,5}):\s*(\d+(?:\.\d+)?)\s*%.*?\(\$?([\d,]+(?:\.\d+)?)\)'
        
        # Pattern 3: "XX% TICKER ($X,XXX)"
        pattern3 = r'(\d+(?:\.\d+)?)\s*%\s*([A-Z]{2,5})\s*\(\$?([\d,]+(?:\.\d+)?)\)'
        
        # Try different patterns
        matches = re.findall(pattern1, text, re.MULTILINE | re.IGNORECASE)
        if not matches:
            matches = re.findall(pattern2, text, re.MULTILINE | re.IGNORECASE)
        if not matches:
            # Try pattern 3 and rearrange
            temp_matches = re.findall(pattern3, text, re.MULTILINE | re.IGNORECASE)
            matches = [(m[1], m[0], m[2], "") for m in temp_matches]
        
        # Process matches
        total_percentage = 0
        for match in matches:
            if len(match) >= 3:
                ticker = match[0].upper()
                percentage = float(match[1])
                amount_str = match[2].replace(',', '')
                amount = float(amount_str)
                reasoning = match[3].strip() if len(match) > 3 else ""
                
                # Validate ticker (2-5 uppercase letters)
                if 2 <= len(ticker) <= 5 and ticker.isalpha():
                    portfolio_data["tickers"].append(ticker)
                    portfolio_data["weights"].append(percentage / 100)  # Convert to decimal
                    portfolio_data["amounts"].append(amount)
                    portfolio_data["reasoning"][ticker] = reasoning
                    portfolio_data["allocations"].append({
                        "ticker": ticker,
                        "percentage": percentage,
                        "amount": amount,
                        "reasoning": reasoning
                    })
                    total_percentage += percentage
                    
                    logger.debug(f"Parsed allocation: {ticker} - {percentage}% (${amount})")
        
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