#!/usr/bin/env python3
"""
Test script for the enhanced InvestForge deployment.
Tests API endpoints, S3 bucket, and validates the deployment.
"""

import boto3
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

def test_api_endpoints(base_url: str) -> Dict[str, Any]:
    """Test all API endpoints."""
    results = {}
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        results['health'] = {
            'status': response.status_code,
            'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            'success': response.status_code == 200
        }
    except Exception as e:
        results['health'] = {'error': str(e), 'success': False}
    
    # Test waitlist endpoint
    try:
        test_data = {
            'email': f'test-{int(time.time())}@example.com',
            'source': 'deployment_test'
        }
        response = requests.post(
            f"{base_url}/waitlist/join",
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        results['waitlist'] = {
            'status': response.status_code,
            'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            'success': response.status_code in [200, 201]
        }
    except Exception as e:
        results['waitlist'] = {'error': str(e), 'success': False}
    
    # Test signup endpoint
    try:
        test_data = {
            'email': f'testuser-{int(time.time())}@example.com',
            'password': 'TestPassword123!',
            'plan': 'free'
        }
        response = requests.post(
            f"{base_url}/auth/signup",
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        results['signup'] = {
            'status': response.status_code,
            'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            'success': response.status_code in [200, 201]
        }
    except Exception as e:
        results['signup'] = {'error': str(e), 'success': False}
    
    return results

def test_dynamodb_tables() -> Dict[str, Any]:
    """Test DynamoDB table accessibility."""
    dynamodb = boto3.resource('dynamodb')
    results = {}
    
    tables_to_check = [
        'investforge-api-prod-users',
        'investforge-api-prod-waitlist',
        'investforge-api-prod-analytics',
        'investforge-api-prod-usage'
    ]
    
    for table_name in tables_to_check:
        try:
            table = dynamodb.Table(table_name)
            # Try to describe the table
            table.load()
            results[table_name] = {
                'exists': True,
                'status': table.table_status,
                'item_count': table.item_count,
                'success': table.table_status == 'ACTIVE'
            }
        except Exception as e:
            results[table_name] = {'error': str(e), 'success': False}
    
    return results

def test_lambda_functions() -> Dict[str, Any]:
    """Test Lambda function deployment."""
    lambda_client = boto3.client('lambda')
    results = {}
    
    functions_to_check = [
        'investforge-api-prod-health',
        'investforge-api-prod-signup',
        'investforge-api-prod-login',
        'investforge-api-prod-join_waitlist',
        'investforge-api-prod-track_event',
        'investforge-api-prod-get_user'
    ]
    
    for function_name in functions_to_check:
        try:
            response = lambda_client.get_function(FunctionName=function_name)
            results[function_name] = {
                'state': response['Configuration']['State'],
                'runtime': response['Configuration']['Runtime'],
                'handler': response['Configuration']['Handler'],
                'success': response['Configuration']['State'] == 'Active'
            }
        except Exception as e:
            results[function_name] = {'error': str(e), 'success': False}
    
    return results

def test_s3_bucket(bucket_name: str) -> Dict[str, Any]:
    """Test S3 bucket and website hosting."""
    s3_client = boto3.client('s3')
    results = {}
    
    try:
        # Check if bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        results['bucket_exists'] = True
        
        # Check website configuration
        try:
            website_config = s3_client.get_bucket_website(Bucket=bucket_name)
            results['website_enabled'] = True
            results['index_document'] = website_config.get('IndexDocument', {}).get('Suffix')
        except:
            results['website_enabled'] = False
        
        # List some objects
        try:
            objects = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=10)
            results['object_count'] = objects.get('KeyCount', 0)
            results['objects'] = [obj['Key'] for obj in objects.get('Contents', [])]
        except:
            results['object_count'] = 0
            results['objects'] = []
        
        results['success'] = True
        
    except Exception as e:
        results = {'error': str(e), 'success': False}
    
    return results

def get_api_gateway_url() -> Optional[str]:
    """Get the API Gateway URL from AWS."""
    apigateway = boto3.client('apigateway')
    
    try:
        # Get all REST APIs
        apis = apigateway.get_rest_apis()
        
        # Look for InvestForge API
        for api in apis['items']:
            if 'investforge' in api['name'].lower():
                region = boto3.Session().region_name or 'us-east-1'
                return f"https://{api['id']}.execute-api.{region}.amazonaws.com/prod"
        
        return None
    except Exception as e:
        print(f"Error getting API Gateway URL: {e}")
        return None

def main():
    """Main test function."""
    print("🧪 InvestForge Enhanced Deployment Test")
    print("=" * 50)
    print()
    
    # Get current AWS account info
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"AWS Account: {identity['Account']}")
        print(f"Region: {boto3.Session().region_name or 'us-east-1'}")
        print()
    except Exception as e:
        print(f"❌ AWS credentials error: {e}")
        return
    
    # Test 1: Lambda Functions
    print("🔍 Testing Lambda Functions...")
    lambda_results = test_lambda_functions()
    for func_name, result in lambda_results.items():
        status = "✅" if result.get('success') else "❌"
        print(f"  {status} {func_name}: {result.get('state', result.get('error', 'Unknown'))}")
    print()
    
    # Test 2: DynamoDB Tables
    print("🔍 Testing DynamoDB Tables...")
    dynamodb_results = test_dynamodb_tables()
    for table_name, result in dynamodb_results.items():
        status = "✅" if result.get('success') else "❌"
        print(f"  {status} {table_name}: {result.get('status', result.get('error', 'Unknown'))}")
    print()
    
    # Test 3: API Gateway and Endpoints
    print("🔍 Testing API Gateway...")
    api_url = get_api_gateway_url()
    
    if api_url:
        print(f"API URL: {api_url}")
        api_results = test_api_endpoints(api_url)
        
        for endpoint, result in api_results.items():
            status = "✅" if result.get('success') else "❌"
            print(f"  {status} {endpoint}: HTTP {result.get('status', 'N/A')} - {result.get('response', result.get('error', 'Unknown'))}")
    else:
        print("❌ Could not find API Gateway URL")
        api_results = {}
    
    print()
    
    # Test 4: S3 Bucket
    print("🔍 Testing S3 Landing Page...")
    bucket_name = "investforge.io-landing-page"
    s3_results = test_s3_bucket(bucket_name)
    
    if s3_results.get('success'):
        print(f"  ✅ Bucket exists: {bucket_name}")
        print(f"  ✅ Website enabled: {s3_results.get('website_enabled')}")
        print(f"  ✅ Objects: {s3_results.get('object_count', 0)}")
        if s3_results.get('objects'):
            print(f"     Files: {', '.join(s3_results['objects'][:5])}")
    else:
        print(f"  ❌ S3 test failed: {s3_results.get('error', 'Unknown error')}")
    
    print()
    
    # Summary
    total_tests = 0
    passed_tests = 0
    
    for test_group in [lambda_results, dynamodb_results, api_results, {'s3': s3_results}]:
        for result in test_group.values():
            total_tests += 1
            if result.get('success'):
                passed_tests += 1
    
    print("📊 Test Summary")
    print("-" * 20)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print()
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Your enhanced InvestForge deployment is working correctly.")
    elif passed_tests > total_tests * 0.8:
        print("⚠️  Most tests passed. Check the failed items above.")
    else:
        print("❌ Multiple tests failed. Please review the deployment.")
    
    print()
    if api_url:
        print("🧪 Manual Test Commands:")
        print(f"curl {api_url}/health")
        print(f"curl -X POST {api_url}/waitlist/join -H 'Content-Type: application/json' -d '{{\"email\":\"your@email.com\"}}'")
        print(f"curl -X POST {api_url}/auth/signup -H 'Content-Type: application/json' -d '{{\"email\":\"test@example.com\",\"password\":\"TestPass123\"}}'")

if __name__ == "__main__":
    main()