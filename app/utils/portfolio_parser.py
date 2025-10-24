"""
Portfolio Parser Utility - Simplified Version
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

        # Simplified pattern: TICKER - XX% ($X,XXX) - Full text after (category and/or reasoning)
        # Captures everything after amount in one group, preserving hyphenated words
        pattern = r'([A-Z]{2,5})(?:\s*\(([^)]+)\))?\s*[-:]\s*(\d+(?:\.\d+)?)\s*%\s*\(\$?([\d,]+(?:\.\d+)?)\)\s*[-:]\s*(.+?)(?=\n+[A-Z]{2,5}(?:\s*\([^)]+\))?\s*[-:]\s*\d+(?:\.\d+)?%|##|\Z)'

        matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE | re.DOTALL)

        # Process matches
        ticker_data = {}
        total_percentage = 0

        for match in matches:
            if len(match) >= 3:
                ticker = match[0].upper()
                category_in_parens = match[1].strip() if match[1] else ""
                percentage = float(match[2])
                amount_str = match[3].replace(',', '')
                full_text = match[4].strip() if len(match) > 4 else ""

                amount = float(amount_str)

                # Start with category from parentheses if available
                category = category_in_parens if category_in_parens else ""
                reasoning_text = full_text

                # If there's " - " in the text and no category from parens, try to split
                if ' - ' in full_text and not category:
                    parts = full_text.split(' - ', 1)
                    first_part = parts[0].strip()

                    # Check if first part looks like a category
                    category_keywords = ['Technology', 'Healthcare', 'Financial', 'Consumer', 'Energy',
                                       'Industrial', 'ETF', 'Stock ETF', 'Bond ETF', 'International ETF', 'REIT ETF',
                                       'Dividend ETF', 'Bond', 'Treasury', 'Fixed Income', 'Real Estate', 'REIT', 'Growth',
                                       'Value', 'Large Cap', 'Small Cap', 'International', 'Global', 'Emerging Markets',
                                       'Intermediate', 'Short', 'Long', 'Term', 'Government']

                    is_category = (len(first_part.split()) <= 5 and
                                 any(keyword.lower() in first_part.lower() for keyword in category_keywords))

                    if is_category:
                        category = first_part
                        reasoning_text = parts[1].strip() if len(parts) > 1 else full_text
                    # else: keep full_text as reasoning (don't split hyphenated words)

                # Validate ticker (2-5 uppercase letters)
                if 2 <= len(ticker) <= 5 and ticker.isalpha():
                    # If ticker already exists, use the highest percentage allocation
                    if ticker in ticker_data:
                        if percentage > ticker_data[ticker]['percentage']:
                            ticker_data[ticker] = {
                                'percentage': percentage,
                                'amount': amount,
                                'reasoning': reasoning_text,
                                'category': category
                            }
                            logger.debug(f"Updated {ticker} allocation to {percentage}%")
                    else:
                        ticker_data[ticker] = {
                            'percentage': percentage,
                            'amount': amount,
                            'reasoning': reasoning_text,
                            'category': category
                        }
                        logger.debug(f"Parsed allocation: {ticker} - {percentage}% - reasoning: '{reasoning_text[:50]}...'")

        # Convert consolidated data to lists
        for ticker, data in ticker_data.items():
            portfolio_data["tickers"].append(ticker)
            portfolio_data["weights"].append(data['percentage'] / 100)  # Convert to decimal
            portfolio_data["amounts"].append(data['amount'])

            # Ensure reasoning is never empty - add fallback
            reasoning = data['reasoning']
            if not reasoning or reasoning.strip() == "":
                # Generate fallback reasoning based on category or generic
                if data['category'] and data['category'] != "N/A":
                    reasoning = f"Diversification in {data['category']} sector"
                else:
                    reasoning = f"Core portfolio holding for diversification"
                logger.info(f"Added fallback reasoning for {ticker}: {reasoning}")

            portfolio_data["reasoning"][ticker] = reasoning

            portfolio_data["allocations"].append({
                "ticker": ticker,
                "percentage": data['percentage'],
                "amount": data['amount'],
                "reasoning": reasoning,
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

        logger.info(f"Parsed portfolio with {len(portfolio_data['tickers'])} holdings, total {total_percentage:.1f}%")
        return portfolio_data

    except Exception as e:
        logger.error(f"Error parsing portfolio output: {e}", exc_info=True)
        return {
            "tickers": [],
            "weights": [],
            "amounts": [],
            "reasoning": {},
            "total_amount": investment_amount,
            "allocations": [],
            "expected_return": None,
            "key_risks": []
        }


def validate_portfolio_data(portfolio_data: Dict) -> bool:
    """Validate that portfolio data is properly structured"""
    required_keys = ["tickers", "weights", "amounts", "reasoning"]
    return all(key in portfolio_data for key in required_keys) and len(portfolio_data["tickers"]) > 0
