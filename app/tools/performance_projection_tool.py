from crewai.tools import tool
import numpy as np
from typing import Dict


def _calculate_projections_impl(
    investment_amount: float,
    expected_annual_return: float,
    timeline_years: int,
    annual_volatility: float = 0.15
) -> Dict:
    """
    Internal implementation of portfolio projection calculations.
    This is the non-decorated version that can be called directly.
    """
    try:
        # Calculate number of months
        months = timeline_years * 12

        # Convert annual returns to monthly
        monthly_return = (1 + expected_annual_return) ** (1/12) - 1

        # Calculate three scenarios using standard deviation
        # Conservative: 1 standard deviation below expected
        conservative_return = expected_annual_return - annual_volatility
        conservative_monthly = (1 + conservative_return) ** (1/12) - 1
        conservative_values = [investment_amount * ((1 + conservative_monthly) ** month)
                              for month in range(months + 1)]

        # Expected scenario: use the provided expected return
        expected_values = [investment_amount * ((1 + monthly_return) ** month)
                          for month in range(months + 1)]

        # Optimistic: 1 standard deviation above expected
        optimistic_return = expected_annual_return + annual_volatility
        optimistic_monthly = (1 + optimistic_return) ** (1/12) - 1
        optimistic_values = [investment_amount * ((1 + optimistic_monthly) ** month)
                            for month in range(months + 1)]

        # Build results dictionary
        scenarios = {
            'conservative': {
                'values': conservative_values,
                'final_value': conservative_values[-1],
                'total_return_pct': ((conservative_values[-1] - investment_amount) / investment_amount) * 100,
                'annual_return': conservative_return
            },
            'expected': {
                'values': expected_values,
                'final_value': expected_values[-1],
                'total_return_pct': ((expected_values[-1] - investment_amount) / investment_amount) * 100,
                'annual_return': expected_annual_return
            },
            'optimistic': {
                'values': optimistic_values,
                'final_value': optimistic_values[-1],
                'total_return_pct': ((optimistic_values[-1] - investment_amount) / investment_amount) * 100,
                'annual_return': optimistic_return
            }
        }

        return {
            'timeline_years': timeline_years,
            'timeline_months': months,
            'initial_investment': investment_amount,
            'expected_annual_return': expected_annual_return,
            'annual_volatility': annual_volatility,
            'scenarios': scenarios,
            'summary': {
                'conservative_final_value': f"${scenarios['conservative']['final_value']:,.2f}",
                'conservative_final_value_raw': round(scenarios['conservative']['final_value'], 2),
                'conservative_total_return': f"{scenarios['conservative']['total_return_pct']:.1f}%",
                'expected_final_value': f"${scenarios['expected']['final_value']:,.2f}",
                'expected_final_value_raw': round(scenarios['expected']['final_value'], 2),
                'expected_total_return': f"{scenarios['expected']['total_return_pct']:.1f}%",
                'optimistic_final_value': f"${scenarios['optimistic']['final_value']:,.2f}",
                'optimistic_final_value_raw': round(scenarios['optimistic']['final_value'], 2),
                'optimistic_total_return': f"{scenarios['optimistic']['total_return_pct']:.1f}%"
            }
        }

    except Exception as e:
        return {
            'error': f'Failed to calculate projections: {str(e)}',
            'suggestion': 'Please verify input parameters are valid numbers'
        }


@tool
def calculate_portfolio_projections(
    investment_amount: float,
    expected_annual_return: float,
    timeline_years: int,
    annual_volatility: float = 0.15
) -> Dict:
    """
    Calculate portfolio performance projections over a given timeline with three scenarios.

    Args:
        investment_amount (float): Initial investment amount in dollars
        expected_annual_return (float): Expected annual return as decimal (e.g., 0.08 for 8%)
        timeline_years (int): Investment timeline in years
        annual_volatility (float): Expected annual volatility as decimal (e.g., 0.15 for 15%)

    Returns:
        dict: Dictionary with projection scenarios including conservative, expected, and optimistic outcomes
    """
    return _calculate_projections_impl(
        investment_amount=investment_amount,
        expected_annual_return=expected_annual_return,
        timeline_years=timeline_years,
        annual_volatility=annual_volatility
    )


# Legacy class wrapper for backward compatibility
class PerformanceProjectionTool:
    """Legacy wrapper for the performance projection tool."""

    def __init__(self):
        self.name = "calculate_portfolio_projections"
        self.description = "Calculate portfolio performance projections over time"

    def _run(self, *args, **kwargs):
        return calculate_portfolio_projections(*args, **kwargs)
