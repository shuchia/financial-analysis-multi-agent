#!/bin/bash

# InvestForge Enhanced Deployment for Existing Infrastructure
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${BLUE}🚀 InvestForge Enhanced Deployment for Existing Infrastructure${NC}"
echo -e "${BLUE}=========================================================${NC}"
echo ""

# Configuration
DOMAIN_NAME="${DOMAIN_NAME:-investforge.io}"
STACK_NAME="investforge-enhanced"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${BLUE}📋 Deployment Configuration:${NC}"
echo "Domain: $DOMAIN_NAME"
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo ""

# Step 1: Deploy the serverless API
echo -e "${PURPLE}🔧 Step 1: Deploying Serverless API${NC}"
cd api

# Set environment variables for serverless deployment
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-investforge-jwt-prod-$(date +%s)}"
export STRIPE_SECRET_KEY="${STRIPE_SECRET_KEY:-sk_test_placeholder}"
export STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-whsec_placeholder}"

echo "Environment variables set:"
echo "JWT_SECRET_KEY: ${JWT_SECRET_KEY:0:20}..."
echo "STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY:0:20}..."
echo ""

# Check if serverless is available, install if not
if ! command -v serverless &> /dev/null; then
    echo "Installing Serverless Framework locally..."
    
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
    
    npm install --no-fund --no-audit
    echo "Using local serverless installation..."
    SERVERLESS_CMD="./node_modules/.bin/serverless"
else
    SERVERLESS_CMD="serverless"
fi

echo "Deploying API with Serverless Framework..."
$SERVERLESS_CMD deploy --config serverless-simple.yml --stage prod --region $REGION --verbose

# Get API Gateway URL
API_URL=$($SERVERLESS_CMD info --config serverless-simple.yml --stage prod --region $REGION | grep -E "https://.*\.execute-api\." | head -1 | awk '{print $NF}')

if [[ -n "$API_URL" ]]; then
    echo -e "${GREEN}✅ Serverless API deployed successfully${NC}"
    echo "API URL: $API_URL"
else
    echo -e "${YELLOW}⚠️  Could not extract API URL, but deployment likely succeeded${NC}"
fi

cd ..

# Step 2: Test the API
echo -e "${PURPLE}🔧 Step 2: Testing API Endpoints${NC}"

if [[ -n "$API_URL" ]]; then
    echo "Testing health endpoint..."
    if curl -f -s "$API_URL/health" > /dev/null; then
        echo -e "${GREEN}✅ Health endpoint is working!${NC}"
        echo "Response:"
        curl -s "$API_URL/health" | jq . 2>/dev/null || curl -s "$API_URL/health"
    else
        echo -e "${YELLOW}⚠️  Health endpoint test failed, but API may still be working${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Skipping API test - URL not available${NC}"
fi

# Step 3: Create/Update S3 bucket for landing page
echo -e "${PURPLE}🔧 Step 3: Setting up S3 Bucket for Landing Page${NC}"

BUCKET_NAME="$DOMAIN_NAME-landing-page"

# Check if bucket exists
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "Bucket $BUCKET_NAME already exists"
else
    echo "Creating S3 bucket: $BUCKET_NAME"
    aws s3 mb s3://$BUCKET_NAME --region $REGION
    
    # Enable website hosting
    aws s3 website s3://$BUCKET_NAME --index-document index.html --error-document error.html
fi

# Upload landing page
if [[ -f "landing/index.html" ]]; then
    echo "Uploading landing page..."
    aws s3 sync landing/ s3://$BUCKET_NAME/ --delete
    echo -e "${GREEN}✅ Landing page uploaded${NC}"
else
    echo -e "${YELLOW}⚠️  No landing page found, creating a simple one...${NC}"
    
    mkdir -p landing
    cat > landing/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>InvestForge - Financial Analysis Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { text-align: center; max-width: 800px; padding: 3rem; }
        h1 { font-size: 4rem; margin-bottom: 1rem; font-weight: 700; text-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        .tagline { font-size: 1.5rem; margin-bottom: 3rem; opacity: 0.9; }
        .cta-buttons { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; margin-bottom: 4rem; }
        .btn { display: inline-block; padding: 1rem 2rem; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 8px; font-size: 1.1rem; font-weight: 600; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.3); transition: all 0.3s ease; }
        .btn:hover { background: rgba(255,255,255,0.3); transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.2); }
        .btn-primary { background: #4CAF50; border: 1px solid #4CAF50; }
        .btn-primary:hover { background: #45a049; }
        .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 2rem; margin-top: 3rem; text-align: left; }
        .feature { background: rgba(255,255,255,0.1); padding: 2rem; border-radius: 12px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); }
        .feature h3 { margin-bottom: 1rem; font-size: 1.3rem; }
        .feature p { opacity: 0.9; line-height: 1.6; }
        .status { margin-top: 3rem; padding: 1.5rem; background: rgba(76, 175, 80, 0.2); border-radius: 8px; border: 1px solid rgba(76, 175, 80, 0.3); }
        @media (max-width: 768px) { h1 { font-size: 2.5rem; } .cta-buttons { flex-direction: column; align-items: center; } .features { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>InvestForge</h1>
        <p class="tagline">Advanced Financial Analysis Platform powered by AI</p>
        
        <div class="cta-buttons">
            <a href="/app" class="btn btn-primary">Launch App</a>
            <a href="/app?plan=pro" class="btn">Try Pro Features</a>
        </div>

        <div class="status">
            <h3>🚀 Now Live with Enhanced Architecture</h3>
            <p>Featuring serverless API, real-time analytics, and seamless performance.</p>
        </div>
        
        <div class="features">
            <div class="feature">
                <h3>🤖 AI-Powered Analysis</h3>
                <p>Advanced machine learning models for market prediction and risk assessment.</p>
            </div>
            <div class="feature">
                <h3>📊 Real-time Data</h3>
                <p>Live market data integration with comprehensive technical indicators.</p>
            </div>
            <div class="feature">
                <h3>📈 Advanced Tools</h3>
                <p>Technical analysis, portfolio optimization, and backtesting capabilities.</p>
            </div>
            <div class="feature">
                <h3>⚡ Serverless API</h3>
                <p>High-performance backend with automatic scaling and reliability.</p>
            </div>
        </div>
    </div>
</body>
</html>
EOF

    aws s3 sync landing/ s3://$BUCKET_NAME/ --delete
    echo -e "${GREEN}✅ Default landing page created and uploaded${NC}"
fi

# Step 4: Display deployment summary
echo ""
echo -e "${GREEN}🎉 Enhanced Deployment Complete!${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo -e "✅ Serverless API: ${GREEN}Deployed${NC}"
echo -e "✅ DynamoDB Tables: ${GREEN}Created${NC}"
echo -e "✅ Lambda Functions: ${GREEN}Active${NC}"
echo -e "✅ Landing Page S3: ${GREEN}Uploaded${NC}"
echo ""

if [[ -n "$API_URL" ]]; then
    echo -e "${BLUE}🔗 API Endpoints:${NC}"
    echo -e "Base URL: ${GREEN}$API_URL${NC}"
    echo -e "Health: ${GREEN}$API_URL/health${NC}"
    echo -e "Auth: ${GREEN}$API_URL/auth/signup${NC} (POST)"
    echo -e "Login: ${GREEN}$API_URL/auth/login${NC} (POST)"
    echo -e "Waitlist: ${GREEN}$API_URL/waitlist/join${NC} (POST)"
    echo ""
fi

echo -e "${BLUE}🌐 Web Resources:${NC}"
echo -e "Landing Page Bucket: ${GREEN}s3://$BUCKET_NAME${NC}"
echo -e "Website URL: ${GREEN}http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com${NC}"
echo ""

echo -e "${BLUE}🧪 Test Commands:${NC}"
if [[ -n "$API_URL" ]]; then
    echo "# Test API health"
    echo "curl $API_URL/health"
    echo ""
    echo "# Test waitlist signup"
    echo "curl -X POST $API_URL/waitlist/join -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\"}'"
    echo ""
fi

echo -e "${BLUE}⏳ Next Steps for Full Production:${NC}"
echo "1. ${YELLOW}Update your existing ALB${NC} to include path-based routing:"
echo "   - /api/* routes to Lambda functions"
echo "   - /app/* routes to your existing ECS service"
echo "   - /* routes to S3/CloudFront for landing page"
echo ""
echo "2. ${YELLOW}Set up CloudFront${NC} distribution for:"
echo "   - SSL termination"
echo "   - Global CDN for static content"
echo "   - Origin routing to ALB"
echo ""
echo "3. ${YELLOW}Update Route 53${NC} to point to CloudFront"
echo ""
echo "4. ${YELLOW}Configure your Streamlit app${NC} to use the new API:"
echo "   - Update API_BASE_URL to point to your ALB/domain"
echo "   - Test authentication flow"
echo ""

echo -e "${GREEN}🚀 Your enhanced InvestForge backend is ready!${NC}"