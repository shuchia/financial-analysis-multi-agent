"""
User management handlers for profile operations.
"""

import json
from typing import Dict, Any
from datetime import datetime
from pydantic import ValidationError

from utils.response import (
    success_response, error_response, validation_error_response,
    unauthorized_response, not_found_response, server_error_response
)
from utils.database import db
from utils.auth import get_user_from_event
from models.user import User, UserUpdate


def get_user(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get current user profile."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get user data from database
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        
        return success_response(
            data=user.to_public_dict(),
            message="User profile retrieved successfully"
        )
        
    except Exception as e:
        print(f"Get user error: {str(e)}")
        return server_error_response("Internal server error")


def update_user(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Update current user profile."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate input
        try:
            update_data = UserUpdate(**body)
        except ValidationError as e:
            return validation_error_response(e.errors())
        
        # Get current user data
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        
        # Prepare updates
        updates = {}
        if update_data.first_name is not None:
            updates['first_name'] = update_data.first_name
        if update_data.last_name is not None:
            updates['last_name'] = update_data.last_name
        if update_data.plan is not None:
            # Note: In production, plan changes should go through payment flow
            updates['plan'] = update_data.plan
        if update_data.preferences is not None:
            updates['preferences'] = update_data.preferences
        
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        # Update user in database
        success = db.update_user(user_id, updates)
        if not success:
            return server_error_response("Failed to update user")
        
        # Update user object and return
        user.update_fields(updates)
        
        # Track update event
        from handlers.analytics import track_user_update_event
        track_user_update_event(user_id, list(updates.keys()))
        
        return success_response(
            data=user.to_public_dict(),
            message="User profile updated successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Update user error: {str(e)}")
        return server_error_response("Internal server error")


def delete_user(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Delete current user account."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get user data to ensure it exists
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        
        # In production, you might want to:
        # 1. Cancel any active subscriptions
        # 2. Delete associated data
        # 3. Send confirmation email
        # 4. Implement a grace period before actual deletion
        
        # Delete user from database
        success = db.delete_user(user_id)
        if not success:
            return server_error_response("Failed to delete user")
        
        # Track deletion event
        from handlers.analytics import track_user_deletion_event
        track_user_deletion_event(user_id, user.plan)
        
        return success_response(
            message="User account deleted successfully"
        )
        
    except Exception as e:
        print(f"Delete user error: {str(e)}")
        return server_error_response("Internal server error")


def get_user_preferences(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get user preferences."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get user data from database
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        
        return success_response(
            data=user.preferences,
            message="User preferences retrieved successfully"
        )
        
    except Exception as e:
        print(f"Get preferences error: {str(e)}")
        return server_error_response("Internal server error")


def update_user_preferences(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Update user preferences."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        preferences = body.get('preferences', {})
        
        if not isinstance(preferences, dict):
            return error_response("Preferences must be an object", 400)
        
        # Get current user data
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        
        # Merge with existing preferences
        current_preferences = user.preferences or {}
        current_preferences.update(preferences)
        
        # Update user in database
        updates = {
            'preferences': current_preferences,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        success = db.update_user(user_id, updates)
        if not success:
            return server_error_response("Failed to update preferences")
        
        return success_response(
            data=current_preferences,
            message="Preferences updated successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Update preferences error: {str(e)}")
        return server_error_response("Internal server error")


def get_user_plan_limits(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get user's plan limits and current usage."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get user data from database
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        
        # Get plan limits
        limits = user.get_plan_limits()
        
        # Get current usage (this month)
        from datetime import datetime
        current_month = datetime.now().strftime('%Y-%m')
        usage = db.get_usage(user_id, current_month)
        
        return success_response(
            data={
                "plan": user.plan,
                "limits": limits,
                "current_usage": usage
            },
            message="Plan limits retrieved successfully"
        )
        
    except Exception as e:
        print(f"Get plan limits error: {str(e)}")
        return server_error_response("Internal server error")