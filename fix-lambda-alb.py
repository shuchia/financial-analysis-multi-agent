#!/usr/bin/env python3
"""
Fix Lambda functions to be ALB-compatible and update target groups.
"""

import boto3
import json
import zipfile
import io

def create_alb_compatible_lambda(function_name, handler_code):
    """Create ALB-compatible Lambda function."""
    lambda_client = boto3.client('lambda')
    
    # Create ZIP file with the code
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('lambda_function.py', handler_code)
    
    zip_buffer.seek(0)
    
    try:
        # Update function code
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_buffer.read()
        )
        print(f"✅ Updated {function_name}")
        return response['FunctionArn']
    except Exception as e:
        print(f"❌ Failed to update {function_name}: {e}")
        return None

def main():
    print("🔧 Fixing Lambda functions for ALB compatibility")
    print("=" * 50)
    
    # ALB-compatible health function
    health_code = '''
def lambda_handler(event, context):
    """ALB-compatible health check function."""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
        },
        'body': json.dumps({
            'status': 'healthy',
            'service': 'InvestForge API',
            'version': '1.0.0',
            'timestamp': context.aws_request_id if context else 'test'
        })
    }

import json
'''
    
    # ALB-compatible waitlist function
    waitlist_code = '''
import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """ALB-compatible waitlist function."""
    try:
        # Parse request body for ALB
        if event.get('body'):
            if event.get('isBase64Encoded'):
                import base64
                body = base64.b64decode(event['body']).decode('utf-8')
            else:
                body = event['body']
            data = json.loads(body)
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Request body is required'})
            }
        
        email = data.get('email')
        if not email:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Email is required'})
            }
        
        # Save to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('investforge-api-dev-waitlist')
        
        table.put_item(Item={
            'email': email,
            'joined_at': datetime.utcnow().isoformat(),
            'source': data.get('source', 'alb')
        })
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'success': True, 'message': 'Successfully joined waitlist!'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'success': False, 'message': f'Internal error: {str(e)}'})
        }
'''
    
    # ALB-compatible signup function
    signup_code = '''
import json
import boto3
import hashlib
from datetime import datetime

def lambda_handler(event, context):
    """ALB-compatible signup function."""
    try:
        # Parse request body for ALB
        if event.get('body'):
            if event.get('isBase64Encoded'):
                import base64
                body = base64.b64decode(event['body']).decode('utf-8')
            else:
                body = event['body']
            data = json.loads(body)
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Request body is required'})
            }
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Email and password are required'})
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
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'User already exists'})
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
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True, 
                'message': 'User created successfully!', 
                'user': {'email': email, 'plan': data.get('plan', 'free')}
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'success': False, 'message': f'Internal error: {str(e)}'})
        }
'''
    
    # ALB-compatible analytics function
    analytics_code = '''
import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """ALB-compatible analytics function."""
    try:
        # Parse request body for ALB
        if event.get('body'):
            if event.get('isBase64Encoded'):
                import base64
                body = base64.b64decode(event['body']).decode('utf-8')
            else:
                body = event['body']
            data = json.loads(body)
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'success': False, 'message': 'Request body is required'})
            }
        
        event_type = data.get('event_type', 'unknown')
        user_id = data.get('user_id', 'anonymous')
        
        # Save to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('investforge-api-dev-analytics')
        
        table.put_item(Item={
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'data': data
        })
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'success': True, 'message': 'Event tracked successfully!'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'success': False, 'message': f'Internal error: {str(e)}'})
        }
'''
    
    # Update functions
    functions = [
        ('investforge-health', health_code),
        ('investforge-waitlist', waitlist_code), 
        ('investforge-signup', signup_code),
        ('investforge-analytics', analytics_code)
    ]
    
    updated_functions = {}
    for func_name, code in functions:
        arn = create_alb_compatible_lambda(func_name, code)
        if arn:
            updated_functions[func_name] = arn
    
    print(f"\n✅ Updated {len(updated_functions)} functions")
    
    # Now update target group registrations
    elbv2 = boto3.client('elbv2')
    lambda_client = boto3.client('lambda')
    
    target_groups = {
        'health': 'arn:aws:elasticloadbalancing:us-east-1:453636587892:targetgroup/investforge-lambda-health/909f6a46660a5b8c',
        'auth': 'arn:aws:elasticloadbalancing:us-east-1:453636587892:targetgroup/investforge-lambda-auth/ad837b7610155f0e',
        'waitlist': 'arn:aws:elasticloadbalancing:us-east-1:453636587892:targetgroup/investforge-lambda-waitlist/6a61022d918832f9',
        'analytics': 'arn:aws:elasticloadbalancing:us-east-1:453636587892:targetgroup/investforge-lambda-analytics/7cd0eb61a2c09a96'
    }
    
    function_mapping = {
        'health': 'investforge-health',
        'auth': 'investforge-signup',
        'waitlist': 'investforge-waitlist',
        'analytics': 'investforge-analytics'
    }
    
    print("\n🔗 Updating target group registrations...")
    
    for tg_name, tg_arn in target_groups.items():
        func_name = function_mapping[tg_name]
        
        if func_name in updated_functions:
            func_arn = updated_functions[func_name]
            
            try:
                # Add permission
                lambda_client.add_permission(
                    FunctionName=func_name,
                    StatementId=f'alb-{tg_name}-fixed-{int(datetime.now().timestamp())}',
                    Action='lambda:InvokeFunction',
                    Principal='elasticloadbalancing.amazonaws.com',
                    SourceArn=tg_arn
                )
                print(f"✅ Added permission for {func_name}")
            except Exception as e:
                print(f"⚠️  Permission for {func_name}: {e}")
    
    print("\n🎉 Lambda functions updated for ALB compatibility!")
    print("\n🧪 Test endpoints after 30 seconds:")
    print("curl https://investforge.io/api/health")
    print("curl -X POST https://investforge.io/api/waitlist/join -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\"}'")

if __name__ == "__main__":
    main()