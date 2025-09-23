"""
Application constants and configuration.
"""

import os

# Subscription Plans
PLANS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'analyses_limit': 5,
        'backtests_limit': 2,
        'portfolio_optimizations_limit': 1,
        'features': [
            'Basic stock analysis',
            'Technical indicators',
            'Fundamental metrics',
            'Community support'
        ]
    },
    'growth': {
        'name': 'Growth',
        'price': 4.99,
        'analyses_limit': -1,  # Unlimited
        'backtests_limit': -1,
        'portfolio_optimizations_limit': -1,
        'features': [
            'Everything in Free',
            'Unlimited analyses',
            'Portfolio optimization',
            'Strategy backtesting',
            'Risk simulations',
            'Priority support'
        ]
    },
    'pro': {
        'name': 'Pro',
        'price': 9.99,
        'analyses_limit': -1,
        'backtests_limit': -1,
        'portfolio_optimizations_limit': -1,
        'features': [
            'Everything in Growth',
            'Advanced AI insights',
            'Custom indicators',
            'API access',
            'White-label reports',
            'Dedicated support'
        ]
    }
}

# Usage Limits
USAGE_LIMITS = {
    'free': {
        'analyses_per_month': 5,
        'backtests_per_month': 2,
        'portfolio_optimizations_per_month': 1,
        'api_calls_per_day': 0
    },
    'growth': {
        'analyses_per_month': -1,  # Unlimited
        'backtests_per_month': -1,
        'portfolio_optimizations_per_month': -1,
        'api_calls_per_day': 100
    },
    'pro': {
        'analyses_per_month': -1,
        'backtests_per_month': -1,
        'portfolio_optimizations_per_month': -1,
        'api_calls_per_day': 1000
    }
}

# Redis Keys
REDIS_KEYS = {
    'session': 'session:{}',
    'user': 'user:{}',
    'usage': 'usage:{}:{}',  # user_id, feature
    'waitlist': 'waitlist:{}',
    'analytics': 'analytics:{}:{}'  # event_type, date
}

# API Endpoints
API_BASE_URL = os.getenv('API_BASE_URL', 'https://investforge.io/api')
if 'localhost' in API_BASE_URL or not API_BASE_URL.startswith('http'):
    API_BASE_URL = 'http://localhost:8080/api'

API_ENDPOINTS = {
    'auth': f'{API_BASE_URL}/auth',
    'users': f'{API_BASE_URL}/users',
    'waitlist': f'{API_BASE_URL}/waitlist',
    'stripe': f'{API_BASE_URL}/stripe',
    'analytics': f'{API_BASE_URL}/analytics'
}

# Feature Flags
FEATURE_FLAGS = {
    'portfolio_optimization': True,
    'backtesting': True,
    'api_access': True,
    'social_login': True,
    'magic_links': True,
    'referral_system': False  # Coming soon
}

# UI Configuration
UI_CONFIG = {
    'theme': {
        'primary_color': '#FF6B35',
        'secondary_color': '#004E89',
        'success_color': '#28a745',
        'warning_color': '#ffc107',
        'error_color': '#dc3545'
    },
    'sidebar_width': 300,
    'max_chart_height': 600,
    'default_chart_height': 400
}

# Analysis Configuration
ANALYSIS_CONFIG = {
    'default_period': '1y',
    'available_periods': ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y'],
    'technical_indicators': [
        'SMA', 'EMA', 'RSI', 'MACD', 'Bollinger Bands',
        'Stochastic', 'Williams %R', 'CCI', 'ADX'
    ],
    'fundamental_metrics': [
        'P/E Ratio', 'P/B Ratio', 'PEG Ratio', 'EPS', 'Revenue Growth',
        'Debt to Equity', 'ROE', 'ROA', 'Profit Margin'
    ]
}

# Error Messages
ERROR_MESSAGES = {
    'auth_required': '🔒 Please log in to access this feature.',
    'plan_upgrade_required': '🚀 This feature requires a plan upgrade.',
    'usage_limit_reached': '📊 You\'ve reached your usage limit for this month.',
    'invalid_symbol': '❌ Invalid stock symbol. Please try again.',
    'api_error': '🔧 Service temporarily unavailable. Please try again.',
    'session_expired': '⏰ Your session has expired. Please log in again.'
}

# Success Messages
SUCCESS_MESSAGES = {
    'login_success': '✅ Successfully logged in!',
    'signup_success': '🎉 Account created successfully!',
    'analysis_complete': '📊 Analysis completed successfully!',
    'upgrade_success': '🚀 Plan upgraded successfully!'
}