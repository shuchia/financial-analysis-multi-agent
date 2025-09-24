#!/bin/bash

# InvestForge Unified Architecture Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="prod"
DOMAIN="investforge.io"
PROFILE=""
DRY_RUN=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -e, --env       Environment (dev, staging, prod) [default: prod]"
            echo "  -d, --domain    Domain name [default: investforge.io]"
            echo "  -p, --profile   AWS profile to use"
            echo "  --dry-run       Show what would be deployed without executing"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🚀 InvestForge Unified Architecture Deployment${NC}"
echo -e "${BLUE}=============================================${NC}"
echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "Domain: ${YELLOW}$DOMAIN${NC}"
if [ ! -z "$PROFILE" ]; then
    echo -e "AWS Profile: ${YELLOW}$PROFILE${NC}"
fi
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}⚠️  DRY RUN MODE - No changes will be made${NC}"
fi
echo ""

# Set AWS command
AWS_CMD="aws"
if [ ! -z "$PROFILE" ]; then
    AWS_CMD="aws --profile $PROFILE"
fi

# Validate AWS credentials
echo -e "${BLUE}🔑 Validating AWS credentials...${NC}"
if ! $AWS_CMD sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    exit 1
fi

ACCOUNT_ID=$($AWS_CMD sts get-caller-identity --query Account --output text)
REGION=$($AWS_CMD configure get region || echo "us-east-1")
echo -e "${GREEN}✅ AWS credentials validated (Account: $ACCOUNT_ID, Region: $REGION)${NC}"
echo ""

# Check for required environment variables
echo -e "${BLUE}🔐 Checking environment variables...${NC}"
MISSING_VARS=()

if [ -z "$JWT_SECRET_KEY" ]; then
    MISSING_VARS+=("JWT_SECRET_KEY")
fi

if [ -z "$STRIPE_SECRET_KEY" ]; then
    MISSING_VARS+=("STRIPE_SECRET_KEY")
fi

if [ -z "$STRIPE_WEBHOOK_SECRET" ]; then
    MISSING_VARS+=("STRIPE_WEBHOOK_SECRET")
fi

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Missing environment variables: ${MISSING_VARS[*]}${NC}"
    echo "Please set these variables before deploying to production"
    if [ "$ENVIRONMENT" = "prod" ]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ Environment variables checked${NC}"
echo ""

# Function to deploy CloudFormation stack
deploy_cloudformation() {
    local stack_name="investforge-unified-$ENVIRONMENT"
    local template_file="infrastructure/cloudformation/unified-architecture.yml"
    
    echo -e "${BLUE}📦 Deploying CloudFormation stack: $stack_name${NC}"
    
    # Check if stack exists
    if $AWS_CMD cloudformation describe-stacks --stack-name $stack_name &> /dev/null; then
        echo "Stack exists, updating..."
        ACTION="update-stack"
    else
        echo "Stack doesn't exist, creating..."
        ACTION="create-stack"
    fi
    
    # Prepare parameters
    PARAMETERS="ParameterKey=Environment,ParameterValue=$ENVIRONMENT"
    PARAMETERS="$PARAMETERS ParameterKey=DomainName,ParameterValue=$DOMAIN"
    
    # Get certificate ARN (you may need to create this first)
    CERT_ARN=$($AWS_CMD acm list-certificates --query "CertificateSummaryList[?DomainName=='$DOMAIN'].CertificateArn" --output text)
    if [ -z "$CERT_ARN" ]; then
        echo -e "${YELLOW}⚠️  No SSL certificate found for $DOMAIN${NC}"
        echo "Please create an ACM certificate first"
        if [ "$ENVIRONMENT" = "prod" ]; then
            exit 1
        fi
    else
        PARAMETERS="$PARAMETERS ParameterKey=CertificateArn,ParameterValue=$CERT_ARN"
    fi
    
    # Get VPC and subnet information
    VPC_ID=$($AWS_CMD ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text)
    PUBLIC_SUBNETS=$($AWS_CMD ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=map-public-ip-on-launch,Values=true" --query "Subnets[].SubnetId" --output text | tr '\t' ',')
    PRIVATE_SUBNETS=$($AWS_CMD ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=map-public-ip-on-launch,Values=false" --query "Subnets[].SubnetId" --output text | tr '\t' ',')
    
    PARAMETERS="$PARAMETERS ParameterKey=VpcId,ParameterValue=$VPC_ID"
    PARAMETERS="$PARAMETERS ParameterKey=PublicSubnetIds,ParameterValue=\"$PUBLIC_SUBNETS\""
    PARAMETERS="$PARAMETERS ParameterKey=PrivateSubnetIds,ParameterValue=\"$PRIVATE_SUBNETS\""
    
    if [ "$DRY_RUN" = true ]; then
        echo "Would deploy CloudFormation stack with parameters:"
        echo "$PARAMETERS"
        return
    fi
    
    # Deploy stack
    $AWS_CMD cloudformation $ACTION \
        --stack-name $stack_name \
        --template-body file://$template_file \
        --parameters $PARAMETERS \
        --capabilities CAPABILITY_IAM \
        --region $REGION
    
    echo "Waiting for stack deployment to complete..."
    $AWS_CMD cloudformation wait stack-${ACTION%-stack}-complete --stack-name $stack_name --region $REGION
    
    echo -e "${GREEN}✅ CloudFormation stack deployed successfully${NC}"
}

# Function to build and push Docker image
build_and_push_image() {
    echo -e "${BLUE}🐳 Building and pushing Docker image...${NC}"
    
    # Create ECR repository if it doesn't exist
    REPO_NAME="investforge/streamlit"
    if ! $AWS_CMD ecr describe-repositories --repository-names $REPO_NAME &> /dev/null; then
        echo "Creating ECR repository..."
        $AWS_CMD ecr create-repository --repository-name $REPO_NAME
    fi
    
    # Get ECR login
    $AWS_CMD ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    
    # Build image
    IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:$ENVIRONMENT"
    
    if [ "$DRY_RUN" = true ]; then
        echo "Would build and push image: $IMAGE_URI"
        return
    fi
    
    docker build -t $IMAGE_URI app/
    docker push $IMAGE_URI
    
    echo -e "${GREEN}✅ Docker image built and pushed: $IMAGE_URI${NC}"
    
    # Update the CloudFormation parameter
    export STREAMLIT_IMAGE=$IMAGE_URI
}

# Function to deploy serverless API
deploy_api() {
    echo -e "${BLUE}⚡ Deploying serverless API...${NC}"
    
    cd api
    
    if [ "$DRY_RUN" = true ]; then
        echo "Would deploy serverless API to environment: $ENVIRONMENT"
        cd ..
        return
    fi
    
    # Install dependencies
    npm install
    
    # Deploy with ALB integration
    npx serverless deploy --config serverless-alb.yml --stage $ENVIRONMENT
    
    cd ..
    echo -e "${GREEN}✅ Serverless API deployed${NC}"
}

# Function to upload landing page to S3
upload_landing_page() {
    echo -e "${BLUE}🌐 Uploading landing page to S3...${NC}"
    
    BUCKET_NAME="investforge-unified-$ENVIRONMENT-landing-$ENVIRONMENT"
    
    if [ "$DRY_RUN" = true ]; then
        echo "Would upload landing page to bucket: $BUCKET_NAME"
        return
    fi
    
    # Upload files
    $AWS_CMD s3 sync landing/ s3://$BUCKET_NAME/ --delete
    
    # Invalidate CloudFront cache
    DISTRIBUTION_ID=$($AWS_CMD cloudformation describe-stacks --stack-name "investforge-unified-$ENVIRONMENT" --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDistributionId'].OutputValue" --output text)
    if [ ! -z "$DISTRIBUTION_ID" ]; then
        $AWS_CMD cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"
    fi
    
    echo -e "${GREEN}✅ Landing page uploaded and cache invalidated${NC}"
}

# Function to update ECS service
update_ecs_service() {
    echo -e "${BLUE}🚢 Updating ECS service...${NC}"
    
    SERVICE_NAME="investforge-unified-$ENVIRONMENT-streamlit-$ENVIRONMENT"
    CLUSTER_NAME="investforge-unified-$ENVIRONMENT-cluster-$ENVIRONMENT"
    
    if [ "$DRY_RUN" = true ]; then
        echo "Would update ECS service: $SERVICE_NAME"
        return
    fi
    
    # Force new deployment
    $AWS_CMD ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment
    
    # Wait for deployment to complete
    echo "Waiting for ECS service to stabilize..."
    $AWS_CMD ecs wait services-stable --cluster $CLUSTER_NAME --services $SERVICE_NAME
    
    echo -e "${GREEN}✅ ECS service updated${NC}"
}

# Main deployment sequence
main() {
    echo -e "${BLUE}🎯 Starting unified deployment...${NC}"
    echo ""
    
    # Step 1: Deploy infrastructure
    deploy_cloudformation
    echo ""
    
    # Step 2: Build and push Docker image
    build_and_push_image
    echo ""
    
    # Step 3: Deploy serverless API
    deploy_api
    echo ""
    
    # Step 4: Upload landing page
    upload_landing_page
    echo ""
    
    # Step 5: Update ECS service with new image
    update_ecs_service
    echo ""
    
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}📋 Deployment Summary:${NC}"
    echo -e "Domain: ${GREEN}https://$DOMAIN${NC}"
    echo -e "Landing Page: ${GREEN}https://$DOMAIN${NC}"
    echo -e "App: ${GREEN}https://$DOMAIN/app${NC}"
    echo -e "API: ${GREEN}https://$DOMAIN/api${NC}"
    echo ""
    echo -e "${YELLOW}📝 Next Steps:${NC}"
    echo "1. Update DNS to point to CloudFront distribution"
    echo "2. Configure Stripe webhook URL: https://$DOMAIN/api/stripe/webhook"
    echo "3. Verify SES domain in AWS Console"
    echo "4. Test all endpoints"
}

# Run main function
main