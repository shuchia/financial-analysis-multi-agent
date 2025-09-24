#!/usr/bin/env python3
"""
Fix DynamoDB Decimal serialization issue in preferences Lambda.
"""

import os
import boto3
import zipfile
import json

def create_decimal_safe_lambda():
    """Create preferences Lambda with Decimal serialization fix."""
    
    lambda_code = '''
import json
import boto3
from datetime import datetime
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('investforge-users-simple')

def decimal_default(obj):
    """Helper function to serialize Decimal objects."""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 != 0 else int(obj)
    raise TypeError

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
                    
                    # Convert preferences to JSON-safe format
                    safe_preferences = json.loads(json.dumps(preferences, default=decimal_default))
                    
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
                            'data': safe_preferences
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
    zip_filename = "/tmp/decimal-safe-preferences-lambda.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lambda_function.py", lambda_code)
    
    return zip_filename

def update_lambda():
    """Update the preferences Lambda function."""
    
    print("🔧 Fixing Decimal Serialization Issue")
    print("=" * 35)
    
    lambda_client = boto3.client('lambda')
    
    try:
        zip_file = create_decimal_safe_lambda()
        
        with open(zip_file, 'rb') as f:
            zip_content = f.read()
        
        response = lambda_client.update_function_code(
            FunctionName='investforge-preferences',
            ZipFile=zip_content,
            Publish=True
        )
        
        print(f"✅ Lambda updated!")
        print(f"   State: {response['State']}")
        
        os.remove(zip_file)
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_decimal_fix():
    """Test the decimal serialization fix."""
    
    print("\n🧪 Testing Decimal Fix")
    print("=" * 21)
    
    import requests
    import time
    
    test_email = "final.test@example.com"
    
    # Test retrieval after the fix
    print("Testing preferences retrieval...")
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
            preferences = get_data.get('data', {})
            print(f"Retrieved preferences: {json.dumps(preferences, indent=2)}")
            
            # Check that risk_tolerance is properly converted
            risk_tolerance = preferences.get('risk_tolerance')
            if isinstance(risk_tolerance, (int, float)):
                print("✅ Decimal serialization fixed!")
                return True
            else:
                print(f"❌ Risk tolerance still has wrong type: {type(risk_tolerance)}")
                return False
        else:
            print(f"❌ Get failed: {get_data}")
            return False
    else:
        print(f"❌ Get request failed: {get_response.text}")
        return False

def main():
    """Main function."""
    print("🚀 Fixing DynamoDB Decimal Serialization")
    print("=" * 40)
    
    if update_lambda():
        print("\n⏳ Waiting for Lambda to be ready...")
        import time
        time.sleep(10)
        
        if test_decimal_fix():
            print("\n✅ Decimal serialization issue fixed!")
            print("\n📋 Summary:")
            print("   ✅ DynamoDB Decimal objects now serialize correctly")
            print("   ✅ Preferences retrieval working")
            print("   ✅ All numeric values properly converted")
        else:
            print("\n❌ Decimal fix verification failed")
    else:
        print("\n❌ Failed to update Lambda")

if __name__ == "__main__":
    main()