"""
Enhanced user preferences handlers with support for young investor features.
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
from models.preferences import (
    EnhancedUserPreferences, PreferencesUpdate, LegacyPreferences,
    migrate_legacy_preferences, get_achievement_definitions
)


def get_enhanced_preferences(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get enhanced user preferences."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get user preferences from database
        preferences_data = db.get_user_preferences(user_id)
        if not preferences_data:
            return success_response(
                data={},
                message="No preferences found"
            )
        
        # Check if we have enhanced preferences or legacy format
        if 'demographics' in preferences_data and 'investment_goals' in preferences_data:
            # Already enhanced format
            return success_response(
                data=preferences_data,
                message="Enhanced preferences retrieved successfully"
            )
        else:
            # Legacy format - migrate on the fly
            try:
                enhanced_prefs = migrate_legacy_preferences(preferences_data)
                # Save migrated preferences back to database
                db.update_user_preferences(user_id, enhanced_prefs.dict())
                
                return success_response(
                    data=enhanced_prefs.dict(),
                    message="Preferences migrated and retrieved successfully"
                )
            except Exception as e:
                print(f"Migration error: {str(e)}")
                return success_response(
                    data=preferences_data,
                    message="Legacy preferences retrieved (migration failed)"
                )
        
    except Exception as e:
        print(f"Get enhanced preferences error: {str(e)}")
        return server_error_response("Internal server error")


def update_enhanced_preferences(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Update enhanced user preferences."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Check if this is a complete enhanced preferences object or partial update
        if 'demographics' in body and 'investment_goals' in body:
            # Complete enhanced preferences
            try:
                enhanced_prefs = EnhancedUserPreferences(**body)
                preferences_dict = enhanced_prefs.dict()
            except ValidationError as e:
                return validation_error_response(e.errors())
        else:
            # Partial update or legacy format
            # Get existing preferences first
            current_prefs = db.get_user_preferences(user_id) or {}
            
            # If current prefs are legacy, migrate first
            if current_prefs and 'demographics' not in current_prefs:
                try:
                    enhanced_prefs = migrate_legacy_preferences(current_prefs)
                    current_prefs = enhanced_prefs.dict()
                except:
                    current_prefs = {}
            
            # Apply partial updates
            try:
                if 'preferences' in body:
                    # Handle API client format
                    update_data = PreferencesUpdate(**body['preferences'])
                else:
                    # Direct format
                    update_data = PreferencesUpdate(**body)
                
                # Merge updates with current preferences
                update_dict = update_data.dict(exclude_unset=True)
                for key, value in update_dict.items():
                    if value is not None:
                        current_prefs[key] = value
                
                # Update timestamp
                current_prefs['last_updated'] = datetime.utcnow().isoformat()
                preferences_dict = current_prefs
                
            except ValidationError as e:
                return validation_error_response(e.errors())
        
        # Save to database
        success = db.update_user_preferences(user_id, preferences_dict)
        if not success:
            return server_error_response("Failed to update preferences")
        
        # Track preferences update event
        from handlers.analytics import track_preferences_update_event
        track_preferences_update_event(user_id, preferences_dict)
        
        return success_response(
            data=preferences_dict,
            message="Enhanced preferences updated successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Update enhanced preferences error: {str(e)}")
        return server_error_response("Internal server error")


def get_user_achievements(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get user achievements and progress."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get achievements from database
        achievements_data = db.get_user_achievements(user_id)
        
        # Get achievement definitions
        achievement_defs = get_achievement_definitions()
        
        # Combine with definitions for full context
        enhanced_achievements = {
            'unlocked': achievements_data.get('unlocked', []),
            'progress': achievements_data.get('progress', {}),
            'available': {aid: {
                'name': ach.name,
                'description': ach.description,
                'unlocked': aid in achievements_data.get('unlocked', [])
            } for aid, ach in achievement_defs.items()}
        }
        
        return success_response(
            data=enhanced_achievements,
            message="User achievements retrieved successfully"
        )
        
    except Exception as e:
        print(f"Get achievements error: {str(e)}")
        return server_error_response("Internal server error")


def unlock_achievement(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Unlock an achievement for a user."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        achievement_id = body.get('achievement_id')
        
        if not achievement_id:
            return error_response("Achievement ID is required", 400)
        
        # Validate achievement exists
        achievement_defs = get_achievement_definitions()
        if achievement_id not in achievement_defs:
            return error_response("Invalid achievement ID", 400)
        
        # Unlock achievement
        success = db.unlock_achievement(user_id, achievement_id)
        if not success:
            return server_error_response("Failed to unlock achievement")
        
        # Track achievement unlock event
        from handlers.analytics import track_achievement_unlock_event
        track_achievement_unlock_event(user_id, achievement_id)
        
        achievement_def = achievement_defs[achievement_id]
        
        return success_response(
            data={
                'achievement_id': achievement_id,
                'name': achievement_def.name,
                'description': achievement_def.description,
                'unlocked_at': datetime.utcnow().isoformat()
            },
            message=f"Achievement '{achievement_def.name}' unlocked!"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Unlock achievement error: {str(e)}")
        return server_error_response("Internal server error")


def update_achievement_progress(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Update progress for an achievement."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        achievement_id = body.get('achievement_id')
        progress_data = body.get('progress_data', {})
        
        if not achievement_id:
            return error_response("Achievement ID is required", 400)
        
        # Validate achievement exists
        achievement_defs = get_achievement_definitions()
        if achievement_id not in achievement_defs:
            return error_response("Invalid achievement ID", 400)
        
        # Update progress
        success = db.update_achievement_progress(user_id, achievement_id, progress_data)
        if not success:
            return server_error_response("Failed to update achievement progress")
        
        return success_response(
            data={
                'achievement_id': achievement_id,
                'progress_data': progress_data
            },
            message="Achievement progress updated successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Update achievement progress error: {str(e)}")
        return server_error_response("Internal server error")


def get_onboarding_analytics(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get onboarding analytics (admin only)."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        # Check if user is admin (implement your admin check logic)
        user_id = user_info['user_id']
        user_data = db.get_user(user_id)
        if not user_data or user_data.get('plan') != 'admin':  # Adjust admin check as needed
            return unauthorized_response("Admin access required")
        
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        start_date = query_params.get('start_date', '2024-01-01')
        end_date = query_params.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Get analytics data
        analytics_data = db.get_onboarding_analytics(start_date, end_date)
        
        return success_response(
            data=analytics_data,
            message="Onboarding analytics retrieved successfully"
        )
        
    except Exception as e:
        print(f"Get onboarding analytics error: {str(e)}")
        return server_error_response("Internal server error")


def get_user_onboarding_metrics(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get onboarding metrics for current user."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get user onboarding metrics
        metrics_data = db.get_user_onboarding_metrics(user_id)
        
        return success_response(
            data=metrics_data,
            message="User onboarding metrics retrieved successfully"
        )
        
    except Exception as e:
        print(f"Get user onboarding metrics error: {str(e)}")
        return server_error_response("Internal server error")


# Legacy compatibility endpoint
def handle_legacy_preferences(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle legacy preferences API calls for backward compatibility."""
    try:
        # Parse the request
        body = json.loads(event.get('body', '{}'))
        action = body.get('action', 'get')
        email = body.get('email')
        
        if not email:
            return error_response("Email is required", 400)
        
        if action == 'get':
            # Get preferences by email (legacy API client method)
            preferences_data = db.get_preferences_by_email(email)
            return success_response(
                data=preferences_data or {},
                message="Preferences retrieved successfully"
            )
        
        elif action == 'update' or 'preferences' in body:
            # Update preferences by email
            preferences = body.get('preferences', {})
            
            # Check if this is enhanced or legacy format
            if 'demographics' in preferences:
                # Enhanced format
                try:
                    enhanced_prefs = EnhancedUserPreferences(**preferences)
                    preferences_dict = enhanced_prefs.dict()
                except ValidationError as e:
                    return validation_error_response(e.errors())
            else:
                # Legacy format - store as-is for now
                preferences_dict = preferences
                preferences_dict['timestamp'] = datetime.utcnow().isoformat()
            
            success = db.update_preferences_by_email(email, preferences_dict)
            if not success:
                return server_error_response("Failed to update preferences")
            
            return success_response(
                data=preferences_dict,
                message="Preferences updated successfully"
            )
        
        else:
            return error_response("Invalid action", 400)
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Legacy preferences error: {str(e)}")
        return server_error_response("Internal server error")