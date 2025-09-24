#!/bin/bash

# Simple fix for Streamlit static assets
echo "🔧 Fixing Streamlit Static Assets - Simple Approach"
echo "=================================================="

echo "📋 The issue: Streamlit static assets are being blocked by CloudFront"
echo "    Error: GET https://investforge.io/static/media/SourceSansVF-Upright.ttf.BsWL4Kly.woff2 403 (Forbidden)"
echo ""

echo "🔍 Analysis:"
echo "   ✅ Your Dockerfile has correct baseUrlPath=/app"
echo "   ❌ CloudFront is not routing /static/* to ALB"
echo ""

echo "🧪 Testing current static asset access:"
echo "1. Testing static asset directly through ALB:"
curl -s -w "HTTP Status: %{http_code}\n" "https://financial-analysis-alb-161240.us-east-1.elb.amazonaws.com/static/media/SourceSansVF-Upright.ttf.BsWL4Kly.woff2" | head -2

echo ""
echo "2. Testing static asset through CloudFront:"
curl -s -w "HTTP Status: %{http_code}\n" "https://investforge.io/static/media/SourceSansVF-Upright.ttf.BsWL4Kly.woff2" | head -2

echo ""
echo "3. Testing Streamlit health endpoint:"
curl -s -w "HTTP Status: %{http_code}\n" "https://investforge.io/app/health" | head -2

echo ""
echo "🔧 SOLUTION OPTIONS:"
echo "==================="
echo ""

echo "Option 1: Quick Fix - Update Streamlit to serve from /app/static"
echo "  Problem: Static assets are served from root /static/, not /app/static/"
echo "  Solution: Configure Streamlit to serve assets under the base path"
echo ""

echo "Option 2: CloudFront Behavior Fix (Manual)"
echo "  Go to AWS Console → CloudFront → Distribution E9A4E00CLHHQQ"
echo "  Add behavior: Path /static/* → ALB Origin"
echo "  Add behavior: Path /_stcore/* → ALB Origin"
echo ""

echo "Option 3: Test with baseUrlPath fix in Streamlit config"
echo ""

echo "🧪 Let's test if the issue is actually the assets or something else:"
echo "Testing if the app loads at all..."

# Check if the app is accessible and what the actual error is
echo ""
echo "4. Full app test:"
curl -s "https://investforge.io/app" | grep -E "(error|Error|403|404)" | head -5 || echo "No obvious errors in HTML"

echo ""
echo "5. Testing if static assets work when accessed correctly:"
curl -s -w "HTTP Status: %{http_code}\n" "https://investforge.io/app/_stcore/static/media/SourceSansVF-Upright.ttf.BsWL4Kly.woff2" | head -2

echo ""
echo "📋 RECOMMENDED IMMEDIATE FIX:"
echo "============================="
echo ""
echo "The quickest fix is to add CloudFront cache behaviors for static assets."
echo "Since the automated approach failed, here's the manual steps:"
echo ""
echo "1. Go to AWS Console → CloudFront → Distribution E9A4E00CLHHQQ"
echo "2. Go to Behaviors tab → Create behavior"
echo "3. Add these behaviors:"
echo ""
echo "   Behavior 1:"
echo "   - Path pattern: /static/*"
echo "   - Origin: ALB-investforge"
echo "   - Cache policy: CachingDisabled"
echo "   - Origin request policy: CORS-S3Origin or AllViewer"
echo ""
echo "   Behavior 2:"
echo "   - Path pattern: /_stcore/*"
echo "   - Origin: ALB-investforge"
echo "   - Cache policy: CachingOptimized"
echo "   - Origin request policy: CORS-S3Origin or AllViewer"
echo ""
echo "4. Save and wait 5-10 minutes for propagation"
echo ""
echo "🔄 Alternative: Force refresh your ECS service to pick up any config changes:"
aws ecs update-service --cluster financial-analysis-cluster --service financial-analysis-service --force-new-deployment 2>/dev/null || echo "⚠️  No service found (might be running as standalone task)"

echo ""
echo "✅ After making these changes, test: https://investforge.io/app"