"""
Lambda function for analytics tracking.
Simplified wrapper for the handlers/analytics.py track_event function.
Compatible with existing Lambda infrastructure.
"""

import json
import os
import logging
from datetime import datetime
import boto3
import uuid

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda handler for analytics tracking.
    Implements the core logic from handlers/analytics.py track_event function
    """
    try:
        # CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        }
        
        # Handle preflight requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Parse request body (matching handlers/analytics.py logic)
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract required fields (matching track_event logic)
        event_type = body.get('event_type')
        event_data = body.get('event_data', {})
        user_id = body.get('user_id')  # Optional for anonymous events
        
        if not event_type:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Event type is required'
                })
            }
        
        # Connect to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ.get('DYNAMODB_TABLE_ANALYTICS', 'investforge-analytics')
        table = dynamodb.Table(table_name)
        
        # Create event record (matching handlers/analytics.py format)
        event_record = {
            'event_id': str(uuid.uuid4()),
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'event_data': event_data,
            'source': 'api'
        }
        
        # Store in DynamoDB
        try:
            table.put_item(Item=event_record)
            logger.info(f"Analytics event tracked: {event_type} for user {user_id}")
        except Exception as e:
            logger.error(f"Error storing analytics: {str(e)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Failed to track event'
                })
            }
        
        # Return success response (matching handlers/analytics.py format)
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'Event tracked successfully'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Internal server error'
            })
        }