#!/bin/bash

# =====================================
# Deploy CodePipeline for InvestForge
# =====================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}InvestForge CI/CD Pipeline Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Configuration
STACK_NAME="investforge-cicd"
REGION="us-east-1"
TEMPLATE_FILE="infrastructure/codepipeline.yml"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not configured properly${NC}"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account ID: ${AWS_ACCOUNT_ID}${NC}"

# Parameters
read -p "Enter GitHub Repository Owner (default: shuchia): " GITHUB_OWNER
GITHUB_OWNER=${GITHUB_OWNER:-shuchia}

read -p "Enter GitHub Repository Name (default: financial-analysis-multi-agent): " GITHUB_REPO
GITHUB_REPO=${GITHUB_REPO:-financial-analysis-multi-agent}

read -p "Enter GitHub Branch (default: main): " GITHUB_BRANCH
GITHUB_BRANCH=${GITHUB_BRANCH:-main}

read -p "Enter Notification Email: " NOTIFICATION_EMAIL

read -p "Enter Environment (dev/staging/prod, default: prod): " ENVIRONMENT
ENVIRONMENT=${ENVIRONMENT:-prod}

echo ""
echo -e "${YELLOW}Deploying with the following configuration:${NC}"
echo "  Stack Name: $STACK_NAME"
echo "  Region: $REGION"
echo "  GitHub: $GITHUB_OWNER/$GITHUB_REPO (branch: $GITHUB_BRANCH)"
echo "  Environment: $ENVIRONMENT"
echo "  Notification Email: $NOTIFICATION_EMAIL"
echo ""

read -p "Continue with deployment? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Deploy CloudFormation stack
echo ""
echo -e "${GREEN}Deploying CloudFormation stack...${NC}"

aws cloudformation deploy \
    --template-file $TEMPLATE_FILE \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        GitHubOwner=$GITHUB_OWNER \
        GitHubRepo=$GITHUB_REPO \
        GitHubBranch=$GITHUB_BRANCH \
        NotificationEmail=$NOTIFICATION_EMAIL \
    --region $REGION \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Pipeline deployed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    # Get outputs
    PIPELINE_NAME=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query "Stacks[0].Outputs[?OutputKey=='PipelineName'].OutputValue" \
        --output text)

    PIPELINE_URL=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query "Stacks[0].Outputs[?OutputKey=='PipelineUrl'].OutputValue" \
        --output text)

    GITHUB_CONNECTION_ARN=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query "Stacks[0].Outputs[?OutputKey=='GitHubConnectionArn'].OutputValue" \
        --output text)

    echo -e "${YELLOW}Pipeline Name:${NC} $PIPELINE_NAME"
    echo -e "${YELLOW}Pipeline URL:${NC} $PIPELINE_URL"
    echo ""

    echo -e "${YELLOW}⚠️  IMPORTANT: GitHub Connection Setup Required${NC}"
    echo ""
    echo "The GitHub connection has been created but needs to be activated:"
    echo ""
    echo "1. Go to AWS Console → Developer Tools → Connections"
    echo "   URL: https://console.aws.amazon.com/codesuite/settings/connections?region=$REGION"
    echo ""
    echo "2. Find the connection: ${STACK_NAME}-github-connection"
    echo "   ARN: $GITHUB_CONNECTION_ARN"
    echo ""
    echo "3. Click 'Update pending connection'"
    echo "4. Complete the GitHub OAuth flow to authorize AWS"
    echo "5. Once connected, the pipeline will automatically trigger on new commits"
    echo ""
    echo -e "${GREEN}After activating the connection, push to main branch to trigger the pipeline!${NC}"
    echo ""

    # Check if email needs confirmation
    echo -e "${YELLOW}📧 Email Notification Setup${NC}"
    echo "Check your email ($NOTIFICATION_EMAIL) and confirm the SNS subscription"
    echo "to receive pipeline status notifications."
    echo ""

else
    echo -e "${RED}✗ Deployment failed${NC}"
    exit 1
fi
