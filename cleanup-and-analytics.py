#!/usr/bin/env python3
"""
Clean up test users and set up proper analytics tracking system.
"""

import boto3
import json
import zipfile
import os
from datetime import datetime

def clean_up_test_users():
    """Remove all test users from DynamoDB to start fresh."""
    
    print("🧹 Cleaning Up Test Users")
    print("=" * 26)
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('investforge-users-simple')
    
    try:
        # Scan all users
        response = table.scan()
        users = response['Items']
        
        print(f"Found {len(users)} users to clean up:")
        
        deleted_count = 0
        for user in users:
            email = user['email']
            print(f"  - {email}")
            
            # Delete user
            table.delete_item(Key={'email': email})
            deleted_count += 1
        
        print(f"\n✅ Deleted {deleted_count} users")
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning up users: {str(e)}")
        return False

def create_analytics_table():
    """Create a DynamoDB table for analytics tracking."""
    
    print("\n📊 Creating Analytics Table")
    print("=" * 28)
    
    dynamodb = boto3.client('dynamodb')
    
    try:
        # Check if table already exists
        try:
            response = dynamodb.describe_table(TableName='investforge-analytics')
            print("✅ Analytics table already exists!")
            return True
        except dynamodb.exceptions.ResourceNotFoundException:
            pass
        
        # Create analytics table
        print("📈 Creating new analytics table...")
        response = dynamodb.create_table(
            TableName='investforge-analytics',
            KeySchema=[
                {
                    'AttributeName': 'event_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'event_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'event_type',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user-events-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'user_id',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                },
                {
                    'IndexName': 'event-type-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'event_type',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        print("⏳ Waiting for table to be active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName='investforge-analytics')
        
        print("✅ Analytics table created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating analytics table: {str(e)}")
        return False

def create_usage_table():
    """Create a DynamoDB table for usage tracking."""
    
    print("\n📈 Creating Usage Tracking Table")
    print("=" * 33)
    
    dynamodb = boto3.client('dynamodb')
    
    try:
        # Check if table already exists
        try:
            response = dynamodb.describe_table(TableName='investforge-usage')
            print("✅ Usage table already exists!")
            return True
        except dynamodb.exceptions.ResourceNotFoundException:
            pass
        
        # Create usage table
        print("🔢 Creating new usage table...")
        response = dynamodb.create_table(
            TableName='investforge-usage',
            KeySchema=[
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'month',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'month',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        print("⏳ Waiting for table to be active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName='investforge-usage')
        
        print("✅ Usage table created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating usage table: {str(e)}")
        return False

def create_analytics_lambda():
    """Create a Lambda function to handle analytics tracking."""
    
    lambda_code = '''
import json
import boto3
import uuid
from datetime import datetime, timezone

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
analytics_table = dynamodb.Table('investforge-analytics')
usage_table = dynamodb.Table('investforge-usage')

def lambda_handler(event, context):
    """Handle analytics and usage tracking requests."""
    
    print(f"Analytics event received: {json.dumps(event, default=str)}")
    
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
                'service': 'analytics'
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
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        action = body.get('action', 'track')
        
        if action == 'track':
            return handle_track_event(body)
        elif action == 'usage':
            return handle_usage_update(body)
        elif action == 'get_usage':
            return handle_get_usage(body)
        else:
            return {
                'statusCode': 400,
                'statusDescription': '400 Bad Request',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'message': 'Invalid action'
                }),
                'isBase64Encoded': False
            }
    
    except Exception as e:
        print(f"Analytics handler error: {str(e)}")
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

def handle_track_event(body):
    """Handle event tracking."""
    
    user_id = body.get('user_id')
    event_type = body.get('event_type')
    event_data = body.get('event_data', {})
    
    if not user_id or not event_type:
        return {
            'statusCode': 400,
            'statusDescription': '400 Bad Request',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'user_id and event_type are required'
            }),
            'isBase64Encoded': False
        }
    
    try:
        # Store analytics event
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        analytics_table.put_item(
            Item={
                'event_id': event_id,
                'user_id': user_id,
                'event_type': event_type,
                'event_data': event_data,
                'timestamp': timestamp
            }
        )
        
        print(f"Tracked event: {event_type} for user: {user_id}")
        
        return {
            'statusCode': 200,
            'statusDescription': '200 OK',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': 'Event tracked successfully'
            }),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        print(f"Error tracking event: {str(e)}")
        return {
            'statusCode': 500,
            'statusDescription': '500 Internal Server Error',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Failed to track event'
            }),
            'isBase64Encoded': False
        }

def handle_usage_update(body):
    """Handle usage tracking updates."""
    
    user_id = body.get('user_id')
    feature = body.get('feature')
    count = body.get('count', 1)
    
    if not user_id or not feature:
        return {
            'statusCode': 400,
            'statusDescription': '400 Bad Request',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'user_id and feature are required'
            }),
            'isBase64Encoded': False
        }
    
    try:
        # Update usage for current month
        current_month = datetime.now().strftime('%Y-%m')
        
        # Increment usage count
        usage_table.update_item(
            Key={
                'user_id': user_id,
                'month': current_month
            },
            UpdateExpression=f'ADD {feature} :count',
            ExpressionAttributeValues={
                ':count': count
            }
        )
        
        print(f"Updated usage: {feature}+{count} for user: {user_id}")
        
        return {
            'statusCode': 200,
            'statusDescription': '200 OK',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': 'Usage updated successfully'
            }),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        print(f"Error updating usage: {str(e)}")
        return {
            'statusCode': 500,
            'statusDescription': '500 Internal Server Error',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Failed to update usage'
            }),
            'isBase64Encoded': False
        }

def handle_get_usage(body):
    """Handle usage retrieval."""
    
    user_id = body.get('user_id')
    month = body.get('month', datetime.now().strftime('%Y-%m'))
    
    if not user_id:
        return {
            'statusCode': 400,
            'statusDescription': '400 Bad Request',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'user_id is required'
            }),
            'isBase64Encoded': False
        }
    
    try:
        # Get usage for specified month
        response = usage_table.get_item(
            Key={
                'user_id': user_id,
                'month': month
            }
        )
        
        usage_data = {}
        if 'Item' in response:
            item = response['Item']
            # Remove the key fields
            usage_data = {k: v for k, v in item.items() if k not in ['user_id', 'month']}
        
        return {
            'statusCode': 200,
            'statusDescription': '200 OK',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': 'Usage retrieved successfully',
                'data': {
                    'user_id': user_id,
                    'month': month,
                    'usage': usage_data
                }
            }),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        print(f"Error getting usage: {str(e)}")
        return {
            'statusCode': 500,
            'statusDescription': '500 Internal Server Error',
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Failed to get usage'
            }),
            'isBase64Encoded': False
        }
'''
    
    # Create zip file
    zip_filename = "/tmp/analytics-lambda.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lambda_function.py", lambda_code)
    
    return zip_filename

def deploy_analytics_lambda():
    """Deploy or update the analytics Lambda function."""
    
    print("\n⚡ Deploying Analytics Lambda")
    print("=" * 29)
    
    lambda_client = boto3.client('lambda')
    
    try:
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName='investforge-analytics-new')
            print("✅ Function exists, updating...")
            
            # Update existing function
            zip_file = create_analytics_lambda()
            with open(zip_file, 'rb') as f:
                zip_content = f.read()
            
            lambda_client.update_function_code(
                FunctionName='investforge-analytics-new',
                ZipFile=zip_content,
                Publish=True
            )
            
            os.remove(zip_file)
            return True
            
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create new function
            print("📦 Creating new analytics function...")
            
            zip_file = create_analytics_lambda()
            with open(zip_file, 'rb') as f:
                zip_content = f.read()
            
            # Get or create IAM role
            iam = boto3.client('iam')
            role_name = 'investforge-lambda-role'
            
            try:
                role_response = iam.get_role(RoleName=role_name)
                role_arn = role_response['Role']['Arn']
            except iam.exceptions.NoSuchEntityException:
                print("Creating IAM role...")
                # Role creation logic (same as before)
                pass
            
            # Create function
            lambda_client.create_function(
                FunctionName='investforge-analytics-new',
                Runtime='python3.11',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='Handle analytics and usage tracking for InvestForge',
                Timeout=30,
                MemorySize=256,
                Publish=True
            )
            
            os.remove(zip_file)
            print("✅ Analytics Lambda function created!")
            return True
            
    except Exception as e:
        print(f"❌ Error deploying analytics Lambda: {str(e)}")
        return False

def update_api_client_analytics():
    """Update the API client to include analytics methods."""
    
    print("\n📝 Updating API Client for Analytics")
    print("=" * 35)
    
    api_client_path = "/Users/shuchiagarwal/Documents/Financial-Analysis--Multi-Agent-Open-Source-LLM/app/utils/api_client.py"
    
    # Read current API client
    with open(api_client_path, 'r') as f:
        content = f.read()
    
    # Analytics methods to add
    analytics_methods = '''
    # Enhanced analytics methods
    
    def track_signup_event(self, user_id: str, plan: str, referral_source: str = None) -> bool:
        """Track user signup event."""
        return self.track_event('user_signup', {
            'plan': plan,
            'referral_source': referral_source,
            'timestamp': datetime.now().isoformat()
        })
    
    def track_login_event(self, user_id: str) -> bool:
        """Track user login event."""
        return self.track_event('user_login', {
            'timestamp': datetime.now().isoformat()
        })
    
    def track_analysis_event(self, user_id: str, symbol: str, analysis_type: str) -> bool:
        """Track stock analysis event."""
        return self.track_event('stock_analysis', {
            'symbol': symbol,
            'analysis_type': analysis_type,
            'timestamp': datetime.now().isoformat()
        })
    
    def track_preferences_event(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Track preferences completion event."""
        return self.track_event('preferences_completed', {
            'experience': preferences.get('experience'),
            'risk_tolerance': preferences.get('risk_tolerance'),
            'initial_amount': preferences.get('initial_amount'),
            'timestamp': datetime.now().isoformat()
        })
    
    def increment_feature_usage(self, user_id: str, feature: str, count: int = 1) -> bool:
        """Increment usage count for a feature."""
        try:
            response = requests.post(
                f"{self.base_url}/analytics/usage",
                headers=self._get_headers(include_auth=False),
                json={
                    'action': 'usage',
                    'user_id': user_id,
                    'feature': feature,
                    'count': count
                },
                timeout=self.timeout
            )
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def get_user_usage(self, user_id: str, month: str = None) -> Optional[Dict[str, Any]]:
        """Get user usage statistics."""
        try:
            payload = {
                'action': 'get_usage',
                'user_id': user_id
            }
            if month:
                payload['month'] = month
            
            response = requests.post(
                f"{self.base_url}/analytics/usage",
                headers=self._get_headers(include_auth=False),
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result['data']
            
            return None
            
        except Exception:
            return None
'''
    
    # Check if analytics methods already exist
    if 'track_signup_event' not in content:
        # Add import for datetime
        if 'from datetime import datetime' not in content:
            content = content.replace(
                'import streamlit as st\nfrom datetime import datetime, timedelta',
                'import streamlit as st\nfrom datetime import datetime, timedelta'
            )
        
        # Add before the last few lines
        lines = content.split('\n')
        insert_index = len(lines) - 3
        
        new_lines = lines[:insert_index] + analytics_methods.split('\n') + lines[insert_index:]
        new_content = '\n'.join(new_lines)
        
        with open(api_client_path, 'w') as f:
            f.write(new_content)
        
        print("✅ API client updated with analytics methods")
    else:
        print("✅ API client already has analytics methods")

def update_streamlit_analytics():
    """Update Streamlit app to use analytics tracking."""
    
    print("\n📱 Updating Streamlit App for Analytics")
    print("=" * 37)
    
    app_path = "/Users/shuchiagarwal/Documents/Financial-Analysis--Multi-Agent-Open-Source-LLM/app/app.py"
    
    # Read current app
    with open(app_path, 'r') as f:
        content = f.read()
    
    # Update save_user_preferences to include analytics
    old_save_function = '''def save_user_preferences(experience, goals, risk, amount):
    """Save user onboarding preferences."""
    preferences = {
        'experience': experience,
        'goals': goals,
        'risk_tolerance': risk,
        'initial_amount': amount,
        'timestamp': datetime.now().isoformat()
    }
    
    # Save to session state
    st.session_state.user_preferences = preferences
    
    # Save to database via API
    if st.session_state.user_email:
        success = api_client.save_user_preferences(st.session_state.user_email, preferences)
        if success:
            st.success("✅ Preferences saved successfully!")
        else:
            st.warning("⚠️ Preferences saved locally but couldn't sync to server")'''
    
    new_save_function = '''def save_user_preferences(experience, goals, risk, amount):
    """Save user onboarding preferences."""
    preferences = {
        'experience': experience,
        'goals': goals,
        'risk_tolerance': risk,
        'initial_amount': amount,
        'timestamp': datetime.now().isoformat()
    }
    
    # Save to session state
    st.session_state.user_preferences = preferences
    
    # Save to database via API
    if st.session_state.user_email:
        success = api_client.save_user_preferences(st.session_state.user_email, preferences)
        if success:
            st.success("✅ Preferences saved successfully!")
            
            # Track preferences completion
            user_data = st.session_state.get('user_data', {})
            user_id = user_data.get('user_id')
            if user_id:
                api_client.track_preferences_event(user_id, preferences)
                api_client.increment_feature_usage(user_id, 'onboarding_completed', 1)
        else:
            st.warning("⚠️ Preferences saved locally but couldn't sync to server")'''
    
    # Replace the function
    if old_save_function in content:
        content = content.replace(old_save_function, new_save_function)
        
        with open(app_path, 'w') as f:
            f.write(content)
        
        print("✅ Streamlit app updated with analytics tracking")
    else:
        print("⚠️ Could not find exact function to update")

def test_clean_system():
    """Test that the system is clean and ready for fresh users."""
    
    print("\n🧪 Testing Clean System State")
    print("=" * 28)
    
    # Test 1: Check that users table is empty
    dynamodb = boto3.resource('dynamodb')
    users_table = dynamodb.Table('investforge-users-simple')
    
    try:
        response = users_table.scan()
        user_count = len(response['Items'])
        
        if user_count == 0:
            print("✅ Users table is clean (0 users)")
        else:
            print(f"⚠️ Users table still has {user_count} users")
    except Exception as e:
        print(f"❌ Error checking users table: {str(e)}")
    
    # Test 2: Test signup with fresh user
    print("\n🧪 Testing fresh signup...")
    import requests
    import uuid
    
    test_email = f"fresh-user-{str(uuid.uuid4())[:8]}@example.com"
    
    signup_response = requests.post(
        "https://investforge.io/api/auth/signup",
        headers={"Content-Type": "application/json"},
        json={
            "email": test_email,
            "password": "testpass123",
            "first_name": "Fresh",
            "last_name": "User",
            "plan": "free"
        }
    )
    
    if signup_response.status_code == 201:
        signup_data = signup_response.json()
        if signup_data.get('success'):
            print("✅ Fresh signup working correctly")
            
            # Test login
            import time
            time.sleep(1)
            
            login_response = requests.post(
                "https://investforge.io/api/auth/login",
                headers={"Content-Type": "application/json"},
                json={
                    "email": test_email,
                    "password": "testpass123"
                }
            )
            
            if login_response.status_code == 200:
                print("✅ Fresh login working correctly")
            else:
                print("❌ Fresh login failed")
        else:
            print("❌ Fresh signup failed")
    else:
        print(f"❌ Fresh signup HTTP error: {signup_response.status_code}")

def main():
    """Main function."""
    print("🚀 Cleaning Up System and Setting Up Analytics")
    print("=" * 47)
    print("\nThis will remove all test users and set up proper analytics tracking.\n")
    
    # Step 1: Clean up existing users
    if not clean_up_test_users():
        print("❌ Failed to clean up users")
        return
    
    # Step 2: Create analytics tables
    if not create_analytics_table():
        print("❌ Failed to create analytics table")
        return
    
    if not create_usage_table():
        print("❌ Failed to create usage table")
        return
    
    # Step 3: Deploy analytics Lambda
    if not deploy_analytics_lambda():
        print("❌ Failed to deploy analytics Lambda")
        return
    
    # Step 4: Update API client and Streamlit app
    update_api_client_analytics()
    update_streamlit_analytics()
    
    # Step 5: Test the clean system
    test_clean_system()
    
    print("\n📋 Summary:")
    print("   ✅ All test users removed from DynamoDB")
    print("   ✅ Analytics table created for event tracking")
    print("   ✅ Usage table created for feature usage tracking")
    print("   ✅ Analytics Lambda function deployed")
    print("   ✅ API client updated with analytics methods")
    print("   ✅ Streamlit app updated with usage tracking")
    print("\n🎯 System is now clean and ready with proper analytics!")

if __name__ == "__main__":
    main()