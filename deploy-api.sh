#!/bin/bash

# InvestForge API Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 InvestForge API Deployment${NC}"
echo -e "${BLUE}=============================${NC}"
echo ""

# Set environment variables
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-dev-jwt-secret-key-$(date +%s)}"
export STRIPE_SECRET_KEY="${STRIPE_SECRET_KEY:-sk_test_placeholder}"
export STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-whsec_placeholder}"

echo -e "${BLUE}🔧 Setting up environment...${NC}"
echo "JWT_SECRET_KEY: ${JWT_SECRET_KEY:0:20}..."
echo "STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY:0:20}..."
echo ""

# Navigate to API directory
cd api

# Install Serverless Framework locally if not present
if [ ! -d "node_modules/.bin" ] || [ ! -f "node_modules/.bin/serverless" ]; then
    echo -e "${BLUE}📦 Installing Serverless Framework locally...${NC}"
    
    # Create package.json if it doesn't exist
    if [ ! -f "package.json" ]; then
        cat > package.json << 'EOF'
{
  "name": "investforge-api",
  "version": "1.0.0",
  "description": "InvestForge API",
  "scripts": {
    "deploy": "serverless deploy",
    "remove": "serverless remove"
  },
  "devDependencies": {
    "serverless": "^3.38.0",
    "serverless-python-requirements": "^6.0.0"
  }
}
EOF
    fi
    
    # Clean npm cache and install
    rm -rf node_modules
    npm cache clean --force 2>/dev/null || true
    npm install --no-fund --no-audit
fi

echo -e "${GREEN}✅ Serverless Framework ready${NC}"
echo ""

# Deploy using local serverless
echo -e "${BLUE}⚡ Deploying API...${NC}"
./node_modules/.bin/serverless deploy --config serverless-simple.yml --stage dev --verbose

# Get the API URL
API_URL=$(./node_modules/.bin/serverless info --config serverless-simple.yml --stage dev | grep -E "https://.*\.execute-api\." | head -1)

echo ""
echo -e "${GREEN}🎉 Deployment completed!${NC}"
echo ""
echo -e "${BLUE}📋 API Endpoints:${NC}"
echo -e "Base URL: ${GREEN}$API_URL${NC}"
echo -e "Health Check: ${GREEN}$API_URL/health${NC}"
echo -e "Signup: ${GREEN}$API_URL/auth/signup${NC}"
echo -e "Login: ${GREEN}$API_URL/auth/login${NC}"
echo -e "Waitlist: ${GREEN}$API_URL/waitlist/join${NC}"
echo ""

# Test the health endpoint
echo -e "${BLUE}🧪 Testing health endpoint...${NC}"
if curl -f -s "$API_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ Health endpoint is working!${NC}"
    
    # Test response
    echo -e "${BLUE}📄 Health response:${NC}"
    curl -s "$API_URL/health" | jq . || curl -s "$API_URL/health"
else
    echo -e "${YELLOW}⚠️  Health endpoint test failed${NC}"
fi

echo ""
echo -e "${BLUE}🧪 Test Commands:${NC}"
echo "curl $API_URL/health"
echo "curl -X POST $API_URL/waitlist/join -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\",\"source\":\"api_test\"}'"

cd ..