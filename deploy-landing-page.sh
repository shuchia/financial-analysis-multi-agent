#!/bin/bash

# Deploy Landing Page to S3
set -e

echo "🚀 Deploying InvestForge Landing Page to S3"
echo "==========================================="

# Configuration
BUCKET_NAME="investforge-simple-landing"
DISTRIBUTION_ID="E9A4E00CLHHQQ"
REGION="us-east-1"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${BLUE}📋 Configuration:${NC}"
echo "Bucket: $BUCKET_NAME"
echo "CloudFront Distribution: $DISTRIBUTION_ID"
echo "Region: $REGION"
echo ""

# Sync landing page to S3
echo -e "${BLUE}📤 Uploading landing page files to S3...${NC}"
aws s3 sync landing/ s3://$BUCKET_NAME/ \
    --delete \
    --region $REGION \
    --cache-control "public, max-age=3600" \
    --exclude "*.DS_Store"

echo -e "${GREEN}✅ Files uploaded to S3${NC}"
echo ""

# Invalidate CloudFront cache
echo -e "${BLUE}🔄 Creating CloudFront invalidation...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*" \
    --query "Invalidation.Id" \
    --output text)

echo -e "${GREEN}✅ CloudFront invalidation created: $INVALIDATION_ID${NC}"
echo ""

# Check invalidation status
echo -e "${YELLOW}⏳ Checking invalidation status...${NC}"
aws cloudfront wait invalidation-completed \
    --distribution-id "$DISTRIBUTION_ID" \
    --id "$INVALIDATION_ID" &

echo ""
echo -e "${GREEN}🎉 Landing page deployment initiated!${NC}"
echo ""
echo "📍 Your landing page will be live at:"
echo "   https://investforge.io/"
echo "   https://d2u8inxjroivr9.cloudfront.net/"
echo ""
echo -e "${YELLOW}⏳ Note: CloudFront invalidation may take 2-5 minutes to complete.${NC}"
echo ""
echo "✅ Deployment complete!"
