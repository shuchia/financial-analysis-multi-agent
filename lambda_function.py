"""
Lambda function for user login with enhanced authentication.
Compatible with existing Lambda infrastructure.
"""

import json
import os
import logging
from datetime import datetime
import boto3

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda handler for user login.
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
        
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract required fields
        email = body.get('email', '').strip().lower()
        password = body.get('password', '')
        
        # Basic validation
        if not email or not password:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Email and password are required'
                })
            }
        
        # Connect to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ.get('DYNAMODB_TABLE_USERS', 'investforge-users-simple')
        table = dynamodb.Table(table_name)
        
        # Get user by email (email is the primary key)
        try:
            response = table.get_item(Key={'email': email})
            user = response.get('Item')
            
            if not user:
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({
                        'success': False,
                        'message': 'Invalid email or password'
                    })
                }
            
        except Exception as e:
            logger.error(f"Error retrieving user: {str(e)}")
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Invalid email or password'
                })
            }
        
        # Check account status
        if user.get('status') != 'active':
            return {
                'statusCode': 403,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Account is suspended or inactive'
                })
            }
        
        # Verify password
        def verify_password(password, stored_password):
            try:
                import hashlib
                
                salt = stored_password[:32]  # First 32 chars are salt
                stored_hash = stored_password[32:]  # Rest is hash
                
                password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
                return password_hash.hex() == stored_hash
            except:
                return False
        
        if not verify_password(password, user.get('password_hash', '')):
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Invalid email or password'
                })
            }
        
        # Update last login
        try:
            table.update_item(
                Key={'email': user['email']},
                UpdateExpression='SET last_login = :login_time, updated_at = :updated_at',
                ExpressionAttributeValues={
                    ':login_time': datetime.utcnow().isoformat(),
                    ':updated_at': datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update last login: {str(e)}")
        
        # Create simple JWT token
        import base64
        import uuid
        
        token_payload = {
            'user_id': user['user_id'],
            'email': user['email'],
            'plan': user.get('plan', 'free'),
            'exp': int((datetime.utcnow().timestamp() + 86400) * 1000),  # 24 hours
            'type': 'access'
        }
        
        token_data = base64.b64encode(json.dumps(token_payload).encode()).decode()
        access_token = f"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.{token_data}.demo_signature"
        
        # Track login event
        try:
            analytics_table_name = os.environ.get('DYNAMODB_TABLE_ANALYTICS', 'investforge-analytics')
            analytics_table = dynamodb.Table(analytics_table_name)
            
            event_data = {
                'event_id': str(uuid.uuid4()),
                'event_type': 'login',
                'user_id': user['user_id'],
                'timestamp': datetime.utcnow().isoformat(),
                'event_data': {
                    'method': 'email'
                },
                'source': 'lambda'
            }
            
            analytics_table.put_item(Item=event_data)
        except Exception as e:
            logger.warning(f"Failed to track login event: {str(e)}")
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'Login successful',
                'data': {
                    'user': {
                        'user_id': user['user_id'],
                        'email': user['email'],
                        'first_name': user.get('first_name', ''),
                        'last_name': user.get('last_name', ''),
                        'plan': user.get('plan', 'free'),
                        'email_verified': user.get('email_verified', False)
                    },
                    'access_token': access_token,
                    'token_type': 'Bearer'
                }
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
        logger.error(f"Login error: {str(e)}")
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