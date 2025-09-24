#!/bin/bash

# InvestForge Quick Deployment Script (No Docker Required)
# This script deploys just the API and basic infrastructure for testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 InvestForge Quick Deployment${NC}"
echo -e "${BLUE}===============================${NC}"
echo ""

# Check AWS credentials
echo -e "${BLUE}🔑 Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")
echo -e "${GREEN}✅ AWS credentials verified (Account: $ACCOUNT_ID, Region: $REGION)${NC}"
echo ""

# Step 1: Deploy the API only (serverless)
echo -e "${BLUE}⚡ Deploying serverless API...${NC}"
cd api

# Check if Node.js is available
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm not found. Please install Node.js first${NC}"
    exit 1
fi

# Install dependencies
echo "Installing npm dependencies..."
npm install

# Set environment variables for development
export JWT_SECRET_KEY="dev-jwt-secret-key-change-in-production-$(date +%s)"
export STRIPE_SECRET_KEY="sk_test_placeholder"
export STRIPE_WEBHOOK_SECRET="whsec_placeholder"

echo "Deploying API with stage 'dev'..."
npx serverless deploy --stage dev --verbose

cd ..

echo ""
echo -e "${GREEN}✅ API deployment completed!${NC}"

# Get API Gateway URL
API_URL=$(cd api && npx serverless info --stage dev | grep "ServiceEndpoint:" | awk '{print $2}')

echo ""
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo -e "API URL: ${GREEN}$API_URL${NC}"
echo ""
echo -e "${BLUE}🧪 Test the API:${NC}"
echo "curl $API_URL/health"
echo "curl -X POST $API_URL/waitlist/join -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\",\"source\":\"test\"}'"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Test the API endpoints"
echo "2. If working, proceed with full infrastructure deployment"
echo "3. Install Docker for container deployment"
echo "4. Set up proper environment variables"

# Test the health endpoint
echo ""
echo -e "${BLUE}🧪 Testing health endpoint...${NC}"
if curl -f -s "$API_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ Health endpoint is working!${NC}"
else
    echo -e "${YELLOW}⚠️  Health endpoint test failed (this might be expected)${NC}"
fi