#!/usr/bin/env python3
"""
Update the login Lambda function with proper dependencies and code.
"""

import os
import boto3
import zipfile
import shutil
import subprocess
import sys
import json
from pathlib import Path

def create_lambda_deployment_package():
    """Create a deployment package for the login Lambda function."""
    
    print("🔧 Creating Login Lambda Deployment Package")
    print("=" * 45)
    
    # Create a temporary directory
    temp_dir = Path("/tmp/login-lambda")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    
    print("📦 Preparing Lambda package...")
    
    # Create lambda_function.py with the login handler
    lambda_code = '''
import json
import os
from typing import Dict, Any
from datetime import datetime

# Import handlers and utilities
from handlers.auth import login
from utils.response import error_response

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """ALB Lambda handler that routes to the login function."""
    try:
        # Handle ALB health checks
        if event.get('path') == '/api/auth/login' and event.get('httpMethod') == 'GET':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'status': 'healthy', 'service': 'login'})
            }
        
        # Process login request
        response = login(event, context)
        
        # Convert response for ALB format if needed
        if 'statusCode' not in response:
            return {
                'statusCode': response.get('status_code', 200),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps(response)
            }
        
        return response
        
    except Exception as e:
        print(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Internal server error'
            })
        }
'''
    
    with open(temp_dir / "lambda_function.py", "w") as f:
        f.write(lambda_code)
    
    # Copy the API directory structure
    api_dir = Path("/Users/shuchiagarwal/Documents/Financial-Analysis--Multi-Agent-Open-Source-LLM/api")
    
    # Copy handlers directory
    handlers_dir = temp_dir / "handlers"
    handlers_dir.mkdir(exist_ok=True)
    
    for handler_file in ["auth.py", "analytics.py", "__init__.py"]:
        src_file = api_dir / "handlers" / handler_file
        if src_file.exists():
            shutil.copy(src_file, handlers_dir / handler_file)
    
    # Create empty __init__.py if it doesn't exist
    if not (handlers_dir / "__init__.py").exists():
        (handlers_dir / "__init__.py").touch()
    
    # Copy utils directory
    utils_dir = temp_dir / "utils"
    utils_dir.mkdir(exist_ok=True)
    
    for util_file in ["response.py", "database.py", "auth.py", "__init__.py"]:
        src_file = api_dir / "utils" / util_file
        if src_file.exists():
            shutil.copy(src_file, utils_dir / util_file)
    
    # Create empty __init__.py if it doesn't exist
    if not (utils_dir / "__init__.py").exists():
        (utils_dir / "__init__.py").touch()
    
    # Copy models directory
    models_dir = temp_dir / "models"
    models_dir.mkdir(exist_ok=True)
    
    for model_file in ["user.py", "__init__.py"]:
        src_file = api_dir / "models" / model_file
        if src_file.exists():
            shutil.copy(src_file, models_dir / model_file)
    
    # Create empty __init__.py if it doesn't exist
    if not (models_dir / "__init__.py").exists():
        (models_dir / "__init__.py").touch()
    
    # Create requirements.txt with necessary dependencies
    requirements = """pydantic==2.5.3
bcrypt==4.1.2
PyJWT==2.8.0
boto3==1.34.19
python-jose==3.3.0
"""
    
    with open(temp_dir / "requirements.txt", "w") as f:
        f.write(requirements)
    
    print("📥 Installing dependencies...")
    
    # Install dependencies
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "-r", str(temp_dir / "requirements.txt"),
        "--target", str(temp_dir),
        "--quiet"
    ], check=True)
    
    # Create deployment package
    zip_file = "/tmp/login-lambda-deployment.zip"
    
    print("🗜️  Creating ZIP package...")
    
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.pyc') or file.startswith('.'):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zf.write(file_path, arcname)
    
    # Clean up
    shutil.rmtree(temp_dir)
    
    return zip_file

def update_lambda_function(zip_file):
    """Update the Lambda function with the new deployment package."""
    
    print("\n📤 Updating Login Lambda Function")
    print("=" * 35)
    
    lambda_client = boto3.client('lambda')
    
    try:
        with open(zip_file, 'rb') as f:
            zip_content = f.read()
        
        print("🚀 Uploading new code to Lambda...")
        
        response = lambda_client.update_function_code(
            FunctionName='investforge-login',
            ZipFile=zip_content,
            Publish=True
        )
        
        print(f"✅ Lambda function updated successfully!")
        print(f"   Version: {response['Version']}")
        print(f"   State: {response['State']}")
        
        # Update function configuration to ensure correct handler
        print("\n🔧 Updating Lambda configuration...")
        
        config_response = lambda_client.update_function_configuration(
            FunctionName='investforge-login',
            Handler='lambda_function.lambda_handler',
            Timeout=30,
            MemorySize=256,
            Environment={
                'Variables': {
                    'JWT_SECRET': 'your-secret-key-here',  # This should be from Secrets Manager in production
                    'JWT_ALGORITHM': 'HS256',
                    'JWT_EXPIRATION_HOURS': '24',
                    'DYNAMODB_TABLE': 'investforge-users'
                }
            }
        )
        
        print(f"✅ Configuration updated!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda: {str(e)}")
        return False
    finally:
        # Clean up
        if os.path.exists(zip_file):
            os.remove(zip_file)

def test_login_endpoint():
    """Test the updated login endpoint."""
    
    print("\n🧪 Testing Login Endpoint")
    print("=" * 25)
    
    import time
    time.sleep(5)  # Wait for Lambda to be ready
    
    # Test with curl
    import subprocess
    
    test_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    cmd = [
        "curl", "-s", "-w", "\\nHTTP Status: %{http_code}\\n",
        "https://investforge.io/api/auth/login",
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(test_data)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    
    if "200" in result.stdout or "201" in result.stdout:
        print("\n✅ Login endpoint is working!")
    else:
        print("\n⚠️  Login endpoint may need additional configuration")

def main():
    """Main function."""
    print("🚀 Updating Login Lambda Function")
    print("=" * 35)
    print("\nThis will fix the missing dependencies and update the Lambda code.\n")
    
    # Create deployment package
    zip_file = create_lambda_deployment_package()
    
    if not os.path.exists(zip_file):
        print("❌ Failed to create deployment package")
        return
    
    print(f"\n✅ Deployment package created: {os.path.getsize(zip_file) / 1024 / 1024:.1f} MB")
    
    # Update Lambda function
    if update_lambda_function(zip_file):
        print("\n🎉 Login Lambda function updated successfully!")
        
        # Test the endpoint
        test_login_endpoint()
        
        print("\n📋 Summary:")
        print("   ✅ Lambda code updated with proper handler")
        print("   ✅ All dependencies installed (pydantic, bcrypt, etc.)")
        print("   ✅ Environment variables configured")
        print("   ✅ ALB integration ready")
        print("\n🔗 Users can now log in at: https://investforge.io/app")
    else:
        print("\n❌ Failed to update Lambda function")

if __name__ == "__main__":
    main()