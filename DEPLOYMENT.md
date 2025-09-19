# AWS App Runner Deployment Guide

This guide explains how to deploy the Financial Analysis Multi-Agent application to AWS App Runner.

## Prerequisites

1. AWS CLI installed and configured
2. AWS Account with appropriate permissions
3. Docker installed (for local testing)

## Required AWS Permissions

Your AWS user/role needs the following permissions:
- `apprunner:*`
- `iam:CreateRole`
- `iam:AttachRolePolicy` 
- `iam:PassRole`
- `ecr:*` (if using ECR for container registry)

## Deployment Steps

### 1. Set Up Environment Variables

AWS App Runner will need access to AWS Bedrock for the LLM functionality. You can configure this either through:

**Option A: IAM Roles (Recommended)**
- Create an IAM role with Bedrock access
- Attach the role to your App Runner service

**Option B: Environment Variables**
- Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in App Runner

### 2. Deploy via AWS Console

1. Go to AWS App Runner in the AWS Console
2. Click "Create service"
3. Choose "Source code repository" if using GitHub, or "Container registry" if using ECR
4. If using GitHub:
   - Connect your GitHub repository
   - Choose the branch (usually `main`)
   - App Runner will automatically detect the `apprunner.yaml` configuration
5. Configure service settings:
   - Service name: `financial-analysis-app`
   - CPU: 1 vCPU
   - Memory: 2 GB
6. Configure environment variables (if not using IAM roles):
   - `AWS_ACCESS_KEY_ID`: Your AWS access key
   - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
   - `AWS_DEFAULT_REGION`: us-east-1 (or your preferred region)
7. Click "Create & deploy"

### 3. Deploy via AWS CLI

```bash
# Create the App Runner service
aws apprunner create-service \\
  --service-name financial-analysis-app \\
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "public.ecr.aws/your-registry/financial-analysis-app:latest",
      "ImageConfiguration": {
        "Port": "8080"
      },
      "ImageRepositoryType": "ECR_PUBLIC"
    },
    "AutoDeploymentsEnabled": false
  }' \\
  --instance-configuration '{
    "Cpu": "1024",
    "Memory": "2048"
  }'
```

### 4. Monitor Deployment

- Check the App Runner console for deployment status
- Review CloudWatch logs for any issues
- Test the deployed application URL

## Local Testing

Before deploying, test the container locally:

```bash
# Build the Docker image
docker build -t financial-analysis-app .

# Run locally with environment variables
docker run -p 8080:8080 \\
  -e AWS_ACCESS_KEY_ID=your_key \\
  -e AWS_SECRET_ACCESS_KEY=your_secret \\
  -e AWS_DEFAULT_REGION=us-east-1 \\
  financial-analysis-app
```

Visit `http://localhost:8080` to test the application.

## Configuration Files

- `apprunner.yaml`: App Runner service configuration
- `Dockerfile`: Container configuration optimized for App Runner
- `.env.template`: Template for environment variables
- `.dockerignore`: Files to exclude from Docker build

## Troubleshooting

### Common Issues

1. **Port Binding Issues**
   - Ensure the application listens on port 8080
   - Check that Streamlit is configured with `--server.port=8080`

2. **AWS Credentials**
   - Verify AWS credentials have Bedrock access
   - Check CloudWatch logs for authentication errors

3. **Memory Issues**
   - Increase instance memory if the application runs out of memory
   - Consider optimizing the application for lower memory usage

4. **Build Failures**
   - Check that all dependencies in requirements.txt are available
   - Verify Docker build works locally

### Logs

View logs in CloudWatch:
```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/apprunner/financial-analysis-app"
```

## Security Considerations

1. Use IAM roles instead of hardcoded credentials when possible
2. Enable VPC configuration if accessing private resources
3. Configure proper security groups and network ACLs
4. Regularly rotate AWS credentials
5. Monitor CloudTrail for access patterns

## Cost Optimization

- Start with smaller instance sizes (0.25 vCPU, 0.5 GB memory) and scale up if needed
- Configure auto-scaling based on traffic patterns
- Monitor usage with AWS Cost Explorer

## Updates and Maintenance

To update the application:
1. Push changes to your repository
2. App Runner will automatically deploy if auto-deployment is enabled
3. Or manually trigger deployment in the console
4. Monitor the deployment in CloudWatch and App Runner console