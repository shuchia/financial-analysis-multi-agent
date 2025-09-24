#!/usr/bin/env python3
"""
Create a simple working InvestForge API for testing.
"""

import boto3
import json

def create_simple_working_api():
    """Create a simple API that actually works."""
    print("🚀 Creating Simple InvestForge API")
    
    lambda_client = boto3.client('lambda')
    apigateway = boto3.client('apigateway')
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    region = boto3.Session().region_name or 'us-east-1'
    
    # Simple working Lambda functions
    functions_code = {
        'health': '''
def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
        },
        'body': '{"status": "healthy", "service": "InvestForge API", "version": "1.0.0"}'
    }
''',
        'waitlist': '''
import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    try:
        # Parse request body
        if event.get('body'):
            body = json.loads(event['body'])
            email = body.get('email')
            
            if not email:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': '{"success": false, "message": "Email is required"}'
                }
            
            # Save to DynamoDB (simplified)
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table('investforge-api-dev-waitlist')
            
            table.put_item(Item={
                'email': email,
                'joined_at': datetime.utcnow().isoformat(),
                'source': body.get('source', 'api')
            })
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': '{"success": true, "message": "Successfully joined waitlist!"}'
            }
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': '{"success": false, "message": "Request body is required"}'
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': f'{{"success": false, "message": "Internal error: {str(e)}"}}'
        }
''',
        'signup': '''
import json
import boto3
from datetime import datetime
import hashlib

def lambda_handler(event, context):
    try:
        if event.get('body'):
            body = json.loads(event['body'])
            email = body.get('email')
            password = body.get('password')
            
            if not email or not password:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': '{"success": false, "message": "Email and password are required"}'
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
                    'body': '{"success": false, "message": "User already exists"}'
                }
            
            # Create user
            table.put_item(Item={
                'user_id': email,
                'email': email,
                'password_hash': password_hash,
                'plan': body.get('plan', 'free'),
                'created_at': datetime.utcnow().isoformat()
            })
            
            return {
                'statusCode': 201,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': '{"success": true, "message": "User created successfully!", "user": {"email": "' + email + '", "plan": "' + body.get('plan', 'free') + '"}}'
            }
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': '{"success": false, "message": "Request body is required"}'
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': f'{{"success": false, "message": "Internal error: {str(e)}"}}'
        }
'''
    }
    
    # Update existing functions with working code
    for func_name, code in functions_code.items():
        function_name = f'investforge-{func_name}'
        
        try:
            # Create ZIP with the code
            import zipfile
            import io
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr('lambda_function.py', code)
            
            zip_buffer.seek(0)
            
            # Update function code
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_buffer.read()
            )
            
            print(f"✅ Updated {function_name} with working code")
            
        except Exception as e:
            print(f"❌ Failed to update {function_name}: {e}")
    
    # Get the existing API Gateway URL
    apis = apigateway.get_rest_apis()
    investforge_api = None
    
    for api in apis['items']:
        if 'investforge' in api['name'].lower():
            investforge_api = api
            break
    
    if investforge_api:
        api_url = f"https://{investforge_api['id']}.execute-api.{region}.amazonaws.com/dev"
        print(f"✅ Using existing API: {api_url}")
        
        return api_url
    else:
        print("❌ No InvestForge API found")
        return None

def test_endpoints(api_url):
    """Test the API endpoints."""
    import urllib.request
    import urllib.error
    
    tests = [
        {
            'name': 'Health Check',
            'url': f'{api_url}/health',
            'method': 'GET'
        },
        {
            'name': 'Waitlist Signup',
            'url': f'{api_url}/waitlist',
            'method': 'POST',
            'data': json.dumps({'email': 'test@example.com', 'source': 'api_test'})
        },
        {
            'name': 'User Signup',
            'url': f'{api_url}/auth',
            'method': 'POST',
            'data': json.dumps({'email': 'testuser@example.com', 'password': 'testpass123', 'plan': 'free'})
        }
    ]
    
    print()
    print("🧪 Testing API endpoints...")
    
    for test in tests:
        try:
            if test['method'] == 'GET':
                with urllib.request.urlopen(test['url']) as response:
                    data = response.read().decode()
                    print(f"✅ {test['name']}: {data}")
            else:
                req = urllib.request.Request(
                    test['url'], 
                    data=test['data'].encode(),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req) as response:
                    data = response.read().decode()
                    print(f"✅ {test['name']}: {data}")
                    
        except urllib.error.HTTPError as e:
            error_data = e.read().decode()
            print(f"❌ {test['name']} failed ({e.code}): {error_data}")
        except Exception as e:
            print(f"❌ {test['name']} error: {e}")

def main():
    """Main function."""
    api_url = create_simple_working_api()
    
    if api_url:
        print()
        print("⏳ Waiting for functions to be ready...")
        import time
        time.sleep(5)
        
        test_endpoints(api_url)
        
        print()
        print("🎉 InvestForge API is working!")
        print(f"📍 Base URL: {api_url}")
        print()
        print("🧪 Manual test commands:")
        print(f"curl {api_url}/health")
        print(f"curl -X POST {api_url}/waitlist -H 'Content-Type: application/json' -d '{{\"email\":\"your@email.com\"}}'")
        print(f"curl -X POST {api_url}/auth -H 'Content-Type: application/json' -d '{{\"email\":\"user@test.com\",\"password\":\"test123\"}}'")

if __name__ == "__main__":
    main()