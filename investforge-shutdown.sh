#!/bin/bash
# =====================================
# InvestForge AWS Resources Shutdown Script
# Saves AWS costs by stopping resources when not in use
# =====================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== InvestForge Resources Shutdown Script ===${NC}"
echo -e "${YELLOW}This will stop ECS services and other resources to save costs${NC}"
echo ""

# Configuration
CLUSTER_NAME="financial-analysis-cluster"
SERVICE_NAME="financial-analysis-service"
REGION="us-east-1"

# Function to check if AWS CLI is installed
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
        exit 1
    fi
}

# Function to save current state
save_state() {
    echo -e "${YELLOW}Saving current state...${NC}"
    
    # Save ECS service desired count
    CURRENT_COUNT=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $REGION \
        --query "services[0].desiredCount" \
        --output text)
    
    echo "{
        \"ecs_desired_count\": $CURRENT_COUNT,
        \"shutdown_time\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
        \"cluster\": \"$CLUSTER_NAME\",
        \"service\": \"$SERVICE_NAME\"
    }" > investforge-state.json
    
    echo -e "${GREEN}✓ State saved to investforge-state.json${NC}"
}

# Function to scale down ECS service
scale_down_ecs() {
    echo -e "${YELLOW}Scaling down ECS service...${NC}"
    
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --desired-count 0 \
        --region $REGION \
        --output json > /dev/null
    
    echo -e "${GREEN}✓ ECS service scaled down to 0 tasks${NC}"
    
    # Wait for tasks to stop
    echo -e "${YELLOW}Waiting for tasks to stop...${NC}"
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $REGION
    
    echo -e "${GREEN}✓ All tasks stopped${NC}"
}

# Function to check ALB target health
check_alb_targets() {
    echo -e "${YELLOW}Checking ALB targets...${NC}"
    
    # Get target group ARN
    TG_ARN=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $REGION \
        --query "services[0].loadBalancers[0].targetGroupArn" \
        --output text)
    
    if [ "$TG_ARN" != "None" ] && [ -n "$TG_ARN" ]; then
        # Check target health
        HEALTHY_COUNT=$(aws elbv2 describe-target-health \
            --target-group-arn $TG_ARN \
            --region $REGION \
            --query "length(TargetHealthDescriptions[?TargetHealth.State=='healthy'])" \
            --output text)
        
        echo -e "${GREEN}✓ ALB has $HEALTHY_COUNT healthy targets (should be 0)${NC}"
    fi
}

# Function to display cost savings estimate
display_cost_savings() {
    echo ""
    echo -e "${GREEN}=== Estimated Cost Savings ===${NC}"
    echo "ECS Fargate (1 vCPU, 2GB RAM):"
    echo "  - Per hour: ~\$0.05"
    echo "  - Per day: ~\$1.20"
    echo "  - Per month: ~\$36"
    echo ""
    echo "ALB costs continue (fixed ~\$16/month) as it's needed for domain"
    echo "Lambda & DynamoDB remain free tier or pay-per-use"
    echo ""
    echo -e "${GREEN}Total monthly savings: ~\$36 when not in use${NC}"
}

# Main execution
main() {
    echo -e "${YELLOW}Starting shutdown process...${NC}"
    echo ""
    
    # Check prerequisites
    check_aws_cli
    
    # Save current state
    save_state
    
    # Scale down ECS
    scale_down_ecs
    
    # Check ALB targets
    check_alb_targets
    
    # Display cost savings
    display_cost_savings
    
    echo ""
    echo -e "${GREEN}=== Shutdown Complete ===${NC}"
    echo -e "${YELLOW}Resources have been stopped to save costs.${NC}"
    echo -e "${YELLOW}To restart, run: ./investforge-startup.sh${NC}"
    echo ""
    
    # Log shutdown
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) - Resources shut down" >> investforge-ops.log
}

# Run main function
main