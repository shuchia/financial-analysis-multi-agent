"""
Lambda function for user signup with enhanced authentication.
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
    Lambda handler for user signup.
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
        first_name = body.get('first_name', '')
        last_name = body.get('last_name', '')
        plan = body.get('plan', 'free')
        
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
        
        # Email format validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Invalid email format'
                })
            }
        
        # Password complexity validation
        def validate_password(password):
            if len(password) < 8:
                return False, "Password must be at least 8 characters long"
            if not any(c.isupper() for c in password):
                return False, "Password must contain at least one uppercase letter"
            if not any(c.islower() for c in password):
                return False, "Password must contain at least one lowercase letter"
            if not any(c.isdigit() for c in password):
                return False, "Password must contain at least one number"
            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                return False, "Password must contain at least one special character"
            return True, None
        
        is_valid, password_error = validate_password(password)
        if not is_valid:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': password_error
                })
            }
        
        # Hash password (simple implementation for Lambda)
        import hashlib
        import secrets
        
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        stored_password = salt + password_hash.hex()
        
        # Create user data
        import uuid
        user_id = str(uuid.uuid4())
        
        user_data = {
            'user_id': user_id,
            'email': email,
            'password_hash': stored_password,
            'first_name': first_name,
            'last_name': last_name,
            'plan': plan,
            'status': 'active',
            'email_verified': False,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Store in DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ.get('DYNAMODB_TABLE_USERS', 'investforge-users-simple')
        table = dynamodb.Table(table_name)
        
        # Check if user exists (email is the primary key)
        try:
            response = table.get_item(Key={'email': email})
            existing_user = response.get('Item')
            
            if existing_user:
                return {
                    'statusCode': 409,
                    'headers': headers,
                    'body': json.dumps({
                        'success': False,
                        'message': 'User with this email already exists'
                    })
                }
        except Exception as e:
            logger.error(f"Error checking existing user: {str(e)}")
        
        # Create user
        try:
            table.put_item(
                Item=user_data,
                ConditionExpression='attribute_not_exists(email)'
            )
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Failed to create user account'
                })
            }
        
        # Create simple JWT token (for demo purposes)
        import base64
        
        token_payload = {
            'user_id': user_id,
            'email': email,
            'plan': plan,
            'exp': int((datetime.utcnow().timestamp() + 86400) * 1000),  # 24 hours
            'type': 'access'
        }
        
        token_data = base64.b64encode(json.dumps(token_payload).encode()).decode()
        access_token = f"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.{token_data}.demo_signature"
        
        # Track signup event
        try:
            analytics_table_name = os.environ.get('DYNAMODB_TABLE_ANALYTICS', 'investforge-analytics')
            analytics_table = dynamodb.Table(analytics_table_name)
            
            event_data = {
                'event_id': str(uuid.uuid4()),
                'event_type': 'signup',
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'event_data': {
                    'plan': plan,
                    'method': 'email'
                },
                'source': 'lambda'
            }
            
            analytics_table.put_item(Item=event_data)
        except Exception as e:
            logger.warning(f"Failed to track signup event: {str(e)}")
        
        # Return success response
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'Account created successfully',
                'data': {
                    'user': {
                        'user_id': user_id,
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'plan': plan
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
        logger.error(f"Signup error: {str(e)}")
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