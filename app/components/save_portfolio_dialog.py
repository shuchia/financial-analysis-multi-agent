"""
Save Portfolio Dialog Component

Provides a modal dialog for saving portfolio snapshots to the backend.
"""

import streamlit as st
import requests
import os
from datetime import datetime
from typing import Dict, Any, Optional


def _generate_default_name(portfolio_data: Dict[str, Any]) -> str:
    """Generate a default portfolio name from portfolio data."""
    try:
        # Try to get from user preferences
        preferences = portfolio_data.get('user_profile', {})
        risk = preferences.get('risk_profile', 'balanced').title()
        goals = preferences.get('investment_goals', [])

        if goals and len(goals) > 0:
            primary_goal = goals[0].replace('_', ' ').title()
        else:
            primary_goal = 'Portfolio'

        year = datetime.now().year
        return f"{risk} {primary_goal} {year}"
    except Exception:
        return f"My Portfolio {datetime.now().strftime('%Y-%m-%d')}"


def _call_save_portfolio_api(
    portfolio_data: Dict[str, Any],
    portfolio_name: str,
    tags: list,
    notes: str,
    user_id: str
) -> tuple[bool, str, Optional[Dict]]:
    """
    Call the backend API to save the portfolio.

    Returns:
        tuple: (success: bool, message: str, response_data: Dict or None)
    """
    try:
        # Get API base URL from environment
        api_base_url = os.environ.get('API_BASE_URL', 'https://api.investforge.ai')
        endpoint = f"{api_base_url}/api/portfolio/save"

        # Prepare request payload
        payload = {
            'user_id': user_id,
            'name': portfolio_name,
            'preferences': portfolio_data.get('user_profile', {}),
            'allocations': portfolio_data.get('allocations', []),
            'tags': tags,
            'notes': notes
        }

        # Add optional fields if present
        if 'risk_metrics' in portfolio_data:
            payload['risk_metrics'] = portfolio_data['risk_metrics']

        if 'optimization_results' in portfolio_data:
            payload['optimization_results'] = portfolio_data['optimization_results']

        # Make API request
        response = requests.post(
            endpoint,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return True, data.get('message', 'Portfolio saved successfully'), data.get('data')
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('message', f'Server returned status {response.status_code}')
            return False, error_msg, None

    except requests.exceptions.Timeout:
        return False, 'Request timed out. Please try again.', None
    except requests.exceptions.ConnectionError:
        return False, 'Could not connect to server. Please check your connection.', None
    except Exception as e:
        return False, f'Unexpected error: {str(e)}', None


@st.dialog("Save Portfolio", width="large")
def show_save_portfolio_dialog(portfolio_data: Dict[str, Any], user_id: str = "demo@investforge.ai"):
    """
    Display a dialog for saving the current portfolio.

    Args:
        portfolio_data: The structured portfolio data to save
        user_id: User identifier (default demo user for now)
    """

    # Generate default name
    default_name = _generate_default_name(portfolio_data)

    st.markdown("### Portfolio Details")
    st.markdown("Save this portfolio configuration for future reference.")

    # Portfolio name input
    portfolio_name = st.text_input(
        "Portfolio Name",
        value=default_name,
        help="Give your portfolio a memorable name",
        placeholder="e.g., Aggressive Growth 2024"
    )

    # Tags input (comma-separated)
    tags_input = st.text_input(
        "Tags (optional)",
        value="",
        help="Add tags to organize your portfolios (comma-separated)",
        placeholder="e.g., growth, tech-heavy, long-term"
    )

    # Parse tags
    tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []

    # Notes textarea
    notes = st.text_area(
        "Notes (optional)",
        value="",
        help="Add any notes or context about this portfolio",
        placeholder="e.g., Created for retirement planning with 20-year horizon",
        height=100
    )

    # Portfolio summary
    st.markdown("---")
    st.markdown("### Portfolio Summary")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Total Holdings",
            len(portfolio_data.get('allocations', []))
        )

        investment_amount = portfolio_data.get('investment_amount', 0)
        st.metric(
            "Investment Amount",
            f"${investment_amount:,.2f}"
        )

    with col2:
        expected_return = portfolio_data.get('expected_return', 'N/A')
        st.metric(
            "Expected Return",
            expected_return
        )

        risk_profile = portfolio_data.get('user_profile', {}).get('risk_profile', 'N/A')
        st.metric(
            "Risk Profile",
            risk_profile.title()
        )

    # Top holdings preview
    st.markdown("**Top Holdings:**")
    allocations = portfolio_data.get('allocations', [])[:3]  # Show top 3
    for alloc in allocations:
        ticker = alloc.get('ticker', 'N/A')
        percentage = alloc.get('percentage', 0)
        st.markdown(f"- **{ticker}**: {percentage:.1f}%")

    if len(portfolio_data.get('allocations', [])) > 3:
        st.markdown(f"*...and {len(portfolio_data.get('allocations', [])) - 3} more*")

    st.markdown("---")

    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

    with col3:
        if st.button("Save Portfolio", type="primary", use_container_width=True):
            # Validate
            if not portfolio_name or portfolio_name.strip() == "":
                st.error("Please enter a portfolio name")
                return

            if not portfolio_data.get('allocations'):
                st.error("No portfolio allocations to save")
                return

            # Show loading state
            with st.spinner("Saving portfolio..."):
                success, message, response_data = _call_save_portfolio_api(
                    portfolio_data=portfolio_data,
                    portfolio_name=portfolio_name.strip(),
                    tags=tags,
                    notes=notes.strip(),
                    user_id=user_id
                )

            if success:
                st.success(f"✅ {message}")

                # Store the saved portfolio info in session state for reference
                if response_data:
                    st.session_state['last_saved_portfolio'] = {
                        'portfolio_id': response_data.get('portfolio_id'),
                        'name': response_data.get('name'),
                        'saved_at': datetime.now().isoformat()
                    }

                # Small delay to show success message
                import time
                time.sleep(1.5)
                st.rerun()
            else:
                st.error(f"❌ Failed to save portfolio: {message}")


def render_save_button(portfolio_data: Optional[Dict[str, Any]] = None):
    """
    Render a save portfolio button that triggers the dialog.

    Args:
        portfolio_data: The portfolio data to save. If None, uses session_state['structured_portfolio']
    """
    # Get portfolio data from session state if not provided
    if portfolio_data is None:
        portfolio_data = st.session_state.get('structured_portfolio')

    # Don't show button if no portfolio data exists
    if not portfolio_data or not portfolio_data.get('allocations'):
        return

    # Show last saved indicator if exists
    last_saved = st.session_state.get('last_saved_portfolio')
    if last_saved:
        saved_time = datetime.fromisoformat(last_saved['saved_at'])
        time_diff = datetime.now() - saved_time

        if time_diff.total_seconds() < 300:  # Show for 5 minutes
            st.success(f"✅ Saved as '{last_saved['name']}'", icon="✓")

    # Render save button
    if st.button("💾 Save Portfolio", use_container_width=False, help="Save this portfolio for future reference"):
        show_save_portfolio_dialog(portfolio_data)
