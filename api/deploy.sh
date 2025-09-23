#!/bin/bash

# InvestForge API Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
STAGE="dev"
REGION="us-east-1"
PROFILE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stage)
            STAGE="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -s, --stage     Deployment stage (dev, staging, prod) [default: dev]"
            echo "  -r, --region    AWS region [default: us-east-1]"
            echo "  -p, --profile   AWS profile to use"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🚀 InvestForge API Deployment${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "Stage: ${YELLOW}$STAGE${NC}"
echo -e "Region: ${YELLOW}$REGION${NC}"
if [ ! -z "$PROFILE" ]; then
    echo -e "Profile: ${YELLOW}$PROFILE${NC}"
fi
echo ""

# Check if required tools are installed
echo -e "${BLUE}🔍 Checking dependencies...${NC}"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm is not installed${NC}"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dependencies check passed${NC}"
echo ""

# Check AWS credentials
echo -e "${BLUE}🔑 Checking AWS credentials...${NC}"

AWS_CMD="aws"
if [ ! -z "$PROFILE" ]; then
    AWS_CMD="aws --profile $PROFILE"
fi

if ! $AWS_CMD sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Please run 'aws configure' or set up your credentials"
    exit 1
fi

ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS credentials verified (Account: $ACCOUNT_ID)${NC}"
echo ""

# Install Node.js dependencies
echo -e "${BLUE}📦 Installing Node.js dependencies...${NC}"
if ! npm install; then
    echo -e "${RED}❌ Failed to install Node.js dependencies${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Node.js dependencies installed${NC}"
echo ""

# Install Python dependencies locally for validation
echo -e "${BLUE}🐍 Validating Python dependencies...${NC}"
if ! python3 -c "import boto3, pydantic, stripe"; then
    echo -e "${YELLOW}⚠️  Some Python dependencies missing locally (this is OK for deployment)${NC}"
fi
echo ""

# Validate environment variables for production
if [ "$STAGE" = "prod" ]; then
    echo -e "${BLUE}🔐 Validating production environment...${NC}"
    
    if [ -z "$JWT_SECRET_KEY" ]; then
        echo -e "${RED}❌ JWT_SECRET_KEY not set for production${NC}"
        exit 1
    fi
    
    if [ -z "$STRIPE_SECRET_KEY" ]; then
        echo -e "${RED}❌ STRIPE_SECRET_KEY not set for production${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Production environment validated${NC}"
    echo ""
fi

# Run linting (if available)
echo -e "${BLUE}🔍 Running code quality checks...${NC}"
if command -v flake8 &> /dev/null; then
    if flake8 handlers/ utils/ models/ --max-line-length=100 --ignore=E203,W503; then
        echo -e "${GREEN}✅ Code quality checks passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Code quality issues found (continuing anyway)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  flake8 not installed, skipping code quality checks${NC}"
fi
echo ""

# Deploy with Serverless Framework
echo -e "${BLUE}🚀 Deploying to AWS...${NC}"
echo -e "${YELLOW}This may take several minutes...${NC}"
echo ""

DEPLOY_CMD="npx sls deploy --stage $STAGE --region $REGION"
if [ ! -z "$PROFILE" ]; then
    DEPLOY_CMD="$DEPLOY_CMD --aws-profile $PROFILE"
fi

if $DEPLOY_CMD; then
    echo ""
    echo -e "${GREEN}🎉 Deployment successful!${NC}"
    echo ""
    
    # Get API Gateway URL
    API_URL=$(npx sls info --stage $STAGE --region $REGION --verbose | grep "ServiceEndpoint:" | awk '{print $2}')
    if [ ! -z "$API_URL" ]; then
        echo -e "${BLUE}📡 API Endpoint:${NC} $API_URL"
    fi
    
    echo ""
    echo -e "${BLUE}📋 Next Steps:${NC}"
    echo "1. Update your frontend API_BASE_URL to: $API_URL"
    echo "2. Configure Stripe webhook URL: $API_URL/stripe/webhook"
    echo "3. Verify SES domain/email addresses in AWS Console"
    echo "4. Test the API endpoints"
    echo ""
    echo -e "${GREEN}✅ InvestForge API is now live on $STAGE environment!${NC}"
    
else
    echo ""
    echo -e "${RED}❌ Deployment failed${NC}"
    echo "Check the error messages above for details."
    exit 1
fi