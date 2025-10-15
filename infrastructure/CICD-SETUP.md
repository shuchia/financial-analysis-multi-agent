# InvestForge CI/CD Pipeline Setup

This guide explains how to set up the automated CI/CD pipeline for InvestForge using AWS CodePipeline.

## Overview

The CI/CD pipeline automates the entire deployment process:

```
GitHub Push → CodePipeline → CodeBuild → ECR → ECS Deployment
```

### Pipeline Stages:

1. **Source**: Detects changes in GitHub main branch
2. **Build**: Builds Docker image using CodeBuild
3. **Deploy**: Deploys new image to ECS Fargate

## Architecture

```
┌─────────────┐
│   GitHub    │
│  (main)     │
└──────┬──────┘
       │ Git Push
       ▼
┌─────────────────┐
│  CodePipeline   │
│                 │
│  ┌───────────┐  │
│  │  Source   │  │  Fetches code from GitHub
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │   Build   │  │  Builds Docker image
│  │ CodeBuild │  │  Pushes to ECR
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │  Deploy   │  │  Updates ECS service
│  │    ECS    │  │  with new image
│  └───────────┘  │
└─────────────────┘
       │
       ▼
┌─────────────┐
│ ECS Fargate │
│  Container  │
└─────────────┘
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **GitHub Repository** with code pushed
3. **Existing Infrastructure**:
   - ECR repository: `financial-analysis-app`
   - ECS cluster: `financial-analysis-cluster`
   - ECS service: `financial-analysis-service`
   - CodeBuild project: `financial-analysis-build`

## Quick Start

### Option 1: Using the Deployment Script (Recommended)

```bash
# Run the interactive deployment script
./infrastructure/deploy-pipeline.sh
```

The script will prompt you for:
- GitHub repository owner (default: shuchia)
- GitHub repository name (default: financial-analysis-multi-agent)
- GitHub branch (default: main)
- Notification email
- Environment (default: prod)

### Option 2: Manual Deployment

```bash
# Deploy the CloudFormation stack
aws cloudformation deploy \
    --template-file infrastructure/codepipeline.yml \
    --stack-name investforge-cicd \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Environment=prod \
        GitHubOwner=shuchia \
        GitHubRepo=financial-analysis-multi-agent \
        GitHubBranch=main \
        NotificationEmail=your-email@example.com \
    --region us-east-1
```

## Post-Deployment Setup

### 1. Activate GitHub Connection

**This is the most important step!** The pipeline won't work until you activate the GitHub connection.

1. Go to AWS Console → **Developer Tools** → **Connections**
   - Direct URL: https://console.aws.amazon.com/codesuite/settings/connections?region=us-east-1

2. Find the connection named: `investforge-cicd-github-connection`
   - Status will be "Pending"

3. Click **"Update pending connection"**

4. Complete the GitHub OAuth flow:
   - Click "Install a new app" (if first time)
   - Select your GitHub account/organization
   - Choose the repository: `financial-analysis-multi-agent`
   - Click "Connect"

5. Connection status will change to "Available"

### 2. Confirm Email Subscription

Check your email and confirm the SNS subscription to receive:
- Pipeline execution started
- Pipeline execution succeeded
- Pipeline execution failed

### 3. Test the Pipeline

Make a small change to your repository and push to main:

```bash
# Make a change
echo "# Testing pipeline" >> README.md

# Commit and push
git add README.md
git commit -m "Test CI/CD pipeline trigger"
git push origin main
```

The pipeline should automatically trigger within 1-2 minutes.

## Pipeline Components

### 1. Source Stage
- **Provider**: CodeStar Connections (GitHub)
- **Trigger**: Automatic on push to main branch
- **Output**: Source code zip artifact

### 2. Build Stage
- **Provider**: AWS CodeBuild
- **Build Spec**: Uses `buildspec.yml` in root
- **Docker Image**: Built using `app/Dockerfile.fast`
- **Output**:
  - Docker image pushed to ECR
  - `imagedefinitions.json` artifact

### 3. Deploy Stage
- **Provider**: Amazon ECS
- **Deployment Type**: Blue/Green with circuit breaker
- **Target**: ECS service `financial-analysis-service`
- **Timeout**: 15 minutes

## Monitoring

### View Pipeline Status

**AWS Console:**
```
AWS Console → CodePipeline → Pipelines → investforge-cicd-pipeline-prod
```

**AWS CLI:**
```bash
# Get pipeline execution status
aws codepipeline get-pipeline-state \
    --name investforge-cicd-pipeline-prod \
    --region us-east-1
```

### View Build Logs

**AWS Console:**
```
AWS Console → CodeBuild → Build Projects → financial-analysis-build → Build History
```

**AWS CLI:**
```bash
# List recent builds
aws codebuild list-builds-for-project \
    --project-name financial-analysis-build \
    --region us-east-1
```

### View Deployment Status

**AWS Console:**
```
AWS Console → ECS → Clusters → financial-analysis-cluster → Services → financial-analysis-service
```

**AWS CLI:**
```bash
# Check ECS service status
aws ecs describe-services \
    --cluster financial-analysis-cluster \
    --services financial-analysis-service \
    --region us-east-1
```

## Troubleshooting

### Issue: Pipeline doesn't trigger on push

**Solution:**
1. Verify GitHub connection is "Available" (not "Pending")
2. Check CloudWatch Events rule is enabled
3. Verify you're pushing to the correct branch (main)

**Check connection status:**
```bash
aws codestar-connections list-connections --region us-east-1
```

### Issue: Build fails

**Solution:**
1. Check CodeBuild logs in CloudWatch
2. Verify ECR repository exists
3. Check IAM permissions for CodeBuild role

**View build logs:**
```bash
# Get latest build ID
BUILD_ID=$(aws codebuild list-builds-for-project \
    --project-name financial-analysis-build \
    --max-items 1 \
    --query 'ids[0]' \
    --output text \
    --region us-east-1)

# View build details
aws codebuild batch-get-builds \
    --ids $BUILD_ID \
    --region us-east-1
```

### Issue: Deploy fails

**Solution:**
1. Check ECS service events
2. Verify task definition is valid
3. Check ECS task role permissions

**View service events:**
```bash
aws ecs describe-services \
    --cluster financial-analysis-cluster \
    --services financial-analysis-service \
    --region us-east-1 \
    --query 'services[0].events[:5]'
```

### Issue: imagedefinitions.json not found

**Solution:**
1. Verify buildspec.yml creates the file correctly
2. Check CodeBuild artifacts configuration
3. Review build logs for errors

**Verify artifact:**
```bash
# Check S3 artifact bucket
aws s3 ls s3://investforge-cicd-pipeline-artifacts-$(aws sts get-caller-identity --query Account --output text)/ --recursive | grep imagedefinitions.json
```

## Pipeline Configuration

### Environment Variables (CodeBuild)

The following environment variables are automatically set:

| Variable | Description | Source |
|----------|-------------|--------|
| `IMAGE_REPO_NAME` | ECR repository name | Pipeline parameter |
| `AWS_DEFAULT_REGION` | AWS region | Stack region |
| `AWS_ACCOUNT_ID` | AWS account ID | Caller identity |
| `CODEBUILD_RESOLVED_SOURCE_VERSION` | Git commit SHA | CodeBuild |

### Buildspec.yml

The build process uses Docker layer caching for faster builds:

```yaml
phases:
  pre_build:
    - Login to ECR
    - Pull previous image for cache
  build:
    - Build Docker image with cache
    - Tag with commit SHA and latest
  post_build:
    - Push images to ECR
    - Create imagedefinitions.json
```

## Cost Optimization

### Pipeline Costs

- **CodePipeline**: $1/month per active pipeline
- **CodeBuild**: $0.005/minute (build time ~5-10 minutes)
- **S3 Artifacts**: ~$0.023/GB (with 30-day lifecycle)
- **Data Transfer**: Included (same region)

**Estimated monthly cost**: ~$5-10 for typical usage (10-20 builds/day)

### Optimization Tips

1. **Use Docker Layer Caching**: Already enabled in buildspec
2. **Limit Artifact Retention**: 30-day lifecycle configured
3. **Use Fargate Spot**: Already configured (80% cost savings)
4. **Monitor Build Time**: Optimize Dockerfile if builds are slow

## Manual Deployment (Fallback)

If you need to deploy manually without the pipeline:

```bash
# 1. Build and push Docker image
cd app
docker build -f Dockerfile.fast -t financial-analysis-app:latest .

# 2. Tag and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag financial-analysis-app:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/financial-analysis-app:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/financial-analysis-app:latest

# 3. Update ECS service
aws ecs update-service \
    --cluster financial-analysis-cluster \
    --service financial-analysis-service \
    --force-new-deployment \
    --region us-east-1
```

## Security Best Practices

1. **IAM Roles**: Least privilege access configured
2. **Encryption**: S3 artifacts encrypted at rest (AES256)
3. **Secrets**: Use AWS Secrets Manager for sensitive data
4. **GitHub Token**: Not stored in template (use Secrets Manager)
5. **VPC**: ECS tasks run in private subnets

## Cleanup

To delete the CI/CD pipeline:

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack \
    --stack-name investforge-cicd \
    --region us-east-1

# Verify deletion
aws cloudformation wait stack-delete-complete \
    --stack-name investforge-cicd \
    --region us-east-1

# Clean up S3 artifacts (optional)
aws s3 rb s3://investforge-cicd-pipeline-artifacts-<account-id> --force
```

## References

- [AWS CodePipeline Documentation](https://docs.aws.amazon.com/codepipeline/)
- [CodeStar Connections](https://docs.aws.amazon.com/dtconsole/latest/userguide/connections.html)
- [ECS Blue/Green Deployment](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-type-bluegreen.html)
- [BuildSpec Reference](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html)

## Support

For issues or questions:
1. Check CloudWatch Logs
2. Review AWS service events
3. Verify IAM permissions
4. Contact AWS Support if needed
