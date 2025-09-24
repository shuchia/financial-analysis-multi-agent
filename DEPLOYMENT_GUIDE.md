# InvestForge AWS Deployment Guide

This guide will walk you through deploying InvestForge to AWS using the unified architecture.

## Prerequisites

### 1. AWS CLI Setup
```bash
# Install AWS CLI if not already installed
brew install awscli  # macOS
# or
pip install awscli

# Configure AWS credentials
aws configure
# Enter your AWS Access Key ID, Secret Access Key, Region (us-east-1), and output format (json)
```

### 2. Docker Setup
```bash
# Ensure Docker is installed and running
docker --version
```

### 3. Node.js and npm
```bash
# Required for Serverless Framework
node --version
npm --version
```

## Step-by-Step Deployment

### Step 1: Verify AWS Prerequisites

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check if you have a domain in Route 53 (optional for testing)
aws route53 list-hosted-zones

# Check available VPCs
aws ec2 describe-vpcs --filters "Name=is-default,Values=true"
```

### Step 2: Create SSL Certificate (Required)

```bash
# Create ACM certificate for your domain
aws acm request-certificate \
    --domain-name investforge.io \
    --subject-alternative-names "*.investforge.io" \
    --validation-method DNS \
    --region us-east-1

# Note: You'll need to validate the certificate via DNS records
# Check certificate status
aws acm list-certificates --region us-east-1
```

**Alternative for testing**: You can skip SSL and use HTTP-only ALB for initial testing.

### Step 3: Set Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp api/.env.example .env

# Edit the file with your values
cat > .env << 'EOF'
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-at-least-32-chars-long

# Stripe Configuration (get from https://dashboard.stripe.com/apikeys)
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# AWS Configuration
AWS_DEFAULT_REGION=us-east-1

# Domain (change this to your domain)
DOMAIN_NAME=investforge.io
EOF

# Load environment variables
source .env
export $(cat .env | xargs)
```

### Step 4: Deploy Infrastructure

```bash
# Option 1: Full automated deployment
./deploy-unified.sh --env dev --domain investforge.io

# Option 2: Step-by-step deployment (recommended for first time)
# Deploy just the infrastructure first
aws cloudformation create-stack \
    --stack-name investforge-unified-dev \
    --template-body file://infrastructure/cloudformation/unified-architecture.yml \
    --parameters ParameterKey=Environment,ParameterValue=dev \
                ParameterKey=DomainName,ParameterValue=investforge.io \
    --capabilities CAPABILITY_IAM \
    --region us-east-1

# Wait for completion
aws cloudformation wait stack-create-complete \
    --stack-name investforge-unified-dev \
    --region us-east-1
```

### Step 5: Build and Push Docker Image

```bash
# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1

# Create ECR repository
aws ecr create-repository --repository-name investforge/streamlit --region $REGION

# Get ECR login
aws ecr get-login-password --region $REGION | \
    docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build and push image
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/investforge/streamlit:dev"
docker build -t $IMAGE_URI app/
docker push $IMAGE_URI

echo "Image pushed: $IMAGE_URI"
```

### Step 6: Deploy Serverless API

```bash
cd api

# Install dependencies
npm install

# Deploy API functions
npx serverless deploy --config serverless-alb.yml --stage dev

cd ..
```

### Step 7: Upload Landing Page

```bash
# Get S3 bucket name from CloudFormation output
BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name investforge-unified-dev \
    --query "Stacks[0].Outputs[?OutputKey=='LandingPageBucket'].OutputValue" \
    --output text)

# Upload landing page
aws s3 sync landing/ s3://$BUCKET_NAME/ --delete

echo "Landing page uploaded to: $BUCKET_NAME"
```

### Step 8: Update ECS Service with New Image

```bash
# Update ECS service to use the new image
SERVICE_NAME="investforge-unified-dev-streamlit-dev"
CLUSTER_NAME="investforge-unified-dev-cluster-dev"

# Get current task definition
TASK_DEF_ARN=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --query "services[0].taskDefinition" \
    --output text)

# Update task definition with new image
# (This would typically be done through CloudFormation update)

# Force new deployment
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --force-new-deployment

# Wait for deployment to complete
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME
```

## Testing the Deployment

### 1. Get URLs

```bash
# Get ALB URL
ALB_URL=$(aws cloudformation describe-stacks \
    --stack-name investforge-unified-dev \
    --query "Stacks[0].Outputs[?OutputKey=='ALBEndpoint'].OutputValue" \
    --output text)

# Get CloudFront URL
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
    --stack-name investforge-unified-dev \
    --query "Stacks[0].Outputs[?OutputKey=='CloudFrontURL'].OutputValue" \
    --output text)

echo "ALB URL: http://$ALB_URL"
echo "CloudFront URL: https://$CLOUDFRONT_URL"
```

### 2. Test Endpoints

```bash
# Test landing page
curl -I http://$ALB_URL/

# Test health endpoints
curl http://$ALB_URL/app/health
curl http://$ALB_URL/api/health

# Test API endpoint
curl -X POST http://$ALB_URL/api/waitlist/join \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","source":"test"}'
```

### 3. Access in Browser

- **Landing Page**: `http://{ALB_URL}/`
- **Streamlit App**: `http://{ALB_URL}/app/`
- **API Docs**: Test API endpoints with curl or Postman

## Troubleshooting

### Common Issues

1. **Certificate Validation**: 
   - Make sure to validate ACM certificate via DNS
   - For testing, you can modify CloudFormation to skip HTTPS

2. **ECS Service Won't Start**:
   ```bash
   # Check ECS service events
   aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME
   
   # Check task logs
   aws logs get-log-events --log-group-name /ecs/investforge-unified-dev --log-stream-name [stream-name]
   ```

3. **API Functions Not Working**:
   ```bash
   # Check Lambda function logs
   aws logs get-log-events --log-group-name /aws/lambda/investforge-api-alb-dev-signup
   ```

4. **Docker Build Issues**:
   ```bash
   # Test Docker build locally
   docker build -t test-image app/
   docker run -p 8080:8080 test-image
   ```

### Cleanup

To remove all resources:
```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name investforge-unified-dev

# Delete ECR repository
aws ecr delete-repository --repository-name investforge/streamlit --force

# Delete S3 bucket contents
aws s3 rm s3://$BUCKET_NAME --recursive
```

## Next Steps After Successful Deployment

1. **Configure Domain**: Point your domain to CloudFront distribution
2. **Setup Stripe**: Update webhook URL in Stripe dashboard
3. **Configure SES**: Verify sending domain in AWS SES
4. **Monitor**: Set up CloudWatch alarms and dashboards
5. **Scale**: Adjust ECS service desired count based on traffic

## Quick Test Commands

```bash
# Quick deployment test (without domain/SSL)
./deploy-unified.sh --env dev --domain localhost --dry-run

# Local development test
docker-compose -f docker-compose.unified.yml up
# Then visit: http://localhost:8080
```