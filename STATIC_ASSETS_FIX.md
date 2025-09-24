# 🔧 Fix for Streamlit Static Assets 403 Error

## Problem
When accessing `https://investforge.io/app`, you get:
```
GET https://investforge.io/static/media/SourceSansVF-Upright.ttf.BsWL4Kly.woff2 net::ERR_ABORTED 403 (Forbidden)
```

## Root Cause
CloudFront is not configured to route `/static/*` and `/_stcore/*` paths to the ALB. These paths default to the S3 origin, which returns 403.

## ✅ **SOLUTION: Manual CloudFront Configuration**

### Step 1: Access AWS Console
1. Go to [AWS CloudFront Console](https://console.aws.amazon.com/cloudfront)
2. Find distribution `E9A4E00CLHHQQ`
3. Click on the distribution ID

### Step 2: Add Cache Behaviors
1. Go to **Behaviors** tab
2. Click **Create behavior**

### Step 3: Add /static/* Behavior
**Create Behavior 1:**
- **Path pattern**: `/static/*`
- **Origin and origin groups**: Select `ALB-investforge` (the ALB origin)
- **Viewer protocol policy**: Redirect HTTP to HTTPS
- **Allowed HTTP methods**: GET, HEAD, OPTIONS
- **Cache policy**: CachingDisabled (or create custom)
- **Origin request policy**: AllViewer
- **Response headers policy**: None
- **Compress objects automatically**: Yes

Click **Create behavior**

### Step 4: Add /_stcore/* Behavior  
**Create Behavior 2:**
- **Path pattern**: `/_stcore/*`
- **Origin and origin groups**: Select `ALB-investforge` (the ALB origin)
- **Viewer protocol policy**: Redirect HTTP to HTTPS
- **Allowed HTTP methods**: GET, HEAD, OPTIONS
- **Cache policy**: CachingOptimized
- **Origin request policy**: AllViewer  
- **Response headers policy**: None
- **Compress objects automatically**: Yes

Click **Create behavior**

### Step 5: Wait for Deployment
- CloudFront will show "Deploying" status
- Wait 5-10 minutes for changes to propagate globally

### Step 6: Test
After propagation:
```bash
# Test the app
https://investforge.io/app

# Test static asset directly
https://investforge.io/static/media/SourceSansVF-Upright.ttf.BsWL4Kly.woff2
```

## 🚀 **ALTERNATIVE: CLI Quick Fix**

If you prefer CLI, here's a one-liner to test the theory:

```bash
# Test if ALB serves the static asset correctly
curl -H "Host: investforge.io" "https://financial-analysis-alb-161240.us-east-1.elb.amazonaws.com/static/media/SourceSansVF-Upright.ttf.BsWL4Kly.woff2"
```

## 📋 **Expected Result**

After fixing:
- ✅ `https://investforge.io/app` loads without 403 errors
- ✅ Fonts and CSS load properly
- ✅ Streamlit interface displays correctly

## ⚡ **Quick Test Commands**

```bash
# Test app
curl -s https://investforge.io/app | grep -i error

# Test static asset
curl -s -w "HTTP %{http_code}\n" https://investforge.io/static/media/SourceSansVF-Upright.ttf.BsWL4Kly.woff2
```

## 🎯 **Why This Fixes It**

Currently:
```
https://investforge.io/static/* → S3 Origin (403 Forbidden)
```

After fix:
```  
https://investforge.io/static/* → ALB Origin → ECS → Streamlit (✅ Works)
```

This ensures all Streamlit assets are served through the correct origin!