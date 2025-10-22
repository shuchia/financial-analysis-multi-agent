#!/bin/bash

# Deploy Landing Page to S3
set -e

echo "🚀 Deploying Landing Page to S3"
echo "======================================"

# Configuration
BUCKET_NAME="investforge-simple-landing"
DISTRIBUTION_ID="E9A4E00CLHHQQ"
LANDING_DIR="./landing"

# Check if landing directory exists
if [ ! -d "$LANDING_DIR" ]; then
    echo "❌ Error: Landing directory not found at $LANDING_DIR"
    exit 1
fi

echo "📦 Syncing files to S3 bucket: $BUCKET_NAME"
aws s3 sync "$LANDING_DIR" "s3://$BUCKET_NAME" \
    --delete \
    --cache-control "max-age=3600" \
    --exclude "*.DS_Store"

echo ""
echo "✅ Files uploaded to S3"

echo ""
echo "🔄 Creating CloudFront invalidation to clear cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/*" \
  --query "Invalidation.Id" \
  --output text)

echo "✅ Invalidation created: $INVALIDATION_ID"

echo ""
echo "⏳ Checking invalidation status..."
aws cloudfront get-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --id "$INVALIDATION_ID" \
  --query "Invalidation.Status" \
  --output text

echo ""
echo "🌐 Landing page URLs:"
echo "   - https://investforge.io/"
echo "   - https://d2u8inxjroivr9.cloudfront.net/"

echo ""
echo "📋 Note: CloudFront invalidation may take 5-15 minutes to complete globally"

echo ""
echo "✅ Landing page deployment completed!"
