"""
DynamoDB database utilities.
"""

import os
import boto3
from typing import Dict, Any, Optional, List
from boto3.dynamodb.conditions import Key, Attr


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
    
    # Waitlist operations
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