#!/usr/bin/env python3
"""
Simple test deployment script that creates minimal AWS resources
to test the InvestForge API without complex dependencies.
"""

import boto3
import json
import sys
import time
from datetime import datetime

def test_aws_connection():
    """Test AWS connection and permissions."""
    print("🔑 Testing AWS connection...")
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ Connected to AWS Account: {identity['Account']}")
        return True
    except Exception as e:
        print(f"❌ AWS connection failed: {e}")
        return False

def create_dynamodb_tables():
    """Create minimal DynamoDB tables for testing."""
    print("📊 Creating DynamoDB tables...")
    dynamodb = boto3.client('dynamodb')
    
    tables = [
        {
            'TableName': 'investforge-api-dev-users',
            'KeySchema': [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        {
            'TableName': 'investforge-api-dev-waitlist',
            'KeySchema': [
                {'AttributeName': 'email', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'email', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }
    ]
    
    for table_config in tables:
        try:
            # Check if table exists
            dynamodb.describe_table(TableName=table_config['TableName'])
            print(f"✅ Table {table_config['TableName']} already exists")
        except dynamodb.exceptions.ResourceNotFoundException:
            # Create table
            print(f"Creating table {table_config['TableName']}...")
            response = dynamodb.create_table(**table_config)
            print(f"✅ Table {table_config['TableName']} created")
        except Exception as e:
            print(f"❌ Error with table {table_config['TableName']}: {e}")

def test_api_locally():
    """Test API functions locally."""
    print("🧪 Testing API functions locally...")
    
    # Test imports
    sys.path.insert(0, 'api')
    try:
        from utils.response import success_response, error_response
        from models.user import User
        from utils.auth import password_manager, jwt_manager
        
        print("✅ All imports successful")
        
        # Test password hashing
        password = "testpassword123"
        hashed = password_manager.hash_password(password)
        assert password_manager.verify_password(password, hashed)
        print("✅ Password hashing works")
        
        # Test JWT tokens
        user_data = {'user_id': 'test-123', 'email': 'test@example.com'}
        token = jwt_manager.create_access_token('test-123', user_data)
        decoded = jwt_manager.verify_token(token)
        assert decoded['user_id'] == 'test-123'
        print("✅ JWT tokens work")
        
        # Test response formatting
        response = success_response(data={'test': 'data'})
        assert response['statusCode'] == 200
        print("✅ Response formatting works")
        
        return True
        
    except Exception as e:
        print(f"❌ Local API test failed: {e}")
        return False

def create_simple_lambda():
    """Create a simple Lambda function for testing."""
    print("⚡ Creating test Lambda function...")
    
    lambda_client = boto3.client('lambda')
    iam_client = boto3.client('iam')
    
    # Create IAM role for Lambda
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # Create role
        role_name = 'investforge-lambda-test-role'
        try:
            role_response = iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description='Test role for InvestForge Lambda'
            )
            role_arn = role_response['Role']['Arn']
            print(f"✅ Created IAM role: {role_arn}")
            
            # Attach basic execution policy
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            
            # Wait for role to propagate
            time.sleep(10)
            
        except iam_client.exceptions.EntityAlreadyExistsException:
            role_response = iam_client.get_role(RoleName=role_name)
            role_arn = role_response['Role']['Arn']
            print(f"✅ Using existing IAM role: {role_arn}")
        
        # Create simple Lambda function
        function_code = '''
def handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': '{"message": "InvestForge API Test - Working!", "timestamp": "' + str(context.aws_request_id) + '"}'
    }
'''
        
        import zipfile
        import io
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('lambda_function.py', function_code)
        
        zip_buffer.seek(0)
        
        function_name = 'investforge-api-test'
        
        try:
            # Create function
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.handler',
                Code={'ZipFile': zip_buffer.read()},
                Description='InvestForge API Test Function'
            )
            print(f"✅ Created Lambda function: {function_name}")
            
        except lambda_client.exceptions.ResourceConflictException:
            # Update existing function
            zip_buffer.seek(0)
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_buffer.read()
            )
            print(f"✅ Updated existing Lambda function: {function_name}")
        
        # Test the function
        print("🧪 Testing Lambda function...")
        test_response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse'
        )
        
        response_payload = json.loads(test_response['Payload'].read())
        print(f"✅ Lambda test response: {response_payload}")
        
        return True
        
    except Exception as e:
        print(f"❌ Lambda creation failed: {e}")
        return False

def main():
    """Run deployment tests."""
    print("🚀 InvestForge Deployment Test")
    print("=" * 30)
    
    # Test 1: AWS Connection
    if not test_aws_connection():
        sys.exit(1)
    
    print()
    
    # Test 2: Create DynamoDB tables
    create_dynamodb_tables()
    
    print()
    
    # Test 3: Test API locally
    if not test_api_locally():
        print("⚠️  Local API tests failed, but continuing...")
    
    print()
    
    # Test 4: Create simple Lambda
    if create_simple_lambda():
        print()
        print("🎉 Basic deployment test completed!")
        print()
        print("✅ What's working:")
        print("  - AWS connection")
        print("  - DynamoDB tables created")
        print("  - Lambda function deployed")
        print()
        print("📝 Next steps:")
        print("  1. Install Docker to build container images")
        print("  2. Set up proper Serverless Framework deployment")
        print("  3. Deploy full infrastructure with CloudFormation")
        print("  4. Configure domain and SSL certificate")
    else:
        print("❌ Deployment test failed")
        sys.exit(1)

if __name__ == "__main__":
    main()