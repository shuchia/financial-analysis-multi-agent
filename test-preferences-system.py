#!/usr/bin/env python3
"""
Test and implement user preferences storage system.
"""

import os
import boto3
import zipfile
import json
import time

def create_preferences_lambda():
    """Create a Lambda function to handle user preferences."""
    
    lambda_code = '''
import json
import boto3
from datetime import datetime

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('investforge-users-simple')

def lambda_handler(event, context):
    """Handle user preferences requests from ALB."""
    
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
        
        # Handle GET preferences
        if event.get('httpMethod') == 'GET':
            try:
                response = table.get_item(Key={'email': email})
                if 'Item' in response:
                    user = response['Item']
                    preferences = user.get('preferences', {})
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
        
        # Handle POST/PUT preferences update
        elif event.get('httpMethod') in ['POST', 'PUT']:
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
                # Check if user exists
                response = table.get_item(Key={'email': email})
                if 'Item' not in response:
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
        
        else:
            return {
                'statusCode': 405,
                'statusDescription': '405 Method Not Allowed',
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'message': 'Method not allowed'
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
    zip_filename = "/tmp/preferences-lambda.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lambda_function.py", lambda_code)
    
    return zip_filename

def create_preferences_lambda_function():
    """Create the preferences Lambda function in AWS."""
    
    print("🔧 Creating Preferences Lambda Function")
    print("=" * 38)
    
    lambda_client = boto3.client('lambda')
    
    try:
        # Check if function already exists
        try:
            lambda_client.get_function(FunctionName='investforge-preferences')
            print("✅ Function already exists, updating...")
            
            # Update existing function
            zip_file = create_preferences_lambda()
            with open(zip_file, 'rb') as f:
                zip_content = f.read()
            
            lambda_client.update_function_code(
                FunctionName='investforge-preferences',
                ZipFile=zip_content,
                Publish=True
            )
            
            os.remove(zip_file)
            return True
            
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create new function
            print("📦 Creating new function...")
            
            zip_file = create_preferences_lambda()
            with open(zip_file, 'rb') as f:
                zip_content = f.read()
            
            # Create IAM role for Lambda (if needed)
            iam = boto3.client('iam')
            role_name = 'investforge-lambda-role'
            
            try:
                role_response = iam.get_role(RoleName=role_name)
                role_arn = role_response['Role']['Arn']
            except iam.exceptions.NoSuchEntityException:
                print("🔐 Creating IAM role...")
                
                trust_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "lambda.amazonaws.com"
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                }
                
                role_response = iam.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description='IAM role for InvestForge Lambda functions'
                )
                role_arn = role_response['Role']['Arn']
                
                # Attach basic execution policy
                iam.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                )
                
                # Attach DynamoDB policy
                iam.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn='arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess'
                )
                
                # Wait for role to be ready
                time.sleep(10)
            
            # Create function
            lambda_client.create_function(
                FunctionName='investforge-preferences',
                Runtime='python3.11',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='Handle user preferences for InvestForge',
                Timeout=30,
                MemorySize=256,
                Publish=True
            )
            
            os.remove(zip_file)
            print("✅ Preferences Lambda function created!")
            return True
            
    except Exception as e:
        print(f"❌ Error creating preferences function: {str(e)}")
        return False

def update_alb_routing():
    """Add ALB routing rules for preferences endpoint."""
    
    print("\n🔗 Setting up ALB routing for preferences")
    print("=" * 42)
    
    # Get ALB information
    elbv2 = boto3.client('elbv2')
    
    try:
        # Find the InvestForge ALB
        response = elbv2.describe_load_balancers()
        alb_arn = None
        
        for lb in response['LoadBalancers']:
            if 'investforge' in lb['LoadBalancerName'].lower():
                alb_arn = lb['LoadBalancerArn']
                break
        
        if not alb_arn:
            print("❌ Could not find InvestForge ALB")
            return False
        
        # Get the listener
        listeners = elbv2.describe_listeners(LoadBalancerArn=alb_arn)
        listener_arn = listeners['Listeners'][0]['ListenerArn']
        
        # Create target group for preferences Lambda
        print("📊 Creating target group for preferences...")
        
        lambda_client = boto3.client('lambda')
        
        # Get function ARN
        func_response = lambda_client.get_function(FunctionName='investforge-preferences')
        function_arn = func_response['Configuration']['FunctionArn']
        
        # Create target group
        try:
            tg_response = elbv2.create_target_group(
                Name='investforge-preferences-tg',
                TargetType='lambda',
                HealthCheckEnabled=False
            )
            target_group_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
            
            # Register Lambda with target group
            elbv2.register_targets(
                TargetGroupArn=target_group_arn,
                Targets=[{'Id': function_arn}]
            )
            
            # Add Lambda permission for ALB
            lambda_client.add_permission(
                FunctionName='investforge-preferences',
                StatementId='alb-invoke-preferences',
                Action='lambda:InvokeFunction',
                Principal='elasticloadbalancing.amazonaws.com',
                SourceArn=target_group_arn
            )
            
            print("✅ Target group created and configured!")
            
        except Exception as e:
            if 'already exists' in str(e):
                print("✅ Target group already exists!")
                # Get existing target group
                tgs = elbv2.describe_target_groups(Names=['investforge-preferences-tg'])
                target_group_arn = tgs['TargetGroups'][0]['TargetGroupArn']
            else:
                raise e
        
        # Create listener rule
        try:
            elbv2.create_rule(
                ListenerArn=listener_arn,
                Conditions=[
                    {
                        'Field': 'path-pattern',
                        'Values': ['/api/users/preferences', '/api/users/preferences/*']
                    }
                ],
                Priority=105,  # Use a unique priority
                Actions=[
                    {
                        'Type': 'forward',
                        'TargetGroupArn': target_group_arn
                    }
                ]
            )
            print("✅ ALB routing rule created for /api/users/preferences")
            
        except Exception as e:
            if 'already exists' in str(e) or 'priority' in str(e).lower():
                print("✅ ALB routing rule already exists!")
            else:
                print(f"⚠️  ALB rule creation warning: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up ALB routing: {str(e)}")
        return False

def test_preferences_api():
    """Test the preferences API endpoints."""
    
    print("\n🧪 Testing Preferences API")
    print("=" * 26)
    
    import subprocess
    
    # Use a known test user
    test_email = "final.test@example.com"
    
    # Test preferences data
    preferences = {
        "experience": "Some knowledge 📚",
        "goals": ["Learn about investing", "Build long-term wealth"],
        "risk_tolerance": 7,
        "initial_amount": "$1,000-5,000",
        "timestamp": "2025-09-23T19:30:00.000Z"
    }
    
    # Test 1: Update preferences
    print("1️⃣ Testing preferences update...")
    update_cmd = [
        "curl", "-s", "-X", "POST", "https://investforge.io/api/users/preferences",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "email": test_email,
            "preferences": preferences
        })
    ]
    
    update_result = subprocess.run(update_cmd, capture_output=True, text=True)
    print(f"Update response: {update_result.stdout}")
    
    # Wait a moment for consistency
    time.sleep(1)
    
    # Test 2: Get preferences
    print("\n2️⃣ Testing preferences retrieval...")
    get_cmd = [
        "curl", "-s", "-X", "GET", "https://investforge.io/api/users/preferences",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"email": test_email})
    ]
    
    get_result = subprocess.run(get_cmd, capture_output=True, text=True)
    print(f"Get response: {get_result.stdout}")
    
    # Test 3: Test with non-existent user
    print("\n3️⃣ Testing with non-existent user...")
    nonexistent_cmd = [
        "curl", "-s", "-X", "GET", "https://investforge.io/api/users/preferences",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"email": "nonexistent@example.com"})
    ]
    
    nonexistent_result = subprocess.run(nonexistent_cmd, capture_output=True, text=True)
    print(f"Non-existent user response: {nonexistent_result.stdout}")

def update_api_client_for_preferences():
    """Update the API client to support preferences."""
    
    print("\n📝 Updating API Client for Preferences")
    print("=" * 37)
    
    api_client_path = "/Users/shuchiagarwal/Documents/Financial-Analysis--Multi-Agent-Open-Source-LLM/app/utils/api_client.py"
    
    # Read current API client
    with open(api_client_path, 'r') as f:
        content = f.read()
    
    # Add preferences methods if they don't exist
    preferences_methods = '''
    # User preferences endpoints
    
    def get_user_preferences(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user preferences."""
        try:
            response = requests.get(
                f"{self.base_url}/users/preferences",
                headers=self._get_headers(include_auth=False),
                json={'email': email},
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result and result.get('success'):
                return result['data']
            
            return None
            
        except Exception as e:
            st.error(f"Failed to get preferences: {str(e)}")
            return None
    
    def save_user_preferences(self, email: str, preferences: Dict[str, Any]) -> bool:
        """Save user preferences."""
        try:
            response = requests.post(
                f"{self.base_url}/users/preferences",
                headers=self._get_headers(include_auth=False),
                json={
                    'email': email,
                    'preferences': preferences
                },
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            return result is not None and result.get('success', False)
            
        except Exception as e:
            st.error(f"Failed to save preferences: {str(e)}")
            return False
'''
    
    # Check if preferences methods already exist
    if 'get_user_preferences' not in content:
        # Add before the last line (global api_client instance)
        lines = content.split('\n')
        insert_index = len(lines) - 3  # Before the last few lines
        
        # Insert the new methods
        new_lines = lines[:insert_index] + preferences_methods.split('\n') + lines[insert_index:]
        new_content = '\n'.join(new_lines)
        
        # Write back to file
        with open(api_client_path, 'w') as f:
            f.write(new_content)
        
        print("✅ API client updated with preferences methods")
    else:
        print("✅ API client already has preferences methods")

def update_streamlit_app_preferences():
    """Update the Streamlit app to use the preferences API."""
    
    print("\n📱 Updating Streamlit App for Preferences")
    print("=" * 39)
    
    app_path = "/Users/shuchiagarwal/Documents/Financial-Analysis--Multi-Agent-Open-Source-LLM/app/app.py"
    
    # Read current app
    with open(app_path, 'r') as f:
        content = f.read()
    
    # Replace the save_user_preferences function
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
        else:
            st.warning("⚠️ Preferences saved locally but couldn't sync to server")
    '''
    
    # Replace the function
    import re
    pattern = r'def save_user_preferences\(.*?\):(.*?)(?=\n\ndef|\nclass|\Z)'
    
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, new_save_function.strip(), content, flags=re.DOTALL)
        
        # Write back to file
        with open(app_path, 'w') as f:
            f.write(new_content)
        
        print("✅ Streamlit app updated to save preferences to API")
    else:
        print("⚠️ Could not find save_user_preferences function to update")

def main():
    """Main function."""
    print("🚀 Testing and Implementing Preferences System")
    print("=" * 45)
    print("\nSetting up user preferences storage and API.\n")
    
    # Step 1: Create preferences Lambda function
    if not create_preferences_lambda_function():
        print("❌ Failed to create preferences Lambda function")
        return
    
    # Wait for function to be ready
    print("\n⏳ Waiting for Lambda function to be ready...")
    time.sleep(10)
    
    # Step 2: Set up ALB routing
    if not update_alb_routing():
        print("❌ Failed to set up ALB routing")
        return
    
    # Wait for ALB changes to propagate
    print("\n⏳ Waiting for ALB changes to propagate...")
    time.sleep(15)
    
    # Step 3: Test the API
    test_preferences_api()
    
    # Step 4: Update API client
    update_api_client_for_preferences()
    
    # Step 5: Update Streamlit app
    update_streamlit_app_preferences()
    
    print("\n📋 Summary:")
    print("   ✅ Preferences Lambda function created")
    print("   ✅ ALB routing configured for /api/users/preferences")
    print("   ✅ API client updated with preferences methods")
    print("   ✅ Streamlit app updated to save preferences")
    print("\n🎯 Users can now save and retrieve their onboarding preferences!")

if __name__ == "__main__":
    main()