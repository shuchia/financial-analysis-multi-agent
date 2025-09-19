#!/bin/bash

# AWS App Runner Deployment Script for Financial Analysis Multi-Agent App
set -e

# Configuration
SERVICE_NAME="financial-analysis-app"
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
GITHUB_REPO_URL="https://github.com/shuchia/financial-analysis-multi-agent"
BRANCH_NAME="main"

echo "🚀 Starting AWS App Runner deployment for $SERVICE_NAME"
echo "📍 Region: $AWS_REGION"
echo "🔗 Repository: $GITHUB_REPO_URL"
echo "🌿 Branch: $BRANCH_NAME"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if user is authenticated
echo "🔐 Checking AWS authentication..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS authentication failed. Please run 'aws configure' first."
    exit 1
fi

echo "✅ AWS authentication successful"

# Check if service already exists
echo "🔍 Checking if App Runner service already exists..."
if aws apprunner describe-service --service-arn "arn:aws:apprunner:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):service/$SERVICE_NAME" &> /dev/null; then
    echo "⚠️  Service $SERVICE_NAME already exists."
    echo "To update the service, please use the AWS Console or update the existing service."
    echo "Deployment URL: https://console.aws.amazon.com/apprunner/home?region=$AWS_REGION#/services"
    exit 0
fi

# Create App Runner service
echo "📦 Creating App Runner service..."

# Note: This is a template - you'll need to configure GitHub connection first
cat << EOF
⚠️  MANUAL SETUP REQUIRED:

Before running this script, you need to:

1. Create a GitHub connection in AWS App Runner:
   - Go to https://console.aws.amazon.com/apprunner/home?region=$AWS_REGION#/connections
   - Click "Create connection"
   - Choose "GitHub" 
   - Authorize the connection

2. Update this script with your GitHub connection ARN

3. Alternatively, use the AWS Console to create the service:
   - Go to https://console.aws.amazon.com/apprunner/home?region=$AWS_REGION#/create
   - Choose "Source code repository"
   - Select your GitHub connection
   - Repository: $GITHUB_REPO_URL
   - Branch: $BRANCH_NAME
   - Configuration: Automatic (uses apprunner.yaml)

EOF

echo "📋 Service configuration ready. Please complete setup via AWS Console."
echo "🔗 App Runner Console: https://console.aws.amazon.com/apprunner/home?region=$AWS_REGION"
echo "📖 Full deployment guide: DEPLOYMENT.md"

echo "✅ Deployment script completed!"