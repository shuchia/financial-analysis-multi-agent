#!/usr/bin/env python3
"""
Fix Lambda functions to properly handle ALB events.
ALB events have a different format than API Gateway events.
"""

import boto3
import json
import zipfile
import io

def create_alb_lambda_handler(function_name, handler_code):
    """Update Lambda function with proper ALB event handler."""
    lambda_client = boto3.client('lambda')
    
    # Create ZIP file with the code
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('lambda_function.py', handler_code)
    
    zip_buffer.seek(0)
    
    try:
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_buffer.read()
        )
        print(f"✅ Updated {function_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to update {function_name}: {e}")
        return False

def main():
    print("🔧 Fixing Lambda Functions for ALB Event Handling")
    print("=" * 55)
    
    # ALB-compatible health function
    health_code = '''
import json

def lambda_handler(event, context):
    """ALB-compatible health check function."""
    
    # ALB events have different structure than API Gateway
    print(f"Event: {json.dumps(event)}")
    
    # For ALB, we need to return this exact format
    response = {
        'statusCode': 200,
        'statusDescription': '200 OK',
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS,PUT,DELETE'
        },
        'body': json.dumps({
            'status': 'healthy',
            'service': 'InvestForge API',
            'version': '1.0.0',
            'timestamp': context.aws_request_id,
            'message': 'Health check successful via ALB'
        }),
        'isBase64Encoded': False
    }
    
    return response
'''
    
    # ALB-compatible waitlist function
    waitlist_code = '''
import json
import boto3
from datetime import datetime
import base64

def lambda_handler(event, context):
    """ALB-compatible waitlist function."""
    
    try:
        print(f"Event: {json.dumps(event)}")
        
        # Parse request body for ALB events
        body = event.get('body', '')
        
        # Handle base64 encoded body
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body).decode('utf-8')
        
        if not body:
            return {
                'statusCode': 400,
                'statusDescription': '400 Bad Request',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Request body is required'}),
                'isBase64Encoded': False
            }
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'statusDescription': '400 Bad Request',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Invalid JSON'}),
                'isBase64Encoded': False
            }
        
        email = data.get('email')
        if not email:
            return {
                'statusCode': 400,
                'statusDescription': '400 Bad Request',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Email is required'}),
                'isBase64Encoded': False
            }
        
        # Save to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('investforge-api-dev-waitlist')
        
        table.put_item(Item={
            'email': email,
            'joined_at': datetime.utcnow().isoformat(),
            'source': data.get('source', 'alb'),
            'user_agent': event.get('headers', {}).get('user-agent', 'unknown')
        })
        
        return {
            'statusCode': 200,
            'statusDescription': '200 OK',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True, 
                'message': 'Successfully joined waitlist!',
                'email': email
            }),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'statusDescription': '500 Internal Server Error',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False, 
                'message': f'Internal error: {str(e)}'
            }),
            'isBase64Encoded': False
        }
'''
    
    # ALB-compatible signup function
    signup_code = '''
import json
import boto3
import hashlib
from datetime import datetime
import base64

def lambda_handler(event, context):
    """ALB-compatible signup function."""
    
    try:
        print(f"Event: {json.dumps(event)}")
        
        # Parse request body for ALB events
        body = event.get('body', '')
        
        # Handle base64 encoded body
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body).decode('utf-8')
        
        if not body:
            return {
                'statusCode': 400,
                'statusDescription': '400 Bad Request',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Request body is required'}),
                'isBase64Encoded': False
            }
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'statusDescription': '400 Bad Request',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Invalid JSON'}),
                'isBase64Encoded': False
            }
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return {
                'statusCode': 400,
                'statusDescription': '400 Bad Request',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Email and password are required'}),
                'isBase64Encoded': False
            }
        
        # Simple password hash
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Save to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('investforge-api-dev-users')
        
        # Check if user exists
        response = table.get_item(Key={'user_id': email})
        if 'Item' in response:
            return {
                'statusCode': 409,
                'statusDescription': '409 Conflict',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'User already exists'}),
                'isBase64Encoded': False
            }
        
        # Create user
        table.put_item(Item={
            'user_id': email,
            'email': email,
            'password_hash': password_hash,
            'plan': data.get('plan', 'free'),
            'created_at': datetime.utcnow().isoformat()
        })
        
        return {
            'statusCode': 201,
            'statusDescription': '201 Created',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True, 
                'message': 'User created successfully!', 
                'user': {
                    'email': email, 
                    'plan': data.get('plan', 'free')
                }
            }),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'statusDescription': '500 Internal Server Error',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False, 
                'message': f'Internal error: {str(e)}'
            }),
            'isBase64Encoded': False
        }
'''
    
    # ALB-compatible analytics function
    analytics_code = '''
import json
import boto3
from datetime import datetime
import base64
import uuid

def lambda_handler(event, context):
    """ALB-compatible analytics function."""
    
    try:
        print(f"Event: {json.dumps(event)}")
        
        # Parse request body for ALB events
        body = event.get('body', '')
        
        # Handle base64 encoded body
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body).decode('utf-8')
        
        if not body:
            return {
                'statusCode': 400,
                'statusDescription': '400 Bad Request',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Request body is required'}),
                'isBase64Encoded': False
            }
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'statusDescription': '400 Bad Request',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Invalid JSON'}),
                'isBase64Encoded': False
            }
        
        event_type = data.get('event_type', 'unknown')
        user_id = data.get('user_id', 'anonymous')
        
        # Save to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('investforge-analytics')
        
        table.put_item(Item={
            'event_id': str(uuid.uuid4()),
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'data': data,
            'source': 'alb'
        })
        
        return {
            'statusCode': 200,
            'statusDescription': '200 OK',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True, 
                'message': 'Event tracked successfully!',
                'event_type': event_type
            }),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'statusDescription': '500 Internal Server Error',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False, 
                'message': f'Internal error: {str(e)}'
            }),
            'isBase64Encoded': False
        }
'''
    
    # Update all functions
    functions_to_update = [
        ('investforge-health', health_code),
        ('investforge-waitlist', waitlist_code),
        ('investforge-signup', signup_code),
        ('investforge-analytics', analytics_code)
    ]
    
    success_count = 0
    for func_name, code in functions_to_update:
        if create_alb_lambda_handler(func_name, code):
            success_count += 1
    
    print(f"\n✅ Successfully updated {success_count}/{len(functions_to_update)} functions")
    
    if success_count == len(functions_to_update):
        print("\n🎉 All Lambda functions updated for ALB compatibility!")
        print("\n⏳ Wait 30 seconds for functions to be ready, then test:")
        print("curl https://investforge.io/api/health")
        print("curl -X POST https://investforge.io/api/waitlist/join -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\"}'")
    else:
        print(f"\n⚠️  {len(functions_to_update) - success_count} functions failed to update")

if __name__ == "__main__":
    main()