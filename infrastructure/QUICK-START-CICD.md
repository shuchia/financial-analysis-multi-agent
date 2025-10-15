# Quick Start: CI/CD Pipeline Setup

## 🚀 Deploy in 5 Minutes

### Step 1: Deploy the Pipeline

```bash
./infrastructure/deploy-pipeline.sh
```

Enter when prompted:
- GitHub Owner: `shuchia`
- Repo: `financial-analysis-multi-agent`
- Branch: `main`
- Email: `your-email@example.com`
- Environment: `prod`

### Step 2: Activate GitHub Connection

⚠️ **CRITICAL STEP** - Pipeline won't work without this!

1. Go to: https://console.aws.amazon.com/codesuite/settings/connections?region=us-east-1
2. Find: `investforge-cicd-github-connection` (Status: Pending)
3. Click: **"Update pending connection"**
4. Complete GitHub OAuth flow
5. Status changes to: **"Available"** ✅

### Step 3: Test the Pipeline

```bash
# Make a test commit
git commit --allow-empty -m "Test CI/CD pipeline"
git push origin main
```

Watch the pipeline: https://console.aws.amazon.com/codesuite/codepipeline/pipelines

### Step 4: Confirm Email

Check your email and confirm SNS subscription for notifications.

## ✅ Success Criteria

- Pipeline triggers automatically on push to main
- Build completes in ~5-10 minutes
- ECS service updates with new container
- You receive email notifications

## 🔍 Quick Status Check

```bash
# Check pipeline status
aws codepipeline get-pipeline-state \
    --name investforge-cicd-pipeline-prod \
    --region us-east-1 \
    --query 'stageStates[*].[stageName,latestExecution.status]' \
    --output table

# Check ECS service
aws ecs describe-services \
    --cluster financial-analysis-cluster \
    --services financial-analysis-service \
    --region us-east-1 \
    --query 'services[0].[serviceName,status,runningCount,desiredCount]' \
    --output table
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Pipeline doesn't trigger | Activate GitHub connection (Step 2) |
| Build fails | Check CodeBuild logs in CloudWatch |
| Deploy fails | Check ECS service events |
| No email | Confirm SNS subscription |

For detailed troubleshooting, see: [CICD-SETUP.md](CICD-SETUP.md)

## 📊 What Happens Now?

Every time you push to main:

1. ✅ Pipeline automatically triggers
2. 🏗️ Docker image built and pushed to ECR
3. 🚀 ECS service updates with zero downtime
4. 📧 Email notification sent

**No manual CodeBuild or ECS updates needed!**

## 🔄 Current vs New Workflow

### Before (Manual):
```
Push code → Manual CodeBuild trigger → Manual ECS update
```

### After (Automated):
```
Push code → ✨ Everything happens automatically! ✨
```

## 💰 Cost

~$5-10/month for typical usage (10-20 deployments/day)

- CodePipeline: $1/month
- CodeBuild: $0.005/minute
- S3 Artifacts: $0.023/GB
- **No charges** when idle

## 🆘 Need Help?

See full documentation: [CICD-SETUP.md](CICD-SETUP.md)
