#!/usr/bin/env python3
"""
Create a simple API Gateway to test InvestForge Lambda functions.
"""

import boto3
import json
import time

def create_api_gateway():
    """Create API Gateway and connect to Lambda."""
    print("🌐 Creating API Gateway...")
    
    # Clients
    apigateway = boto3.client('apigateway')
    lambda_client = boto3.client('lambda')
    sts = boto3.client('sts')
    
    # Get account info
    account_id = sts.get_caller_identity()['Account']
    region = boto3.Session().region_name or 'us-east-1'
    
    try:
        # Create REST API
        api_response = apigateway.create_rest_api(
            name='investforge-api-test',
            description='InvestForge Test API',
            endpointConfiguration={'types': ['REGIONAL']}
        )
        
        api_id = api_response['id']
        print(f"✅ Created API Gateway: {api_id}")
        
        # Get root resource
        resources = apigateway.get_resources(restApiId=api_id)
        root_id = None
        for resource in resources['items']:
            if resource['path'] == '/':
                root_id = resource['id']
                break
        
        # Create health resource
        health_resource = apigateway.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='health'
        )
        health_resource_id = health_resource['id']
        
        # Create GET method for health
        apigateway.put_method(
            restApiId=api_id,
            resourceId=health_resource_id,
            httpMethod='GET',
            authorizationType='NONE'
        )
        
        # Set up Lambda integration
        lambda_uri = f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/arn:aws:lambda:{region}:{account_id}:function:investforge-api-test/invocations"
        
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=health_resource_id,
            httpMethod='GET',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=lambda_uri
        )
        
        # Give API Gateway permission to invoke Lambda
        try:
            lambda_client.add_permission(
                FunctionName='investforge-api-test',
                StatementId='apigateway-test',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f"arn:aws:execute-api:{region}:{account_id}:{api_id}/*/*"
            )
            print("✅ Added Lambda permission for API Gateway")
        except lambda_client.exceptions.ResourceConflictException:
            print("✅ Lambda permission already exists")
        
        # Deploy the API
        deployment = apigateway.create_deployment(
            restApiId=api_id,
            stageName='test',
            description='Test deployment'
        )
        
        print(f"✅ Deployed API to stage: test")
        
        # Get the invoke URL
        invoke_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/test"
        
        print()
        print("🎉 API Gateway created successfully!")
        print(f"📍 API URL: {invoke_url}")
        print(f"🧪 Test endpoint: {invoke_url}/health")
        
        return invoke_url
        
    except Exception as e:
        print(f"❌ API Gateway creation failed: {e}")
        return None

def test_api_endpoint(api_url):
    """Test the API endpoint."""
    print(f"🧪 Testing API endpoint: {api_url}/health")
    
    import urllib.request
    import urllib.error
    
    try:
        with urllib.request.urlopen(f"{api_url}/health") as response:
            data = response.read().decode()
            print(f"✅ API Response: {data}")
            return True
    except urllib.error.URLError as e:
        print(f"❌ API test failed: {e}")
        return False

def main():
    """Main deployment function."""
    print("🚀 Creating InvestForge Test API")
    print("=" * 35)
    
    api_url = create_api_gateway()
    
    if api_url:
        print()
        print("⏳ Waiting for API to be ready...")
        time.sleep(10)  # Wait for deployment to propagate
        
        print()
        test_api_endpoint(api_url)
        
        print()
        print("📋 Summary:")
        print(f"  🌐 API Gateway: {api_url}")
        print(f"  ⚡ Lambda Function: investforge-api-test")
        print(f"  📊 DynamoDB Tables: investforge-api-dev-users, investforge-api-dev-waitlist")
        print()
        print("🎯 Next Steps:")
        print("  1. Test the API in your browser or with curl")
        print("  2. Deploy the full serverless API with all endpoints")
        print("  3. Set up the frontend Streamlit application")
        print("  4. Configure domain and SSL")

if __name__ == "__main__":
    main()