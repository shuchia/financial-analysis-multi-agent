#!/bin/bash

# Add CloudFront behaviors for static assets using AWS CLI
set -e

echo "🔧 Adding CloudFront Behaviors for Static Assets"
echo "==============================================="

DISTRIBUTION_ID="E9A4E00CLHHQQ"

echo "📋 Distribution ID: $DISTRIBUTION_ID"
echo ""

# Get current distribution configuration
echo "1️⃣ Getting current CloudFront configuration..."
aws cloudfront get-distribution-config --id "$DISTRIBUTION_ID" > current-dist-config.json

if [ ! -f "current-dist-config.json" ]; then
    echo "❌ Failed to get distribution config"
    exit 1
fi

ETAG=$(jq -r '.ETag' current-dist-config.json)
echo "✅ Current ETag: $ETAG"

# Extract the distribution config
jq '.DistributionConfig' current-dist-config.json > dist-config.json

echo ""
echo "2️⃣ Adding /static/* cache behavior..."

# Add /static/* behavior
jq '.CacheBehaviors.Items += [{
  "PathPattern": "/static/*",
  "TargetOriginId": "ALB-investforge",
  "ViewerProtocolPolicy": "redirect-to-https",
  "AllowedMethods": {
    "Quantity": 3,
    "Items": ["GET", "HEAD", "OPTIONS"],
    "CachedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"]
    }
  },
  "ForwardedValues": {
    "QueryString": false,
    "Cookies": {"Forward": "none"},
    "Headers": {
      "Quantity": 3,
      "Items": ["Host", "Origin", "Referer"]
    }
  },
  "TrustedSigners": {
    "Enabled": false,
    "Quantity": 0
  },
  "MinTTL": 86400,
  "DefaultTTL": 86400,
  "MaxTTL": 31536000,
  "Compress": true
}] | .CacheBehaviors.Quantity = (.CacheBehaviors.Items | length)' dist-config.json > dist-config-updated.json

echo ""
echo "3️⃣ Adding /_stcore/* cache behavior..."

# Add /_stcore/* behavior
jq '.CacheBehaviors.Items += [{
  "PathPattern": "/_stcore/*", 
  "TargetOriginId": "ALB-investforge",
  "ViewerProtocolPolicy": "redirect-to-https",
  "AllowedMethods": {
    "Quantity": 3,
    "Items": ["GET", "HEAD", "OPTIONS"],
    "CachedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"]
    }
  },
  "ForwardedValues": {
    "QueryString": false,
    "Cookies": {"Forward": "none"},
    "Headers": {
      "Quantity": 3,
      "Items": ["Host", "Origin", "Referer"]
    }
  },
  "TrustedSigners": {
    "Enabled": false,
    "Quantity": 0
  },
  "MinTTL": 86400,
  "DefaultTTL": 86400,
  "MaxTTL": 31536000,
  "Compress": true
}] | .CacheBehaviors.Quantity = (.CacheBehaviors.Items | length)' dist-config-updated.json > dist-config-final.json

echo ""
echo "4️⃣ Updating CloudFront distribution..."

# Update the distribution
aws cloudfront update-distribution \
    --id "$DISTRIBUTION_ID" \
    --distribution-config file://dist-config-final.json \
    --if-match "$ETAG"

echo "✅ CloudFront distribution updated!"

echo ""
echo "5️⃣ Creating invalidation for static assets..."

# Create invalidation
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/static/*" "/_stcore/*" "/app*" \
    --query "Invalidation.Id" \
    --output text)

echo "✅ Invalidation created: $INVALIDATION_ID"

# Clean up temp files
rm -f current-dist-config.json dist-config.json dist-config-updated.json dist-config-final.json

echo ""
echo "⏳ CloudFront is updating (takes 5-10 minutes)..."
echo ""
echo "🧪 After 5-10 minutes, test:"
echo "   https://investforge.io/app"
echo "   The static asset errors should be resolved!"
echo ""
echo "📋 What was fixed:"
echo "   ✅ Added /static/* → ALB routing"
echo "   ✅ Added /_stcore/* → ALB routing"
echo "   ✅ Cleared CloudFront cache"
echo ""
echo "🎉 Static assets should now load properly!"