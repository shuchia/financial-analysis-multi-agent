"""
Analytics handlers for tracking events and generating insights.
"""

import json
from typing import Dict, Any
from datetime import datetime, timedelta

from utils.response import (
    success_response, error_response, unauthorized_response,
    server_error_response
)
from utils.database import db
from utils.auth import get_user_from_event


def track_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Track a custom analytics event."""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        event_type = body.get('event_type')
        event_data = body.get('event_data', {})
        user_id = body.get('user_id')  # Optional for anonymous events
        
        if not event_type:
            return error_response("Event type is required", 400)
        
        # Create event record
        event_record = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'event_data': event_data,
            'source': 'api'
        }
        
        # Save to database
        success = db.track_event(event_record)
        if not success:
            return server_error_response("Failed to track event")
        
        return success_response(
            message="Event tracked successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Track event error: {str(e)}")
        return server_error_response("Internal server error")


def get_analytics(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get analytics data (requires authentication)."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        # This would typically require admin access
        # For now, return user's own analytics
        user_id = user_info['user_id']
        
        # Get query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        event_type = query_params.get('event_type', 'user_action')
        days = int(query_params.get('days', 30))
        
        if days < 1 or days > 365:
            return error_response("Days parameter must be between 1 and 365", 400)
        
        # Calculate date range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Get analytics data
        analytics_data = db.get_analytics(
            event_type,
            start_time.isoformat(),
            end_time.isoformat()
        )
        
        # Filter for user's events only (unless admin)
        user_events = [
            event for event in analytics_data 
            if event.get('user_id') == user_id
        ]
        
        # Aggregate data by day
        daily_stats = {}
        for event_record in user_events:
            event_date = event_record['timestamp'][:10]  # YYYY-MM-DD
            if event_date not in daily_stats:
                daily_stats[event_date] = 0
            daily_stats[event_date] += 1
        
        return success_response(
            data={
                'event_type': event_type,
                'days': days,
                'total_events': len(user_events),
                'daily_stats': daily_stats,
                'events': user_events[:100]  # Limit to recent 100 events
            },
            message="Analytics data retrieved successfully"
        )
        
    except ValueError:
        return error_response("Days parameter must be a valid integer", 400)
    except Exception as e:
        print(f"Get analytics error: {str(e)}")
        return server_error_response("Internal server error")


# Helper functions for tracking specific events

def track_signup_event(user_id: str, plan: str, referral_source: str = None):
    """Track user signup event."""
    event_data = {
        'plan': plan,
        'referral_source': referral_source
    }
    
    event_record = {
        'event_type': 'signup',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_login_event(user_id: str):
    """Track user login event."""
    event_record = {
        'event_type': 'login',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': {},
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_user_update_event(user_id: str, updated_fields: list):
    """Track user profile update event."""
    event_data = {
        'updated_fields': updated_fields
    }
    
    event_record = {
        'event_type': 'user_update',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_user_deletion_event(user_id: str, plan: str):
    """Track user account deletion event."""
    event_data = {
        'plan': plan
    }
    
    event_record = {
        'event_type': 'user_deletion',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_plan_upgrade_event(user_id: str, from_plan: str, to_plan: str):
    """Track plan upgrade event."""
    event_data = {
        'from_plan': from_plan,
        'to_plan': to_plan
    }
    
    event_record = {
        'event_type': 'plan_upgrade',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_feature_usage_event(user_id: str, feature: str, count: int):
    """Track feature usage event."""
    event_data = {
        'feature': feature,
        'count': count
    }
    
    event_record = {
        'event_type': 'feature_usage',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_analysis_event(user_id: str, symbol: str, analysis_type: str, duration: float):
    """Track stock analysis event."""
    event_data = {
        'symbol': symbol,
        'analysis_type': analysis_type,
        'duration_seconds': duration
    }
    
    event_record = {
        'event_type': 'analysis',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_password_reset_event(user_id: str):
    """Track password reset event."""
    event_record = {
        'event_type': 'password_reset',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': {},
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_email_verification_event(user_id: str):
    """Track email verification event."""
    event_record = {
        'event_type': 'email_verification',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': {},
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_account_lockout_event(user_id: str, reason: str, attempts: int):
    """Track account lockout event."""
    event_data = {
        'reason': reason,
        'failed_attempts': attempts
    }
    
    event_record = {
        'event_type': 'account_lockout',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_failed_login_event(email: str, ip_address: str, attempts: int):
    """Track failed login attempt."""
    event_data = {
        'email': email,
        'ip_address': ip_address,
        'failed_attempts': attempts
    }
    
    event_record = {
        'event_type': 'failed_login',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': None,  # No user ID for failed attempts
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def get_dashboard_stats(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get dashboard statistics for admin users."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        # This would typically require admin access
        # For demo purposes, returning mock data
        
        # Get date range
        query_params = event.get('queryStringParameters', {}) or {}
        days = int(query_params.get('days', 7))
        
        # Calculate basic stats
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        # Mock dashboard data
        dashboard_data = {
            'period': f"Last {days} days",
            'total_users': 0,  # Would query actual user count
            'new_signups': 0,  # Would query signup events
            'total_analyses': 0,  # Would query analysis events
            'revenue': 0,  # Would calculate from subscriptions
            'popular_features': [],  # Would aggregate feature usage
            'conversion_rate': 0  # Would calculate from signups/visits
        }
        
        return success_response(
            data=dashboard_data,
            message="Dashboard statistics retrieved successfully"
        )
        
    except ValueError:
        return error_response("Days parameter must be a valid integer", 400)
    except Exception as e:
        print(f"Get dashboard stats error: {str(e)}")
        return server_error_response("Internal server error")


def increment_usage_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle usage increment requests."""
    try:
        # Get authenticated user
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        feature = body.get('feature')
        count = body.get('count', 1)
        
        if not feature:
            return error_response("Feature is required", 400)
        
        # Get current date
        current_date = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Increment usage
        success = db.increment_usage(user_id, current_date, feature, count)
        if not success:
            return server_error_response("Failed to increment usage")
        
        # Get updated usage
        usage_data = db.get_usage(user_id, current_date)
        
        return success_response(
            data={
                'user_id': user_id,
                'feature': feature,
                'count': count,
                'total_usage': usage_data
            },
            message="Usage incremented successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Increment usage error: {str(e)}")
        return server_error_response("Internal server error")


def check_usage_limit_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Check if user has reached usage limits."""
    try:
        # Get authenticated user
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        feature = body.get('feature')
        count = body.get('count', 1)
        
        if not feature:
            return error_response("Feature is required", 400)
        
        # Get user plan
        user_data = db.get_user(user_id)
        if not user_data:
            return error_response("User not found", 404)
        
        user_plan = user_data.get('plan', 'free')
        
        # Define limits per plan
        limits = {
            'free': {
                'analyses_count': 5,
                'api_calls': 100
            },
            'premium': {
                'analyses_count': 100,
                'api_calls': 1000
            },
            'professional': {
                'analyses_count': -1,  # unlimited
                'api_calls': -1
            }
        }
        
        plan_limits = limits.get(user_plan, limits['free'])
        feature_limit = plan_limits.get(feature, 0)
        
        # Get current usage
        current_date = datetime.utcnow().strftime('%Y-%m-%d')
        usage_data = db.get_usage(user_id, current_date)
        current_usage = usage_data.get(feature, 0)
        
        # Check if unlimited
        if feature_limit == -1:
            allowed = True
            remaining = -1
        else:
            allowed = (current_usage + count) <= feature_limit
            remaining = max(0, feature_limit - current_usage)
        
        return success_response(
            data={
                'allowed': allowed,
                'current_usage': current_usage,
                'limit': feature_limit,
                'remaining': remaining,
                'plan': user_plan,
                'feature': feature
            },
            message="Usage limit check completed"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Check usage limit error: {str(e)}")
        return server_error_response("Internal server error")


# Enhanced tracking functions for young investor features

def track_onboarding_completed_event(user_id: str, age_range: str, risk_profile: str, primary_goal: str):
    """Track onboarding completion event."""
    event_data = {
        'age_range': age_range,
        'risk_profile': risk_profile,
        'primary_goal': primary_goal,
        'completion_timestamp': datetime.utcnow().isoformat()
    }
    
    event_record = {
        'event_type': 'onboarding_completed',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_tutorial_started_event(user_id: str, tutorial_stock: str, age_range: str = None):
    """Track tutorial analysis started event."""
    event_data = {
        'tutorial_stock': tutorial_stock,
        'age_range': age_range
    }
    
    event_record = {
        'event_type': 'tutorial_analysis_started',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_achievement_unlock_event(user_id: str, achievement_id: str):
    """Track achievement unlock event."""
    event_data = {
        'achievement_id': achievement_id,
        'unlock_timestamp': datetime.utcnow().isoformat()
    }
    
    event_record = {
        'event_type': 'achievement_unlocked',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_preferences_update_event(user_id: str, preferences_data: dict):
    """Track preferences update event."""
    # Extract key metrics without storing sensitive data
    event_data = {
        'has_demographics': 'demographics' in preferences_data,
        'has_investment_goals': 'investment_goals' in preferences_data,
        'has_risk_assessment': 'risk_assessment' in preferences_data,
        'achievement_count': len(preferences_data.get('achievements', {}).get('unlocked', [])),
        'update_timestamp': datetime.utcnow().isoformat()
    }
    
    event_record = {
        'event_type': 'preferences_updated',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_personalized_suggestion_event(user_id: str, suggestions: dict, selected_stock: str = None):
    """Track personalized stock suggestion interaction."""
    event_data = {
        'suggestion_count': len(suggestions),
        'suggestions': list(suggestions.keys()),
        'selected_stock': selected_stock,
        'interaction_timestamp': datetime.utcnow().isoformat()
    }
    
    event_record = {
        'event_type': 'personalized_suggestion',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_tutorial_tab_view_event(user_id: str, tab_name: str, tutorial_stock: str):
    """Track tutorial tab viewing for educational analytics."""
    event_data = {
        'tab_name': tab_name,
        'tutorial_stock': tutorial_stock,
        'view_timestamp': datetime.utcnow().isoformat()
    }
    
    event_record = {
        'event_type': 'tutorial_tab_viewed',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_risk_scenario_response_event(user_id: str, scenario_responses: dict, risk_score: int, risk_profile: str):
    """Track risk assessment scenario responses."""
    event_data = {
        'scenario_count': len(scenario_responses),
        'risk_score': risk_score,
        'risk_profile': risk_profile,
        'assessment_timestamp': datetime.utcnow().isoformat()
    }
    
    event_record = {
        'event_type': 'risk_assessment_completed',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)


def track_beginner_interface_event(user_id: str, interface_type: str, action: str):
    """Track beginner interface usage."""
    event_data = {
        'interface_type': interface_type,  # 'tutorial', 'beginner', 'standard'
        'action': action,  # 'viewed', 'interacted', 'completed'
        'timestamp': datetime.utcnow().isoformat()
    }
    
    event_record = {
        'event_type': 'beginner_interface_interaction',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_data': event_data,
        'source': 'api'
    }
    
    db.track_event(event_record)