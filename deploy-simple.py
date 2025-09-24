#!/usr/bin/env python3
"""
Deploy InvestForge API using direct AWS SDK calls (no Serverless Framework needed).
"""

import boto3
import json
import zipfile
import io
import os
import time
from datetime import datetime

def create_lambda_deployment_package():
    """Create a deployment package with all the API code."""
    print("📦 Creating deployment package...")
    
    # Create ZIP file
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add all handler files
        handlers_dir = 'api/handlers'
        for filename in os.listdir(handlers_dir):
            if filename.endswith('.py'):
                file_path = os.path.join(handlers_dir, filename)
                zip_file.write(file_path, f'handlers/{filename}')
        
        # Add utils
        utils_dir = 'api/utils'
        for filename in os.listdir(utils_dir):
            if filename.endswith('.py'):
                file_path = os.path.join(utils_dir, filename)
                zip_file.write(file_path, f'utils/{filename}')
        
        # Add models
        models_dir = 'api/models'
        for filename in os.listdir(models_dir):
            if filename.endswith('.py'):
                file_path = os.path.join(models_dir, filename)
                zip_file.write(file_path, f'models/{filename}')
        
        # Add requirements (will need layer for dependencies)
        zip_file.write('api/requirements.txt', 'requirements.txt')
        
        # Add a simple Lambda function that imports our handlers
        wrapper_code = '''
import sys
import json
sys.path.append('/opt/python')  # For Lambda layers

# Import handlers
from handlers import auth, users, analytics, waitlist, health

def signup(event, context):
    return auth.signup(event, context)

def login(event, context):
    return auth.login(event, context)

def health_check(event, context):
    return health.check(event, context)

def join_waitlist(event, context):
    return waitlist.join_waitlist(event, context)

def track_event(event, context):
    return analytics.track_event(event, context)

def get_user(event, context):
    return users.get_user(event, context)
'''
        zip_file.writestr('lambda_function.py', wrapper_code)
    
    zip_buffer.seek(0)
    return zip_buffer.read()

def create_iam_role():
    """Create IAM role for Lambda functions."""
    print("🔐 Creating IAM role...")
    
    iam = boto3.client('iam')
    
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
    
    role_name = 'investforge-lambda-role'
    
    try:
        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='InvestForge Lambda execution role'
        )
        role_arn = role_response['Role']['Arn']
        print(f"✅ Created IAM role: {role_arn}")
        
        # Attach policies
        policies = [
            'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
            'arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess',
            'arn:aws:iam::aws:policy/AmazonSESFullAccess'
        ]
        
        for policy_arn in policies:
            iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        
        # Wait for role to propagate
        time.sleep(10)
        
    except iam.exceptions.EntityAlreadyExistsException:
        role_response = iam.get_role(RoleName=role_name)
        role_arn = role_response['Role']['Arn']
        print(f"✅ Using existing IAM role: {role_arn}")
    
    return role_arn

def create_lambda_functions(role_arn, deployment_package):
    """Create Lambda functions."""
    print("⚡ Creating Lambda functions...")
    
    lambda_client = boto3.client('lambda')
    
    functions = [
        {'name': 'investforge-signup', 'handler': 'lambda_function.signup'},
        {'name': 'investforge-login', 'handler': 'lambda_function.login'},
        {'name': 'investforge-health', 'handler': 'lambda_function.health_check'},
        {'name': 'investforge-waitlist', 'handler': 'lambda_function.join_waitlist'},
        {'name': 'investforge-analytics', 'handler': 'lambda_function.track_event'},
        {'name': 'investforge-get-user', 'handler': 'lambda_function.get_user'},
    ]
    
    created_functions = []
    
    for func in functions:
        try:
            response = lambda_client.create_function(
                FunctionName=func['name'],
                Runtime='python3.9',
                Role=role_arn,
                Handler=func['handler'],
                Code={'ZipFile': deployment_package},
                Description=f'InvestForge API - {func["name"]}',
                Environment={
                    'Variables': {
                        'JWT_SECRET_KEY': os.getenv('JWT_SECRET_KEY', 'dev-secret'),
                        'DYNAMODB_TABLE_USERS': 'investforge-api-dev-users',
                        'DYNAMODB_TABLE_WAITLIST': 'investforge-api-dev-waitlist',
                        'DYNAMODB_TABLE_ANALYTICS': 'investforge-api-dev-analytics',
                        'DYNAMODB_TABLE_USAGE': 'investforge-api-dev-usage',
                    }
                },
                Timeout=30
            )
            print(f"✅ Created function: {func['name']}")
            created_functions.append(func['name'])
            
        except lambda_client.exceptions.ResourceConflictException:
            # Update existing function
            lambda_client.update_function_code(
                FunctionName=func['name'],
                ZipFile=deployment_package
            )
            print(f"✅ Updated function: {func['name']}")
            created_functions.append(func['name'])
        
        except Exception as e:
            print(f"❌ Failed to create {func['name']}: {e}")
    
    return created_functions

def create_api_gateway_full(function_names):
    """Create a complete API Gateway with all endpoints."""
    print("🌐 Creating full API Gateway...")
    
    apigateway = boto3.client('apigateway')
    lambda_client = boto3.client('lambda')
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    region = boto3.Session().region_name or 'us-east-1'
    
    try:
        # Create REST API
        api_response = apigateway.create_rest_api(
            name='investforge-api-full',
            description='InvestForge Complete API',
            endpointConfiguration={'types': ['REGIONAL']}
        )
        
        api_id = api_response['id']
        print(f"✅ Created API Gateway: {api_id}")
        
        # Get root resource
        resources = apigateway.get_resources(restApiId=api_id)
        root_id = next(r['id'] for r in resources['items'] if r['path'] == '/')
        
        # Define endpoints
        endpoints = [
            {'path': 'health', 'method': 'GET', 'function': 'investforge-health'},
            {'path': 'auth', 'method': 'ANY', 'function': 'investforge-signup'},  # Will handle both signup/login
            {'path': 'waitlist', 'method': 'POST', 'function': 'investforge-waitlist'},
            {'path': 'analytics', 'method': 'POST', 'function': 'investforge-analytics'},
            {'path': 'users', 'method': 'GET', 'function': 'investforge-get-user'},
        ]
        
        for endpoint in endpoints:
            if endpoint['function'] not in function_names:
                continue
                
            # Create resource
            try:
                resource = apigateway.create_resource(
                    restApiId=api_id,
                    parentId=root_id,
                    pathPart=endpoint['path']
                )
                resource_id = resource['id']
            except apigateway.exceptions.ConflictException:
                # Resource already exists
                resources = apigateway.get_resources(restApiId=api_id)
                resource_id = next(r['id'] for r in resources['items'] if r['pathPart'] == endpoint['path'])
            
            # Create method
            apigateway.put_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod=endpoint['method'],
                authorizationType='NONE'
            )
            
            # Set up Lambda integration
            lambda_uri = f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/arn:aws:lambda:{region}:{account_id}:function:{endpoint['function']}/invocations"
            
            apigateway.put_integration(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod=endpoint['method'],
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=lambda_uri
            )
            
            # Add Lambda permission
            try:
                lambda_client.add_permission(
                    FunctionName=endpoint['function'],
                    StatementId=f'apigateway-{endpoint["path"]}-{api_id}',
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=f"arn:aws:execute-api:{region}:{account_id}:{api_id}/*/*"
                )
            except lambda_client.exceptions.ResourceConflictException:
                pass  # Permission already exists
        
        # Deploy the API
        deployment = apigateway.create_deployment(
            restApiId=api_id,
            stageName='dev',
            description='Development deployment'
        )
        
        invoke_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/dev"
        
        print(f"✅ API deployed: {invoke_url}")
        return invoke_url
        
    except Exception as e:
        print(f"❌ API Gateway creation failed: {e}")
        return None

def main():
    """Main deployment function."""
    print("🚀 InvestForge Complete API Deployment")
    print("=" * 40)
    
    # Create deployment package
    deployment_package = create_lambda_deployment_package()
    
    # Create IAM role
    role_arn = create_iam_role()
    
    # Create Lambda functions
    function_names = create_lambda_functions(role_arn, deployment_package)
    
    if function_names:
        print()
        # Create API Gateway
        api_url = create_api_gateway_full(function_names)
        
        if api_url:
            print()
            print("🎉 Deployment completed successfully!")
            print()
            print("📋 API Endpoints:")
            print(f"  🏥 Health: {api_url}/health")
            print(f"  📝 Signup: {api_url}/auth (POST)")
            print(f"  🔑 Login: {api_url}/auth (POST)")
            print(f"  📧 Waitlist: {api_url}/waitlist (POST)")
            print(f"  📊 Analytics: {api_url}/analytics (POST)")
            print(f"  👤 User: {api_url}/users (GET)")
            print()
            print("🧪 Test commands:")
            print(f"curl {api_url}/health")
            print(f"curl -X POST {api_url}/waitlist -H 'Content-Type: application/json' -d '{{\"email\":\"test@example.com\"}}'")

if __name__ == "__main__":
    main()