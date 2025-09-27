#!/bin/bash
# =====================================
# InvestForge AWS Resources Startup Script
# Restarts resources after shutdown
# =====================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== InvestForge Resources Startup Script ===${NC}"
echo -e "${YELLOW}This will restart ECS services and verify health${NC}"
echo ""

# Configuration
CLUSTER_NAME="financial-analysis-cluster"
SERVICE_NAME="financial-analysis-service"
REGION="us-east-1"
APP_URL="https://investforge.io/app"

# Function to check if AWS CLI is installed
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
        exit 1
    fi
}

# Function to load saved state
load_state() {
    if [ -f "investforge-state.json" ]; then
        echo -e "${YELLOW}Loading saved state...${NC}"
        DESIRED_COUNT=$(cat investforge-state.json | grep -o '"ecs_desired_count": [0-9]*' | grep -o '[0-9]*')
        if [ -z "$DESIRED_COUNT" ] || [ "$DESIRED_COUNT" -eq 0 ]; then
            DESIRED_COUNT=1
        fi
        echo -e "${GREEN}✓ Will restore to $DESIRED_COUNT tasks${NC}"
    else
        echo -e "${YELLOW}No saved state found, defaulting to 1 task${NC}"
        DESIRED_COUNT=1
    fi
}

# Function to scale up ECS service
scale_up_ecs() {
    echo -e "${YELLOW}Scaling up ECS service...${NC}"
    
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --desired-count $DESIRED_COUNT \
        --region $REGION \
        --output json > /dev/null
    
    echo -e "${GREEN}✓ ECS service scaled up to $DESIRED_COUNT task(s)${NC}"
    
    # Wait for service to stabilize
    echo -e "${YELLOW}Waiting for service to stabilize (this may take 2-3 minutes)...${NC}"
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $REGION
    
    echo -e "${GREEN}✓ Service is stable${NC}"
}

# Function to check ALB health
check_alb_health() {
    echo -e "${YELLOW}Checking ALB target health...${NC}"
    
    # Get target group ARN
    TG_ARN=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $REGION \
        --query "services[0].loadBalancers[0].targetGroupArn" \
        --output text)
    
    if [ "$TG_ARN" != "None" ] && [ -n "$TG_ARN" ]; then
        # Wait for targets to be healthy
        echo -e "${YELLOW}Waiting for targets to become healthy...${NC}"
        
        MAX_ATTEMPTS=30
        ATTEMPT=0
        
        while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
            HEALTHY_COUNT=$(aws elbv2 describe-target-health \
                --target-group-arn $TG_ARN \
                --region $REGION \
                --query "length(TargetHealthDescriptions[?TargetHealth.State=='healthy'])" \
                --output text)
            
            if [ "$HEALTHY_COUNT" -ge 1 ]; then
                echo -e "${GREEN}✓ ALB has $HEALTHY_COUNT healthy target(s)${NC}"
                break
            fi
            
            echo -e "${YELLOW}  Waiting... (attempt $((ATTEMPT + 1))/$MAX_ATTEMPTS)${NC}"
            sleep 10
            ATTEMPT=$((ATTEMPT + 1))
        done
        
        if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
            echo -e "${RED}⚠️  Warning: Targets may not be healthy yet${NC}"
        fi
    fi
}

# Function to verify application health
verify_app_health() {
    echo -e "${YELLOW}Verifying application health...${NC}"
    
    # Check main app endpoint
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL" --max-time 10 || echo "000")
    
    if [ "$HTTP_STATUS" = "200" ]; then
        echo -e "${GREEN}✓ Application is responding (HTTP $HTTP_STATUS)${NC}"
    else
        echo -e "${RED}⚠️  Application returned HTTP $HTTP_STATUS${NC}"
        echo -e "${YELLOW}   It may need a few more minutes to warm up${NC}"
    fi
    
    # Check API health
    API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://investforge.io/api/health" --max-time 10 || echo "000")
    
    if [ "$API_STATUS" = "200" ]; then
        echo -e "${GREEN}✓ API is healthy (HTTP $API_STATUS)${NC}"
    else
        echo -e "${YELLOW}⚠️  API returned HTTP $API_STATUS${NC}"
    fi
}

# Function to display access information
display_access_info() {
    echo ""
    echo -e "${BLUE}=== Access Information ===${NC}"
    echo -e "Application URL: ${GREEN}$APP_URL${NC}"
    echo -e "API Health Check: ${GREEN}https://investforge.io/api/health${NC}"
    echo ""
    
    # Get task details
    TASK_ARN=$(aws ecs list-tasks \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --region $REGION \
        --query "taskArns[0]" \
        --output text)
    
    if [ "$TASK_ARN" != "None" ] && [ -n "$TASK_ARN" ]; then
        echo -e "${YELLOW}Task ARN:${NC} $TASK_ARN"
    fi
}

# Function to display cost information
display_cost_info() {
    echo ""
    echo -e "${YELLOW}=== Cost Information ===${NC}"
    echo "Resources now running:"
    echo "  - ECS Fargate: ~\$0.05/hour"
    echo "  - ALB: ~\$0.022/hour (always running)"
    echo "  - Lambda: Pay per request"
    echo "  - DynamoDB: Free tier / On-demand"
    echo ""
    echo -e "${YELLOW}Remember to shut down when not needed: ./investforge-shutdown.sh${NC}"
}

# Main execution
main() {
    echo -e "${YELLOW}Starting startup process...${NC}"
    echo ""
    
    # Check prerequisites
    check_aws_cli
    
    # Load saved state
    load_state
    
    # Scale up ECS
    scale_up_ecs
    
    # Check ALB health
    check_alb_health
    
    # Verify application
    verify_app_health
    
    # Display access info
    display_access_info
    
    # Display cost info
    display_cost_info
    
    echo ""
    echo -e "${GREEN}=== Startup Complete ===${NC}"
    echo -e "${GREEN}InvestForge is now accessible at: $APP_URL${NC}"
    echo ""
    
    # Log startup
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) - Resources started" >> investforge-ops.log
}

# Run main function
main