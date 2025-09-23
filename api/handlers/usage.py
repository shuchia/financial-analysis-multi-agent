"""
Usage tracking handlers for monitoring feature usage and limits.
"""

import json
from typing import Dict, Any
from datetime import datetime, timedelta

from utils.response import (
    success_response, error_response, unauthorized_response,
    not_found_response, server_error_response, forbidden_response
)
from utils.database import db
from utils.auth import get_user_from_event
from models.user import User


def get_usage(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get user's usage statistics."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        period = query_params.get('period', 'current_month')
        
        # Calculate date range based on period
        now = datetime.now()
        if period == 'current_month':
            date = now.strftime('%Y-%m')
        elif period == 'last_month':
            last_month = now.replace(day=1) - timedelta(days=1)
            date = last_month.strftime('%Y-%m')
        elif period == 'current_year':
            date = now.strftime('%Y')
        else:
            # Custom date provided
            date = period
        
        # Get usage data from database
        usage_data = db.get_usage(user_id, date)
        
        # Get user data for plan limits
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        limits = user.get_plan_limits()
        
        # Calculate usage percentages
        usage_with_percentages = {}
        for feature, count in usage_data.items():
            limit = limits.get(f"{feature}_per_month", -1)
            if limit == -1:  # Unlimited
                percentage = 0
            else:
                percentage = (count / limit) * 100 if limit > 0 else 0
            
            usage_with_percentages[feature] = {
                'count': count,
                'limit': limit,
                'percentage': min(percentage, 100)
            }
        
        return success_response(
            data={
                'period': period,
                'date': date,
                'plan': user.plan,
                'usage': usage_with_percentages,
                'limits': limits
            },
            message="Usage statistics retrieved successfully"
        )
        
    except Exception as e:
        print(f"Get usage error: {str(e)}")
        return server_error_response("Internal server error")


def increment_usage(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Increment usage count for a specific feature."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get feature from path parameters
        path_params = event.get('pathParameters', {}) or {}
        feature = path_params.get('feature')
        
        if not feature:
            return error_response("Feature parameter is required", 400)
        
        # Parse request body for increment amount
        body = json.loads(event.get('body', '{}'))
        increment = body.get('increment', 1)
        
        if not isinstance(increment, int) or increment < 1:
            return error_response("Increment must be a positive integer", 400)
        
        # Get user data for plan limits
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        limits = user.get_plan_limits()
        
        # Check if feature usage is allowed
        current_date = datetime.now().strftime('%Y-%m')
        current_usage = db.get_usage(user_id, current_date)
        
        feature_count = current_usage.get(feature, 0)
        feature_limit = limits.get(f"{feature}_per_month", -1)
        
        # Check if user has reached the limit
        if feature_limit != -1 and feature_count + increment > feature_limit:
            return forbidden_response(
                f"Usage limit exceeded for {feature}. "
                f"Current: {feature_count}, Limit: {feature_limit}"
            )
        
        # Increment usage
        success = db.increment_usage(user_id, current_date, feature, increment)
        if not success:
            return server_error_response("Failed to increment usage")
        
        # Get updated usage
        new_count = feature_count + increment
        
        # Track the usage event
        from handlers.analytics import track_feature_usage_event
        track_feature_usage_event(user_id, feature, increment)
        
        return success_response(
            data={
                'feature': feature,
                'new_count': new_count,
                'limit': feature_limit,
                'remaining': feature_limit - new_count if feature_limit != -1 else -1
            },
            message=f"Usage incremented for {feature}"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Increment usage error: {str(e)}")
        return server_error_response("Internal server error")


def check_usage_limit(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Check if user can perform a specific action based on usage limits."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        feature = query_params.get('feature')
        required_count = int(query_params.get('count', 1))
        
        if not feature:
            return error_response("Feature parameter is required", 400)
        
        # Get user data for plan limits
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        limits = user.get_plan_limits()
        
        # Check current usage
        current_date = datetime.now().strftime('%Y-%m')
        current_usage = db.get_usage(user_id, current_date)
        
        feature_count = current_usage.get(feature, 0)
        feature_limit = limits.get(f"{feature}_per_month", -1)
        
        # Check if action is allowed
        if feature_limit == -1:  # Unlimited
            allowed = True
            remaining = -1
        else:
            allowed = feature_count + required_count <= feature_limit
            remaining = max(0, feature_limit - feature_count)
        
        return success_response(
            data={
                'feature': feature,
                'current_count': feature_count,
                'limit': feature_limit,
                'required_count': required_count,
                'allowed': allowed,
                'remaining': remaining
            },
            message="Usage limit check completed"
        )
        
    except ValueError:
        return error_response("Count parameter must be a valid integer", 400)
    except Exception as e:
        print(f"Check usage limit error: {str(e)}")
        return server_error_response("Internal server error")


def get_usage_history(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get user's usage history over multiple periods."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        months = int(query_params.get('months', 6))  # Default to 6 months
        feature = query_params.get('feature')  # Optional feature filter
        
        if months < 1 or months > 24:
            return error_response("Months parameter must be between 1 and 24", 400)
        
        # Calculate date range
        now = datetime.now()
        history = []
        
        for i in range(months):
            month_date = now.replace(day=1) - timedelta(days=i * 30)
            month_str = month_date.strftime('%Y-%m')
            
            usage_data = db.get_usage(user_id, month_str)
            
            if feature:
                # Filter for specific feature
                month_data = {
                    'month': month_str,
                    'usage': {feature: usage_data.get(feature, 0)}
                }
            else:
                # All features
                month_data = {
                    'month': month_str,
                    'usage': usage_data
                }
            
            history.append(month_data)
        
        # Reverse to get chronological order
        history.reverse()
        
        return success_response(
            data={
                'months': months,
                'feature_filter': feature,
                'history': history
            },
            message="Usage history retrieved successfully"
        )
        
    except ValueError:
        return error_response("Months parameter must be a valid integer", 400)
    except Exception as e:
        print(f"Get usage history error: {str(e)}")
        return server_error_response("Internal server error")


def reset_usage(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Reset usage for a specific feature (admin only)."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        # This would typically check for admin role
        # For now, we'll skip this implementation
        return error_response("Admin access required", 403)
        
    except Exception as e:
        print(f"Reset usage error: {str(e)}")
        return server_error_response("Internal server error")