#!/bin/bash

# Fix S3 Landing Page CloudFront Configuration
set -e

echo "🔧 Fixing S3 Landing Page Configuration"
echo "======================================"

# Configuration
BUCKET_NAME="investforge-simple-landing"
DISTRIBUTION_ID="E9A4E00CLHHQQ"

echo "📋 Checking current CloudFront distribution status..."
aws cloudfront get-distribution --id "$DISTRIBUTION_ID" --query "Distribution.Status" --output text

echo ""
echo "🔍 Checking S3 bucket policy..."
aws s3api get-bucket-policy --bucket "$BUCKET_NAME" --query "Policy" --output text | jq .

echo ""
echo "🧪 Testing S3 bucket direct access (should fail - this is correct)..."
curl -s -w "HTTP Status: %{http_code}\n" "https://${BUCKET_NAME}.s3.amazonaws.com/index.html" | head -2

echo ""
echo "🧪 Testing CloudFront S3 access..."
curl -s -w "HTTP Status: %{http_code}\n" "https://d2u8inxjroivr9.cloudfront.net/" | head -5

echo ""
echo "🔧 If still getting 403, let's fix the bucket policy..."

# Recreate the correct bucket policy
cat > s3-policy-final.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontServicePrincipal",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::453636587892:distribution/${DISTRIBUTION_ID}"
        }
      }
    }
  ]
}
EOF

aws s3api put-bucket-policy --bucket "$BUCKET_NAME" --policy file://s3-policy-final.json
rm s3-policy-final.json

echo "✅ Updated S3 bucket policy"

echo ""
echo "🔄 Creating CloudFront invalidation to clear cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/*" \
  --query "Invalidation.Id" \
  --output text)

echo "✅ Invalidation created: $INVALIDATION_ID"

echo ""
echo "⏳ Waiting 2 minutes for invalidation to process..."
sleep 120

echo ""
echo "🧪 Testing landing page after fixes..."
echo "1. Testing investforge.io root:"
curl -s -w "HTTP Status: %{http_code}\n" "https://investforge.io/" | head -5

echo ""
echo "2. Testing CloudFront direct:"
curl -s -w "HTTP Status: %{http_code}\n" "https://d2u8inxjroivr9.cloudfront.net/" | head -5

echo ""
echo "📋 If still not working, manual steps:"
echo "1. Wait 5-10 more minutes for CloudFront propagation"
echo "2. Check AWS Console → CloudFront → E9A4E00CLHHQQ → Origins"
echo "3. Ensure S3 origin has Origin Access Control enabled"

echo ""
echo "✅ S3 Landing Page fix completed!"