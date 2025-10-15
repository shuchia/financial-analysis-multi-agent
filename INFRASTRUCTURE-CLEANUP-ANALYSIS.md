# Infrastructure Files Cleanup Analysis

## Current Infrastructure (IN USE - DO NOT DELETE)

### ✅ Active Deployment Files

1. **buildspec.yml** (root) - **IN USE**
   - Used by CodeBuild project: `financial-analysis-build`
   - Builds Docker image with layer caching
   - Creates `imagedefinitions.json` for ECS deployment
   - **Status**: Active, required for CI/CD pipeline

2. **app/Dockerfile.fast** - **IN USE**
   - Referenced in buildspec.yml (line 27)
   - Optimized Dockerfile with layer caching
   - Used for production builds
   - **Status**: Active, required

3. **app/Dockerfile** - **KEEP FOR LOCAL DEV**
   - Used by docker-compose for local development
   - Not used in production but useful for dev/testing
   - **Status**: Keep for development

### ✅ New CI/CD Pipeline Files (JUST CREATED)

4. **infrastructure/codepipeline.yml** - **NEW**
   - CodePipeline CloudFormation template
   - Automates: GitHub → CodeBuild → ECS
   - **Status**: Ready to deploy

5. **infrastructure/deploy-pipeline.sh** - **NEW**
   - Deployment script for CodePipeline
   - **Status**: Ready to use

6. **infrastructure/CICD-SETUP.md** - **NEW**
   - Comprehensive CI/CD documentation
   - **Status**: Documentation

7. **infrastructure/QUICK-START-CICD.md** - **NEW**
   - Quick start guide
   - **Status**: Documentation

## Files to REMOVE (Unused/Obsolete)

### 🗑️ Obsolete CloudFormation Templates

1. **infrastructure/cloudformation/unified-architecture.yml** - **REMOVE**
   - **Reason**: Overly complex architecture (ALB + Lambda + ECS + CloudFront + Redis)
   - Current setup is simpler: CodeBuild → ECR → ECS
   - Not deployed (no stack found)
   - **References**: Route 53, Redis cluster (not in use)

2. **infrastructure/enhanced-deployment.yml** - **REMOVE**
   - **Reason**: Duplicates functionality, references non-existent resources
   - Assumes Lambda functions that don't exist
   - References ALB listener rules not configured
   - Not deployed (no stack found)

3. **infrastructure/cloudfront-deployment.yml** - **REMOVE**
   - **Reason**: CloudFront not currently in use
   - References ALB domain that would need to be provided
   - Can be recreated if needed later
   - Not deployed (no stack found)

### 🗑️ Obsolete Deployment Scripts

4. **deploy.sh** - **REMOVE**
   - **Reason**: AWS App Runner script (not using App Runner)
   - References non-existent App Runner service
   - Replaced by CodePipeline

5. **deploy-unified.sh** - **REMOVE**
   - **Reason**: References unified-architecture.yml (being removed)
   - Manual deployment script no longer needed

6. **deploy-api.sh** - **REMOVE**
   - **Reason**: Serverless API deployment (API not currently used)
   - References `api/serverless.yml`

7. **quick-deploy.sh** - **REMOVE**
   - **Reason**: Manual quick deploy script
   - Replaced by automated CodePipeline

8. **deploy-existing-infra.sh** - **REMOVE**
   - **Reason**: Manual deployment to existing infrastructure
   - Replaced by CodePipeline automation

### 🗑️ Python Deployment Scripts (Obsolete)

9. **deploy-simple.py** - **REMOVE**
   - **Reason**: Manual Python deployment script
   - Functionality replaced by CodePipeline

10. **deploy-new-image.py** - **REMOVE**
    - **Reason**: Manual image deployment
    - Replaced by automated ECS deployment stage

11. **deploy-latest-code.py** - **REMOVE**
    - **Reason**: Manual code deployment
    - Replaced by CodePipeline

12. **deploy-streamlit-cmdline.py** - **REMOVE**
    - **Reason**: Command-line Streamlit deployment
    - Replaced by CodePipeline

13. **test-deployment.py** - **REMOVE**
    - **Reason**: Tests for manual deployment (no longer relevant)
    - Old deployment method deprecated

14. **test-enhanced-deployment.py** - **REMOVE**
    - **Reason**: Tests for enhanced-deployment.yml (being removed)

### 🗑️ Obsolete Buildspec Files

15. **app/buildspec.yml** - **REMOVE**
   - **Reason**: Older, simpler buildspec without caching
   - Root buildspec.yml is the active one
   - No references in CodeBuild project

16. **extract-versions-buildspec.yml** - **REMOVE**
   - **Reason**: Appears to be experimental/testing
   - Not referenced in any CodeBuild project

### 🗑️ Obsolete Docker Compose Files

17. **docker-compose.yml** - **KEEP (for local dev)**
   - **Reason**: Used for local development and testing
   - Not used in production but useful for developers
   - **Status**: Keep

18. **docker-compose.unified.yml** - **REMOVE**
   - **Reason**: Unified architecture simulation (not needed)
   - References landing page and API (not in use)
   - More complex than needed for local dev

### 🗑️ Obsolete Documentation

19. **DEPLOYMENT.md** - **UPDATE/MERGE**
   - **Reason**: Outdated deployment instructions
   - References App Runner (not in use)
   - Should be updated or merged with CICD-SETUP.md

20. **DEPLOYMENT_GUIDE.md** - **UPDATE/MERGE**
   - **Reason**: Likely outdated
   - Should be consolidated with new CI/CD docs

21. **DEPLOYMENT_STATUS.md** - **REMOVE**
   - **Reason**: Status file (likely outdated)
   - Current status tracked in AWS console

22. **AUTH_DEPLOYMENT.md** - **KEEP (if auth is planned)**
   - **Reason**: Authentication documentation
   - May be needed for future auth implementation
   - Review if auth features are planned

### 🗑️ API-Related Files (if API not in use)

23. **api/Dockerfile.dev** - **CONDITIONAL**
   - **Check**: Is the Lambda API actually deployed?
   - If no Lambda functions exist, remove entire `api/` directory
   - Current analysis: No Lambda functions in use

24. **api/serverless*.yml** - **CONDITIONAL**
   - Multiple serverless config files
   - Not deployed (no Lambda functions found)
   - **Recommendation**: Remove if API not planned

25. **api/deploy.sh** - **REMOVE** (already listed above)

## Summary

### Current Active Infrastructure

**InvestForge Architecture (Path-Based Routing):**
```
                        investforge.io
                             |
                    ┌────────┴────────┐
                    │   CloudFront    │
                    └────────┬────────┘
                             |
              ┌──────────────┼──────────────┐
              |              |              |
         / (root)       /app/*         /api/*
              |              |              |
         ┌────▼────┐    ┌───▼────┐    ┌───▼─────┐
         │   S3    │    │  ALB   │    │   ALB   │
         │ Landing │    └───┬────┘    └───┬─────┘
         └─────────┘        |              |
                       ┌────▼─────┐   ┌────▼──────┐
                       │   ECS    │   │  Lambda   │
                       │ Fargate  │   │ Functions │
                       │Streamlit │   │  (API)    │
                       │port 8080 │   └───────────┘
                       └──────────┘
```

**Active Resources:**
- **ECS Cluster**: financial-analysis-cluster
- **ECS Service**: financial-analysis-service (Streamlit app)
- **ECR Repository**: financial-analysis-app
- **CodeBuild Project**: financial-analysis-build
- **Lambda Functions** (9 active):
  - investforge-health
  - investforge-signup
  - investforge-login
  - investforge-get-user
  - investforge-waitlist
  - investforge-analytics
  - investforge-analytics-new
  - investforge-preferences
  - investforge-api-test

**CI/CD Pipeline (Streamlit App):**
```
GitHub → CodePipeline (to deploy) → CodeBuild → ECR → ECS
            (automated)           financial-    financial-  financial-
                                 analysis-build analysis-app analysis-service
```

**Note**: Lambda functions deployed separately via Serverless Framework (`api/` directory)

### Files to KEEP
- ✅ buildspec.yml (root) - CodeBuild for Streamlit app
- ✅ app/Dockerfile.fast - Production builds
- ✅ app/Dockerfile - Local development
- ✅ docker-compose.yml - Local development
- ✅ **api/ directory** - Lambda functions (REQUIRED for production)
- ✅ infrastructure/codepipeline.yml - NEW CI/CD pipeline
- ✅ infrastructure/deploy-pipeline.sh - NEW deployment script
- ✅ infrastructure/CICD-SETUP.md - NEW documentation
- ✅ infrastructure/QUICK-START-CICD.md - NEW quick start

### Files to REMOVE (23 files)

**CloudFormation Templates (3):**
- infrastructure/cloudformation/unified-architecture.yml
- infrastructure/enhanced-deployment.yml
- infrastructure/cloudfront-deployment.yml

**Shell Scripts (5):**
- deploy.sh
- deploy-unified.sh
- deploy-api.sh
- quick-deploy.sh
- deploy-existing-infra.sh

**Python Scripts (7):**
- deploy-simple.py
- deploy-new-image.py
- deploy-latest-code.py
- deploy-streamlit-cmdline.py
- test-deployment.py
- test-enhanced-deployment.py
- create-simple-test.py

**Buildspec Files (2):**
- app/buildspec.yml
- extract-versions-buildspec.yml

**Docker Compose (1):**
- docker-compose.unified.yml

**Documentation (3):**
- DEPLOYMENT_STATUS.md
- (DEPLOYMENT.md - to be updated)
- (DEPLOYMENT_GUIDE.md - to be updated)

**API Directory:**
- ✅ **KEEP** - API directory is IN USE with 9 active Lambda functions
- Functions handle authentication, user management, analytics, and health checks
- Deployed via Serverless Framework

### Recommended Actions

1. **Immediate Removal** (safe, no dependencies):
   - All Python deployment scripts
   - Obsolete shell scripts
   - Unused CloudFormation templates
   - app/buildspec.yml
   - extract-versions-buildspec.yml
   - docker-compose.unified.yml

2. **Documentation Consolidation**:
   - Merge DEPLOYMENT*.md into CICD-SETUP.md
   - Create single source of truth for deployment
   - Remove redundant docs

3. **API Directory**:
   - ✅ Confirmed IN USE - 9 Lambda functions active
   - Keep all API files (required for production)
   - Lambda functions handle /api/* routes via ALB

4. **Create Archive** (optional):
   - Move removed files to `archive/` directory
   - Keeps history but cleans up active codebase

## Risk Assessment

**Low Risk Removals** (no active dependencies):
- All deployment scripts (replaced by CodePipeline)
- Unused CloudFormation templates (not deployed)
- Test scripts for old deployment methods
- Duplicate buildspec files

**Medium Risk** (verify first):
- Documentation files (may have useful info)
- docker-compose.unified.yml (check if anyone uses it)

**No Risk** (keep):
- buildspec.yml (active in CodeBuild)
- app/Dockerfile.fast (referenced in buildspec)
- docker-compose.yml (useful for development)

## Next Steps

1. Create `archive/deprecated-deploy-scripts/` directory
2. Move all obsolete files to archive
3. Update/consolidate documentation
4. Commit cleanup with clear message
5. Update README to reference new CI/CD setup
