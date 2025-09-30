"""
DynamoDB database utilities.
"""

import os
import boto3
from typing import Dict, Any, Optional, List
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime


class DatabaseClient:
    """DynamoDB client wrapper."""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.stage = os.getenv('STAGE', 'dev')
        self.service_name = 'investforge-api'
        
        # Table references - use environment variables if available, fallback to actual table names
        self.users_table = self.dynamodb.Table(
            os.getenv('DYNAMODB_TABLE_USERS', 'investforge-users-simple')
        )
        self.usage_table = self.dynamodb.Table(
            os.getenv('DYNAMODB_TABLE_USAGE', 'investforge-usage')
        )
        self.analytics_table = self.dynamodb.Table(
            os.getenv('DYNAMODB_TABLE_ANALYTICS', 'investforge-analytics')
        )
        self.waitlist_table = self.dynamodb.Table(
            os.getenv('DYNAMODB_TABLE_WAITLIST', f'{self.service_name}-{self.stage}-waitlist')
        )
        self.password_resets_table = self.dynamodb.Table(
            os.getenv('DYNAMODB_TABLE_PASSWORD_RESETS', f'{self.service_name}-{self.stage}-password-resets')
        )
    
    # User operations
    def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Create a new user."""
        try:
            self.users_table.put_item(
                Item=user_data,
                ConditionExpression='attribute_not_exists(user_id)'
            )
            return True
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            return False
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            response = self.users_table.get_item(Key={'user_id': user_id})
            return response.get('Item')
        except Exception:
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            response = self.users_table.query(
                IndexName='EmailIndex',
                KeyConditionExpression=Key('email').eq(email)
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except Exception:
            return None
    
    def get_user_by_google_id(self, google_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Google ID."""
        try:
            response = self.users_table.scan(
                FilterExpression=Attr('google_id').eq(google_id)
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except Exception:
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by user ID (alias for get_user)."""
        return self.get_user(user_id)
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user data."""
        try:
            # Build update expression
            update_expression = "SET "
            expression_values = {}
            
            for key, value in updates.items():
                update_expression += f"{key} = :{key}, "
                expression_values[f":{key}"] = value
            
            update_expression = update_expression.rstrip(", ")
            
            self.users_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            return True
        except Exception:
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        try:
            self.users_table.delete_item(Key={'user_id': user_id})
            return True
        except Exception:
            return False
    
    # Usage operations
    def get_usage(self, user_id: str, date: str) -> Dict[str, Any]:
        """Get usage data for a user on a specific date."""
        try:
            response = self.usage_table.query(
                KeyConditionExpression=Key('user_id').eq(user_id) & Key('date_feature').begins_with(date)
            )
            
            usage_data = {}
            for item in response.get('Items', []):
                feature = item['date_feature'].split('#')[1]
                usage_data[feature] = item.get('count', 0)
            
            return usage_data
        except Exception:
            return {}
    
    def increment_usage(self, user_id: str, date: str, feature: str, increment: int = 1) -> bool:
        """Increment usage count for a feature."""
        try:
            date_feature = f"{date}#{feature}"
            
            self.usage_table.update_item(
                Key={'user_id': user_id, 'date_feature': date_feature},
                UpdateExpression='ADD #count :increment',
                ExpressionAttributeNames={'#count': 'count'},
                ExpressionAttributeValues={':increment': increment}
            )
            return True
        except Exception:
            return False
    
    # Analytics operations
    def track_event(self, event_data: Dict[str, Any]) -> bool:
        """Track an analytics event."""
        try:
            self.analytics_table.put_item(Item=event_data)
            return True
        except Exception:
            return False
    
    def get_analytics(
        self, 
        event_type: str, 
        start_time: str, 
        end_time: str
    ) -> List[Dict[str, Any]]:
        """Get analytics events for a time range."""
        try:
            response = self.analytics_table.query(
                KeyConditionExpression=Key('event_type').eq(event_type) & 
                                     Key('timestamp').between(start_time, end_time)
            )
            return response.get('Items', [])
        except Exception:
            return []
    
    # Password reset operations
    def create_password_reset(self, reset_data: Dict[str, Any]) -> bool:
        """Create a password reset token."""
        try:
            self.password_resets_table.put_item(Item=reset_data)
            return True
        except Exception:
            return False
    
    def get_password_reset(self, reset_token: str) -> Optional[Dict[str, Any]]:
        """Get password reset data by token."""
        try:
            response = self.password_resets_table.get_item(
                Key={'reset_token': reset_token}
            )
            return response.get('Item')
        except Exception:
            return None
    
    def update_password_reset(self, reset_token: str, updates: Dict[str, Any]) -> bool:
        """Update password reset data."""
        try:
            update_expression = "SET "
            expression_values = {}
            
            for key, value in updates.items():
                update_expression += f"{key} = :{key}, "
                expression_values[f":{key}"] = value
            
            update_expression = update_expression.rstrip(", ")
            
            self.password_resets_table.update_item(
                Key={'reset_token': reset_token},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            return True
        except Exception:
            return False
    
    def delete_password_reset(self, reset_token: str) -> bool:
        """Delete a password reset token."""
        try:
            self.password_resets_table.delete_item(
                Key={'reset_token': reset_token}
            )
            return True
        except Exception:
            return False
    
    # Waitlist operations
    def add_to_waitlist(self, email: str, data: Dict[str, Any]) -> bool:
        """Add email to waitlist."""
        try:
            waitlist_data = {
                'email': email,
                'timestamp': data.get('timestamp'),
                'source': data.get('source', 'unknown'),
                'metadata': data.get('metadata', {})
            }
            
            self.waitlist_table.put_item(
                Item=waitlist_data,
                ConditionExpression='attribute_not_exists(email)'
            )
            return True
        except Exception:
            return False
    
    def get_waitlist_entry(self, email: str) -> Optional[Dict[str, Any]]:
        """Get waitlist entry by email."""
        try:
            response = self.waitlist_table.get_item(Key={'email': email})
            return response.get('Item')
        except Exception:
            return None
    
    def remove_from_waitlist(self, email: str) -> bool:
        """Remove email from waitlist."""
        try:
            self.waitlist_table.delete_item(Key={'email': email})
            return True
        except Exception:
            return False
    
    # Enhanced user preferences operations
    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences."""
        user = self.get_user(user_id)
        if user:
            return user.get('preferences', {})
        return None
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences."""
        return self.update_user(user_id, {'preferences': preferences})
    
    def get_preferences_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user preferences by email."""
        user = self.get_user_by_email(email)
        if user:
            return user.get('preferences', {})
        return None
    
    def update_preferences_by_email(self, email: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences by email."""
        user = self.get_user_by_email(email)
        if user:
            return self.update_user(user['user_id'], {'preferences': preferences})
        return False
    
    # Achievement operations
    def get_user_achievements(self, user_id: str) -> Dict[str, Any]:
        """Get user achievements."""
        preferences = self.get_user_preferences(user_id)
        if preferences:
            return preferences.get('achievements', {'unlocked': [], 'progress': {}})
        return {'unlocked': [], 'progress': {}}
    
    def unlock_achievement(self, user_id: str, achievement_id: str) -> bool:
        """Unlock an achievement for a user."""
        preferences = self.get_user_preferences(user_id) or {}
        achievements = preferences.get('achievements', {'unlocked': [], 'progress': {}})
        
        if achievement_id not in achievements['unlocked']:
            achievements['unlocked'].append(achievement_id)
            achievements['progress'][achievement_id] = {
                'unlocked_at': datetime.utcnow().isoformat()
            }
            
            preferences['achievements'] = achievements
            return self.update_user_preferences(user_id, preferences)
        
        return True  # Already unlocked
    
    def update_achievement_progress(self, user_id: str, achievement_id: str, progress_data: Dict[str, Any]) -> bool:
        """Update progress for an achievement."""
        preferences = self.get_user_preferences(user_id) or {}
        achievements = preferences.get('achievements', {'unlocked': [], 'progress': {}})
        
        if achievement_id not in achievements['progress']:
            achievements['progress'][achievement_id] = {}
        
        achievements['progress'][achievement_id].update(progress_data)
        preferences['achievements'] = achievements
        
        return self.update_user_preferences(user_id, preferences)
    
    # Analytics operations for onboarding metrics
    def get_onboarding_analytics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get onboarding completion analytics."""
        try:
            # Get onboarding completion events
            completion_events = self.get_analytics('onboarding_completed', start_date, end_date)
            tutorial_events = self.get_analytics('tutorial_analysis_started', start_date, end_date)
            achievement_events = self.get_analytics('achievement_unlocked', start_date, end_date)
            
            # Calculate metrics
            total_completions = len(completion_events)
            
            # Age distribution
            age_distribution = {}
            for event in completion_events:
                age_range = event.get('event_data', {}).get('age_range', 'Unknown')
                age_distribution[age_range] = age_distribution.get(age_range, 0) + 1
            
            # Risk profile distribution
            risk_distribution = {}
            for event in completion_events:
                risk_profile = event.get('event_data', {}).get('risk_profile', 'Unknown')
                risk_distribution[risk_profile] = risk_distribution.get(risk_profile, 0) + 1
            
            # Tutorial completion rate
            tutorial_starts = len(tutorial_events)
            tutorial_completion_rate = (tutorial_starts / total_completions * 100) if total_completions > 0 else 0
            
            return {
                'total_completions': total_completions,
                'tutorial_starts': tutorial_starts,
                'tutorial_completion_rate': tutorial_completion_rate,
                'age_distribution': age_distribution,
                'risk_distribution': risk_distribution,
                'achievement_unlocks': len(achievement_events)
            }
        except Exception:
            return {}
    
    def get_user_onboarding_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get onboarding metrics for a specific user."""
        try:
            # Get user events
            response = self.analytics_table.scan(
                FilterExpression=Attr('user_id').eq(user_id)
            )
            
            events = response.get('Items', [])
            
            # Extract onboarding-related events
            onboarding_events = [e for e in events if e.get('event_type') in [
                'onboarding_completed', 'tutorial_analysis_started', 'achievement_unlocked'
            ]]
            
            # Calculate completion time if available
            onboarding_complete = next((e for e in onboarding_events if e.get('event_type') == 'onboarding_completed'), None)
            tutorial_start = next((e for e in onboarding_events if e.get('event_type') == 'tutorial_analysis_started'), None)
            
            completion_time = None
            if onboarding_complete and tutorial_start:
                # Calculate time between onboarding completion and first tutorial
                onboarding_time = datetime.fromisoformat(onboarding_complete['timestamp'])
                tutorial_time = datetime.fromisoformat(tutorial_start['timestamp'])
                completion_time = (tutorial_time - onboarding_time).total_seconds() / 60  # minutes
            
            return {
                'onboarding_completed': onboarding_complete is not None,
                'tutorial_started': tutorial_start is not None,
                'completion_time_minutes': completion_time,
                'total_events': len(onboarding_events)
            }
        except Exception:
            return {}
    
    # Waitlist operations (removing duplicate)
    def add_to_waitlist(self, waitlist_data: Dict[str, Any]) -> bool:
        """Add email to waitlist."""
        try:
            self.waitlist_table.put_item(
                Item=waitlist_data,
                ConditionExpression='attribute_not_exists(email)'
            )
            return True
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            return False
    
    def get_waitlist_entry(self, email: str) -> Optional[Dict[str, Any]]:
        """Get waitlist entry by email."""
        try:
            response = self.waitlist_table.get_item(Key={'email': email})
            return response.get('Item')
        except Exception:
            return None


# Global database client instance
db = DatabaseClient()