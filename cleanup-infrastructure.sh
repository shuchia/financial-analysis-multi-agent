#!/bin/bash

# =====================================
# Infrastructure Cleanup Script
# Safely archives obsolete deployment files
# =====================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Infrastructure Cleanup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Create archive directory
ARCHIVE_DIR="archive/deprecated-deployment-$(date +%Y%m%d)"
echo -e "${BLUE}Creating archive directory: $ARCHIVE_DIR${NC}"
mkdir -p "$ARCHIVE_DIR"

# Function to move file with logging
move_file() {
    local file=$1
    if [ -f "$file" ]; then
        echo -e "${YELLOW}  Moving: $file${NC}"
        mv "$file" "$ARCHIVE_DIR/"
    else
        echo -e "${RED}  Not found: $file${NC}"
    fi
}

# Function to move directory with logging
move_dir() {
    local dir=$1
    if [ -d "$dir" ]; then
        echo -e "${YELLOW}  Moving directory: $dir${NC}"
        mv "$dir" "$ARCHIVE_DIR/"
    else
        echo -e "${RED}  Not found: $dir${NC}"
    fi
}

echo ""
echo -e "${GREEN}Step 1: Archiving obsolete CloudFormation templates${NC}"
move_file "infrastructure/enhanced-deployment.yml"
move_file "infrastructure/cloudfront-deployment.yml"
mkdir -p "$ARCHIVE_DIR/cloudformation"
if [ -f "infrastructure/cloudformation/unified-architecture.yml" ]; then
    echo -e "${YELLOW}  Moving: infrastructure/cloudformation/unified-architecture.yml${NC}"
    mv "infrastructure/cloudformation/unified-architecture.yml" "$ARCHIVE_DIR/cloudformation/"
fi

echo ""
echo -e "${GREEN}Step 2: Archiving obsolete shell scripts${NC}"
move_file "deploy.sh"
move_file "deploy-unified.sh"
move_file "deploy-api.sh"
move_file "quick-deploy.sh"
move_file "deploy-existing-infra.sh"

echo ""
echo -e "${GREEN}Step 3: Archiving obsolete Python deployment scripts${NC}"
move_file "deploy-simple.py"
move_file "deploy-new-image.py"
move_file "deploy-latest-code.py"
move_file "deploy-streamlit-cmdline.py"
move_file "test-deployment.py"
move_file "test-enhanced-deployment.py"
move_file "create-simple-test.py"

echo ""
echo -e "${GREEN}Step 4: Archiving duplicate buildspec files${NC}"
move_file "app/buildspec.yml"
move_file "extract-versions-buildspec.yml"

echo ""
echo -e "${GREEN}Step 5: Archiving unused docker-compose files${NC}"
move_file "docker-compose.unified.yml"

echo ""
echo -e "${GREEN}Step 6: Archiving obsolete documentation${NC}"
move_file "DEPLOYMENT_STATUS.md"
# Note: Keeping DEPLOYMENT.md and DEPLOYMENT_GUIDE.md for manual review/merge
echo -e "${YELLOW}  NOTE: DEPLOYMENT.md and DEPLOYMENT_GUIDE.md kept for manual review${NC}"
echo -e "${YELLOW}        Review these files and merge useful content into CICD-SETUP.md${NC}"

echo ""
echo -e "${BLUE}Step 7: Checking API directory...${NC}"
if [ -d "api" ]; then
    echo -e "${GREEN}  ✓ API directory found and IN USE${NC}"
    echo -e "${BLUE}    Lambda functions deployed for /api/* routes${NC}"
    echo -e "${BLUE}    Keeping api/ directory (required for production)${NC}"
else
    echo -e "${YELLOW}  ⚠️  No api/ directory found${NC}"
fi

echo ""
echo -e "${GREEN}Step 8: Creating cleanup summary${NC}"
cat > "$ARCHIVE_DIR/README.md" << EOF
# Archived Deployment Files

**Archive Date**: $(date +"%Y-%m-%d %H:%M:%S")
**Reason**: Migration to CodePipeline-based CI/CD

## What Was Archived

This directory contains deployment files that were used before implementing
the automated CodePipeline CI/CD process.

### CloudFormation Templates
- enhanced-deployment.yml - Complex unified architecture (not deployed)
- cloudfront-deployment.yml - CloudFront distribution (not in use)
- unified-architecture.yml - Full stack template (not deployed)

### Shell Scripts
- deploy.sh - App Runner deployment (not using App Runner)
- deploy-unified.sh - Manual unified deployment
- deploy-api.sh - Serverless API deployment
- quick-deploy.sh - Quick manual deployment
- deploy-existing-infra.sh - Existing infra deployment

### Python Scripts
- deploy-simple.py - Simple deployment script
- deploy-new-image.py - Manual image deployment
- deploy-latest-code.py - Code deployment script
- deploy-streamlit-cmdline.py - Streamlit CLI deployment
- test-deployment.py - Deployment tests
- test-enhanced-deployment.py - Enhanced deployment tests
- create-simple-test.py - Test creation script

### Build Specs
- app/buildspec.yml - Older buildspec (replaced by root buildspec.yml)
- extract-versions-buildspec.yml - Version extraction buildspec

### Docker Compose
- docker-compose.unified.yml - Unified architecture simulation

### Documentation
- DEPLOYMENT_STATUS.md - Outdated deployment status

## Current Architecture (InvestForge)

\`\`\`
investforge.io/        → CloudFront → S3 (landing page)
investforge.io/app/*   → ALB → ECS Fargate (Streamlit on port 8080)
investforge.io/api/*   → ALB → Lambda functions (API endpoints)
\`\`\`

### Active Lambda Functions:
- investforge-health
- investforge-signup
- investforge-login
- investforge-get-user
- investforge-waitlist
- investforge-analytics
- investforge-analytics-new
- investforge-preferences
- investforge-api-test

## Current CI/CD Process (Streamlit App Only)

The new automated CI/CD process for the Streamlit app uses:

1. **CodePipeline** (infrastructure/codepipeline.yml)
   - Automatically triggers on GitHub push to main
   - Orchestrates build and deployment

2. **CodeBuild** (buildspec.yml)
   - Builds Docker image for Streamlit app
   - Pushes to ECR: financial-analysis-app
   - Creates imagedefinitions.json

3. **ECS Deployment** (automated)
   - Cluster: financial-analysis-cluster
   - Service: financial-analysis-service
   - Zero-downtime rolling update

**Note**: Lambda API functions are deployed separately via Serverless Framework
See: infrastructure/CICD-SETUP.md for complete documentation

## Restoration

If you need to restore any of these files:

\`\`\`bash
# Copy specific file back
cp archive/deprecated-deployment-YYYYMMDD/<filename> .

# Or restore entire archive
cp -r archive/deprecated-deployment-YYYYMMDD/* .
\`\`\`

## Safe to Delete?

Yes, these files can be safely deleted after confirming:
1. CodePipeline is working correctly
2. ECS deployments are successful
3. No one is using manual deployment scripts

**Recommended**: Keep archive for 30-60 days, then delete if no issues.
EOF

echo -e "${GREEN}  ✓ Created archive README${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Cleanup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Count archived files
ARCHIVED_COUNT=$(find "$ARCHIVE_DIR" -type f | wc -l | tr -d ' ')
echo -e "${BLUE}Archived Files:${NC} $ARCHIVED_COUNT"
echo -e "${BLUE}Archive Location:${NC} $ARCHIVE_DIR"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review archived files in: $ARCHIVE_DIR"
echo "2. Review DEPLOYMENT.md and DEPLOYMENT_GUIDE.md"
echo "3. Merge useful content into infrastructure/CICD-SETUP.md"
echo "4. Commit the cleanup:"
echo "   git add ."
echo "   git commit -m \"Clean up obsolete deployment files, migrate to CodePipeline\""
echo "5. Test the new CI/CD pipeline"
echo ""

echo -e "${GREEN}Files kept for production:${NC}"
echo "  ✅ buildspec.yml (CodeBuild for Streamlit app)"
echo "  ✅ app/Dockerfile.fast (production builds)"
echo "  ✅ app/Dockerfile (local dev)"
echo "  ✅ docker-compose.yml (local dev)"
echo "  ✅ api/ directory (Lambda functions for /api/* routes)"
echo "  ✅ infrastructure/codepipeline.yml (CI/CD for Streamlit)"
echo "  ✅ infrastructure/deploy-pipeline.sh (CI/CD deployment)"
echo "  ✅ infrastructure/CICD-SETUP.md (documentation)"
echo ""

echo -e "${BLUE}Review the archive, then deploy the CI/CD pipeline:${NC}"
echo "  ./infrastructure/deploy-pipeline.sh"
echo ""
