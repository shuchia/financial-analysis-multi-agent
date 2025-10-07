"""
Lambda function for user preferences management.
Handles GET and POST operations for user preferences.
"""

import json
import os
import logging
from datetime import datetime
import boto3
from decimal import Decimal

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')

def decimal_default(obj):
    """JSON encoder for Decimal types."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """
    Lambda handler for user preferences.
    Supports both GET and POST operations.
    """
    try:
        # CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        }
        
        # Handle preflight requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body']) if event['body'] else {}
        else:
            body = event.get('body', {})
        
        logger.info(f"Request body: {json.dumps(body)}")
        
        # Extract email
        email = body.get('email', '').strip().lower()
        
        if not email:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Email is required'
                })
            }
        
        # Connect to DynamoDB
        table_name = os.environ.get('DYNAMODB_TABLE_USERS', 'investforge-users-simple')
        table = dynamodb.Table(table_name)
        
        # Get user by email
        try:
            response = table.get_item(Key={'email': email})
            user = response.get('Item')
            
            if not user:
                return {
                    'statusCode': 404,
                    'headers': headers,
                    'body': json.dumps({
                        'success': False,
                        'message': 'User not found'
                    })
                }
                
        except Exception as e:
            logger.error(f"Error retrieving user: {str(e)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Database error'
                })
            }
        
        # Determine action based on method or explicit action parameter
        http_method = event.get('httpMethod', 'GET')
        action = body.get('action', 'save' if http_method == 'POST' else 'get')
        
        if action == 'get' or http_method == 'GET':
            # Get preferences
            preferences = user.get('preferences', {})
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'success': True,
                    'data': preferences,
                    'message': 'Preferences retrieved successfully'
                }, default=decimal_default)
            }
            
        else:
            # Save/update preferences
            preferences = body.get('preferences', {})
            
            if not isinstance(preferences, dict):
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'success': False,
                        'message': 'Preferences must be an object'
                    })
                }
            
            # Update user preferences
            try:
                # Convert all float values to Decimal recursively
                def convert_floats_to_decimal(obj):
                    if isinstance(obj, float):
                        return Decimal(str(obj))
                    elif isinstance(obj, dict):
                        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_floats_to_decimal(v) for v in obj]
                    return obj
                
                # Convert all floats in preferences to Decimal
                preferences = convert_floats_to_decimal(preferences)
                
                table.update_item(
                    Key={'email': email},
                    UpdateExpression='SET preferences = :preferences, updated_at = :updated_at',
                    ExpressionAttributeValues={
                        ':preferences': preferences,
                        ':updated_at': datetime.utcnow().isoformat()
                    }
                )
                
                logger.info(f"Updated preferences for user: {email}")
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'success': True,
                        'data': preferences,
                        'message': 'Preferences saved successfully'
                    }, default=decimal_default)
                }
                
            except Exception as e:
                logger.error(f"Error updating preferences: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        'success': False,
                        'message': 'Failed to update preferences'
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
        logger.error(f"Preferences handler error: {str(e)}")
        logger.error(f"Event: {json.dumps(event)}")
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