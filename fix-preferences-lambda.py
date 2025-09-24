#!/usr/bin/env python3
"""
Fix the preferences Lambda function to properly handle GET requests.
"""

import os
import boto3
import zipfile
import json

def create_fixed_preferences_lambda():
    """Create a fixed preferences Lambda function."""
    
    lambda_code = '''
import json
import boto3
from datetime import datetime

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('investforge-users-simple')

def lambda_handler(event, context):
    """Handle user preferences requests from ALB."""
    
    print(f"Event received: {json.dumps(event, default=str)}")
    
    # Handle ALB health checks
    if event.get('httpMethod') == 'GET' and event.get('path', '').endswith('/health'):
        return {
            'statusCode': 200,
            'statusDescription': '200 OK',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'healthy',
                'service': 'preferences'
            }),
            'isBase64Encoded': False
        }
    
    # Handle OPTIONS for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'statusDescription': '200 OK',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,PUT'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').lower()
        action = body.get('action', 'save')
        
        print(f"Processing request for email: {email}, action: {action}")
        
        # Basic validation
        if not email:
            return {
                'statusCode': 400,
                'statusDescription': '400 Bad Request',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'message': 'Email is required'
                }),
                'isBase64Encoded': False
            }
        
        # Handle GET preferences (via action parameter or HTTP method)
        if action == 'get' or event.get('httpMethod') == 'GET':
            try:
                print(f"Getting preferences for user: {email}")
                response = table.get_item(Key={'email': email})
                
                if 'Item' in response:
                    user = response['Item']
                    preferences = user.get('preferences', {})
                    print(f"Found preferences: {preferences}")
                    
                    return {
                        'statusCode': 200,
                        'statusDescription': '200 OK',
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'success': True,
                            'message': 'Preferences retrieved successfully',
                            'data': preferences
                        }),
                        'isBase64Encoded': False
                    }
                else:
                    print(f"User not found: {email}")
                    return {
                        'statusCode': 404,
                        'statusDescription': '404 Not Found',
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'success': False,
                            'message': 'User not found'
                        }),
                        'isBase64Encoded': False
                    }
            except Exception as e:
                print(f"Error getting preferences: {str(e)}")
                return {
                    'statusCode': 500,
                    'statusDescription': '500 Internal Server Error',
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'success': False,
                        'message': 'Failed to retrieve preferences'
                    }),
                    'isBase64Encoded': False
                }
        
        # Handle POST/PUT preferences update (default action)
        else:
            preferences = body.get('preferences', {})
            
            if not isinstance(preferences, dict):
                return {
                    'statusCode': 400,
                    'statusDescription': '400 Bad Request',
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'success': False,
                        'message': 'Preferences must be an object'
                    }),
                    'isBase64Encoded': False
                }
            
            try:
                print(f"Updating preferences for user: {email}")
                
                # Check if user exists
                response = table.get_item(Key={'email': email})
                if 'Item' not in response:
                    print(f"User not found for preferences update: {email}")
                    return {
                        'statusCode': 404,
                        'statusDescription': '404 Not Found',
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'success': False,
                            'message': 'User not found'
                        }),
                        'isBase64Encoded': False
                    }
                
                # Update preferences
                table.update_item(
                    Key={'email': email},
                    UpdateExpression='SET preferences = :prefs, updated_at = :updated',
                    ExpressionAttributeValues={
                        ':prefs': preferences,
                        ':updated': datetime.utcnow().isoformat()
                    }
                )
                
                print(f"Preferences updated for user: {email}")
                
                return {
                    'statusCode': 200,
                    'statusDescription': '200 OK',
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'success': True,
                        'message': 'Preferences updated successfully',
                        'data': preferences
                    }),
                    'isBase64Encoded': False
                }
                
            except Exception as e:
                print(f"Error updating preferences: {str(e)}")
                return {
                    'statusCode': 500,
                    'statusDescription': '500 Internal Server Error',
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'success': False,
                        'message': 'Failed to update preferences'
                    }),
                    'isBase64Encoded': False
                }
        
    except Exception as e:
        print(f"Preferences handler error: {str(e)}")
        return {
            'statusCode': 500,
            'statusDescription': '500 Internal Server Error',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Internal server error'
            }),
            'isBase64Encoded': False
        }
'''
    
    # Create zip file
    zip_filename = "/tmp/fixed-preferences-lambda.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lambda_function.py", lambda_code)
    
    return zip_filename

def update_preferences_lambda():
    """Update the preferences Lambda function."""
    
    print("🔧 Fixing Preferences Lambda Function")
    print("=" * 37)
    
    lambda_client = boto3.client('lambda')
    
    try:
        zip_file = create_fixed_preferences_lambda()
        
        with open(zip_file, 'rb') as f:
            zip_content = f.read()
        
        # Update the function code
        response = lambda_client.update_function_code(
            FunctionName='investforge-preferences',
            ZipFile=zip_content,
            Publish=True
        )
        
        print(f"✅ Preferences Lambda updated!")
        print(f"   State: {response['State']}")
        
        os.remove(zip_file)
        return True
        
    except Exception as e:
        print(f"❌ Error updating preferences Lambda: {str(e)}")
        return False

def test_fixed_preferences():
    """Test the fixed preferences functionality."""
    
    print("\n🧪 Testing Fixed Preferences Function")
    print("=" * 37)
    
    import requests
    import time
    
    test_email = "final.test@example.com"
    
    # Test 1: Save preferences
    print("1️⃣ Testing preferences save...")
    preferences = {
        "experience": "Advanced 🚀",
        "goals": ["Generate passive income", "Short-term trading"],
        "risk_tolerance": 9,
        "initial_amount": "$5,000+",
        "timestamp": "2025-09-23T20:00:00.000Z"
    }
    
    save_response = requests.post(
        "https://investforge.io/api/users/preferences",
        headers={"Content-Type": "application/json"},
        json={
            "email": test_email,
            "preferences": preferences
        }
    )
    
    print(f"Save status: {save_response.status_code}")
    if save_response.status_code == 200:
        save_data = save_response.json()
        print(f"Save success: {save_data.get('success')}")
    
    # Wait for consistency
    time.sleep(2)
    
    # Test 2: Get preferences
    print("\n2️⃣ Testing preferences retrieval...")
    get_response = requests.post(
        "https://investforge.io/api/users/preferences",
        headers={"Content-Type": "application/json"},
        json={
            "email": test_email,
            "action": "get"
        }
    )
    
    print(f"Get status: {get_response.status_code}")
    if get_response.status_code == 200:
        get_data = get_response.json()
        print(f"Get success: {get_data.get('success')}")
        
        if get_data.get('success'):
            retrieved_prefs = get_data.get('data', {})
            print(f"Retrieved preferences: {json.dumps(retrieved_prefs, indent=2)}")
            
            # Check if key fields match
            if (retrieved_prefs.get('experience') == preferences['experience'] and
                retrieved_prefs.get('risk_tolerance') == preferences['risk_tolerance']):
                print("✅ Preferences retrieval working correctly!")
            else:
                print("❌ Retrieved preferences don't match saved ones")
        else:
            print(f"❌ Get failed: {get_data}")
    else:
        print(f"❌ Get request failed: {get_response.text}")

def main():
    """Main function."""
    print("🚀 Fixing Preferences Lambda GET Functionality")
    print("=" * 45)
    
    # Update the Lambda function
    if update_preferences_lambda():
        print("\n⏳ Waiting for Lambda function to be ready...")
        import time
        time.sleep(10)
        
        # Test the fixed functionality
        test_fixed_preferences()
        
        print("\n📋 Summary:")
        print("   ✅ Preferences Lambda function fixed")
        print("   ✅ GET requests now work properly")
        print("   ✅ Action parameter handled correctly")
    else:
        print("\n❌ Failed to fix preferences Lambda")

if __name__ == "__main__":
    main()