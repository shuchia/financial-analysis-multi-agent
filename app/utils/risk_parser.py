"""
Risk Analysis Parser Utility
Parses CrewAI risk analysis output into structured data
"""

import re
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def parse_risk_output(crew_output, user_profile: Optional[Dict] = None, investment_amount: float = 10000) -> Dict:
    """
    Parse CrewAI risk analysis text output into structured data matching risk_assessment tool format.

    Args:
        crew_output: Raw text output from risk analysis crew (CrewOutput object or string)
        user_profile: User's risk profile information
        investment_amount: Total investment amount

    Returns:
        Structured risk data dict matching risk_assessment tool format
    """
    try:
        # Extract raw text from crew output
        if hasattr(crew_output, 'tasks_output') and crew_output.tasks_output:
            text = crew_output.tasks_output[0].raw if crew_output.tasks_output else ""
        else:
            text = str(crew_output)

        risk_data = {
            "portfolio_metrics": {
                "beta": 1.0,
                "sharpe_ratio": 0.0,
                "value_at_risk_95": 0.0,
                "value_at_risk_99": 0.0,
                "max_drawdown": 0.0,
                "annual_volatility": 0.0,
                "expected_annual_return": 0.0
            },
            "risk_contributions": {},
            "risk_alignment": {
                "user_profile": user_profile.get('risk_profile', 'moderate') if user_profile else 'moderate',
                "risk_score": user_profile.get('risk_score', 0.5) if user_profile else 0.5,
                "portfolio_risk_level": "aligned",
                "expected_volatility_range": "12%-18%",
                "actual_volatility": "N/A",
                "adjustment_recommendation": None
            },
            "diversification_metrics": {
                "number_of_positions": 0,
                "effective_number_of_stocks": 0,
                "concentration_risk": "moderate"
            },
            "value_at_risk_interpretation": {
                "95%": "Data pending",
                "99%": "Data pending"
            }
        }

        # Parse Portfolio Beta
        beta_pattern = r'beta[:\s]+(\d+\.\d+)'
        beta_match = re.search(beta_pattern, text, re.IGNORECASE)
        if beta_match:
            risk_data["portfolio_metrics"]["beta"] = float(beta_match.group(1))

        # Parse Sharpe Ratio
        sharpe_pattern = r'sharpe\s+ratio[:\s]+(\d+\.\d+)'
        sharpe_match = re.search(sharpe_pattern, text, re.IGNORECASE)
        if sharpe_match:
            risk_data["portfolio_metrics"]["sharpe_ratio"] = float(sharpe_match.group(1))

        # Parse Annual Volatility (handle both percentage and decimal)
        vol_pattern = r'(?:annual\s+)?volatility[:\s]+(\d+(?:\.\d+)?)\s*%?'
        vol_match = re.search(vol_pattern, text, re.IGNORECASE)
        if vol_match:
            volatility = float(vol_match.group(1))
            # If it's already a percentage (>1), use as is, otherwise convert
            risk_data["portfolio_metrics"]["annual_volatility"] = volatility if volatility > 1 else volatility * 100

        # Parse Max Drawdown
        drawdown_pattern = r'max(?:imum)?\s+drawdown[:\s]+(\d+(?:\.\d+)?)\s*%?'
        drawdown_match = re.search(drawdown_pattern, text, re.IGNORECASE)
        if drawdown_match:
            drawdown = float(drawdown_match.group(1))
            risk_data["portfolio_metrics"]["max_drawdown"] = drawdown if drawdown > 1 else drawdown * 100

        # Parse VaR 95% - multiple patterns
        var95_patterns = [
            r'VaR.*?95%[:\s]+\$?(\d+(?:,\d+)?(?:\.\d+)?)',
            r'95%.*?VaR[:\s]+\$?(\d+(?:,\d+)?(?:\.\d+)?)',
            r'Value\s+at\s+Risk.*?95%[:\s]+(\d+(?:\.\d+)?)\s*%'
        ]
        for pattern in var95_patterns:
            var95_match = re.search(pattern, text, re.IGNORECASE)
            if var95_match:
                var_value = float(var95_match.group(1).replace(',', ''))
                # If it's a dollar amount, convert to percentage
                if var_value > 100:
                    var_value = (var_value / investment_amount) * 100
                risk_data["portfolio_metrics"]["value_at_risk_95"] = var_value
                break

        # Parse VaR 99%
        var99_patterns = [
            r'VaR.*?99%[:\s]+\$?(\d+(?:,\d+)?(?:\.\d+)?)',
            r'99%.*?VaR[:\s]+\$?(\d+(?:,\d+)?(?:\.\d+)?)',
            r'Value\s+at\s+Risk.*?99%[:\s]+(\d+(?:\.\d+)?)\s*%'
        ]
        for pattern in var99_patterns:
            var99_match = re.search(pattern, text, re.IGNORECASE)
            if var99_match:
                var_value = float(var99_match.group(1).replace(',', ''))
                if var_value > 100:
                    var_value = (var_value / investment_amount) * 100
                risk_data["portfolio_metrics"]["value_at_risk_99"] = var_value
                break

        # Parse Expected Return
        return_pattern = r'(?:expected|annual)\s+return[:\s]+(\d+(?:\.\d+)?)\s*%?'
        return_match = re.search(return_pattern, text, re.IGNORECASE)
        if return_match:
            expected_return = float(return_match.group(1))
            risk_data["portfolio_metrics"]["expected_annual_return"] = expected_return if expected_return > 1 else expected_return * 100

        # Parse risk alignment
        alignment_keywords = {
            'conservative': ['conservative', 'low risk', 'cautious'],
            'moderate': ['moderate', 'balanced', 'medium risk'],
            'aggressive': ['aggressive', 'high risk', 'growth']
        }

        text_lower = text.lower()
        for risk_level, keywords in alignment_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                risk_data["risk_alignment"]["portfolio_risk_level"] = risk_level
                break

        # Set alignment based on user profile
        user_risk = user_profile.get('risk_profile', 'moderate').lower() if user_profile else 'moderate'
        portfolio_risk = risk_data["risk_alignment"]["portfolio_risk_level"]

        if portfolio_risk == user_risk:
            risk_data["risk_alignment"]["portfolio_risk_level"] = "aligned"
        elif (portfolio_risk == 'conservative' and user_risk in ['moderate', 'aggressive']):
            risk_data["risk_alignment"]["portfolio_risk_level"] = "too_conservative"
        elif (portfolio_risk == 'aggressive' and user_risk in ['moderate', 'conservative']):
            risk_data["risk_alignment"]["portfolio_risk_level"] = "too_aggressive"

        # Update actual volatility
        if risk_data["portfolio_metrics"]["annual_volatility"] > 0:
            risk_data["risk_alignment"]["actual_volatility"] = f"{risk_data['portfolio_metrics']['annual_volatility']:.1f}%"

        # Create VaR interpretation
        if risk_data["portfolio_metrics"]["value_at_risk_95"] > 0:
            var95_dollars = (risk_data["portfolio_metrics"]["value_at_risk_95"] / 100) * investment_amount
            risk_data["value_at_risk_interpretation"]["95%"] = f"5% chance of losing more than ${var95_dollars:.2f} in a day"

        if risk_data["portfolio_metrics"]["value_at_risk_99"] > 0:
            var99_dollars = (risk_data["portfolio_metrics"]["value_at_risk_99"] / 100) * investment_amount
            risk_data["value_at_risk_interpretation"]["99%"] = f"1% chance of losing more than ${var99_dollars:.2f} in a day"

        logger.info(f"Successfully parsed risk analysis output")
        return risk_data

    except Exception as e:
        logger.error(f"Error parsing risk analysis output: {str(e)}")
        # Return default structure with error
        return {
            "portfolio_metrics": {
                "beta": 1.0,
                "sharpe_ratio": 0.0,
                "value_at_risk_95": 0.0,
                "value_at_risk_99": 0.0,
                "max_drawdown": 0.0,
                "annual_volatility": 15.0,
                "expected_annual_return": 8.0
            },
            "risk_contributions": {},
            "risk_alignment": {
                "user_profile": user_profile.get('risk_profile', 'moderate') if user_profile else 'moderate',
                "risk_score": 0.5,
                "portfolio_risk_level": "unknown",
                "expected_volatility_range": "N/A",
                "actual_volatility": "N/A",
                "adjustment_recommendation": None
            },
            "diversification_metrics": {
                "number_of_positions": 0,
                "effective_number_of_stocks": 0,
                "concentration_risk": "moderate"
            },
            "value_at_risk_interpretation": {
                "95%": "Unable to calculate",
                "99%": "Unable to calculate"
            },
            "error": str(e)
        }
