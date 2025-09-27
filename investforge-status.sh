#!/bin/bash
# =====================================
# InvestForge Resources Status Check Script
# Shows current status and costs of all resources
# =====================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== InvestForge Resources Status ===${NC}"
echo -e "Checking all AWS resources..."
echo ""

# Configuration
CLUSTER_NAME="financial-analysis-cluster"
SERVICE_NAME="financial-analysis-service"
REGION="us-east-1"

# Function to format costs
format_cost() {
    printf "\$%.2f" $1
}

# Check ECS Service
check_ecs_status() {
    echo -e "${PURPLE}ECS Fargate Service:${NC}"
    
    # Get service details
    SERVICE_INFO=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $REGION \
        --query "services[0].{desired:desiredCount,running:runningCount,pending:pendingCount,status:status}" \
        --output json 2>/dev/null || echo "{}")
    
    if [ "$SERVICE_INFO" != "{}" ]; then
        DESIRED=$(echo $SERVICE_INFO | jq -r '.desired // 0')
        RUNNING=$(echo $SERVICE_INFO | jq -r '.running // 0')
        PENDING=$(echo $SERVICE_INFO | jq -r '.pending // 0')
        STATUS=$(echo $SERVICE_INFO | jq -r '.status // "UNKNOWN"')
        
        echo -e "  Status: ${GREEN}$STATUS${NC}"
        echo -e "  Tasks: Running=$RUNNING, Desired=$DESIRED, Pending=$PENDING"
        
        # Calculate hourly cost
        HOURLY_COST=$(echo "$RUNNING * 0.05" | bc -l 2>/dev/null || echo "0")
        DAILY_COST=$(echo "$HOURLY_COST * 24" | bc -l 2>/dev/null || echo "0")
        
        if [ "$RUNNING" -gt 0 ]; then
            echo -e "  Cost: ${YELLOW}$(format_cost $HOURLY_COST)/hour, $(format_cost $DAILY_COST)/day${NC}"
        else
            echo -e "  Cost: ${GREEN}\$0.00/hour (stopped)${NC}"
        fi
    else
        echo -e "  ${RED}Service not found or error accessing${NC}"
    fi
    echo ""
}

# Check ALB Status
check_alb_status() {
    echo -e "${PURPLE}Application Load Balancer:${NC}"
    
    # Get ALB info
    ALB_ARN="arn:aws:elasticloadbalancing:us-east-1:453636587892:loadbalancer/app/financial-analysis-alb/62c0d1c63c94cf90"
    
    ALB_INFO=$(aws elbv2 describe-load-balancers \
        --load-balancer-arns $ALB_ARN \
        --region $REGION \
        --query "LoadBalancers[0].{state:State.Code,dns:DNSName}" \
        --output json 2>/dev/null || echo "{}")
    
    if [ "$ALB_INFO" != "{}" ]; then
        STATE=$(echo $ALB_INFO | jq -r '.state // "unknown"')
        echo -e "  Status: ${GREEN}$STATE${NC}"
        echo -e "  Cost: ${YELLOW}\$0.022/hour, \$16.00/month (always running)${NC}"
    else
        echo -e "  ${RED}ALB not found${NC}"
    fi
    echo ""
}

# Check Lambda Functions
check_lambda_status() {
    echo -e "${PURPLE}Lambda Functions:${NC}"
    
    LAMBDA_FUNCTIONS=("investforge-health" "investforge-signup" "investforge-analytics" "investforge-waitlist")
    TOTAL_INVOCATIONS=0
    
    for func in "${LAMBDA_FUNCTIONS[@]}"; do
        # Get function state
        STATE=$(aws lambda get-function \
            --function-name $func \
            --region $REGION \
            --query "Configuration.State" \
            --output text 2>/dev/null || echo "NOT_FOUND")
        
        if [ "$STATE" != "NOT_FOUND" ]; then
            echo -e "  $func: ${GREEN}$STATE${NC}"
        fi
    done
    
    echo -e "  Cost: ${GREEN}Free tier (< 1M requests/month)${NC}"
    echo ""
}

# Check DynamoDB Tables
check_dynamodb_status() {
    echo -e "${PURPLE}DynamoDB Tables:${NC}"
    
    TABLES=("investforge-analytics" "investforge-usage" "investforge-users-simple")
    
    for table in "${TABLES[@]}"; do
        STATUS=$(aws dynamodb describe-table \
            --table-name $table \
            --region $REGION \
            --query "Table.TableStatus" \
            --output text 2>/dev/null || echo "NOT_FOUND")
        
        if [ "$STATUS" != "NOT_FOUND" ]; then
            echo -e "  $table: ${GREEN}$STATUS${NC}"
        fi
    done
    
    echo -e "  Cost: ${GREEN}On-demand pricing (pay per request)${NC}"
    echo ""
}

# Check Recent Activity
check_recent_activity() {
    echo -e "${PURPLE}Recent Activity:${NC}"
    
    if [ -f "investforge-ops.log" ]; then
        LAST_ENTRIES=$(tail -n 3 investforge-ops.log 2>/dev/null || echo "No activity logged")
        echo "$LAST_ENTRIES" | while IFS= read -r line; do
            echo -e "  $line"
        done
    else
        echo -e "  No activity log found"
    fi
    echo ""
}

# Calculate Total Costs
calculate_total_costs() {
    echo -e "${PURPLE}=== Cost Summary ===${NC}"
    
    # Get running tasks
    RUNNING_TASKS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $REGION \
        --query "services[0].runningCount" \
        --output text 2>/dev/null || echo "0")
    
    # Calculate costs
    ECS_HOURLY=$(echo "$RUNNING_TASKS * 0.05" | bc -l 2>/dev/null || echo "0")
    ALB_HOURLY=0.022
    TOTAL_HOURLY=$(echo "$ECS_HOURLY + $ALB_HOURLY" | bc -l 2>/dev/null || echo "0.022")
    TOTAL_DAILY=$(echo "$TOTAL_HOURLY * 24" | bc -l 2>/dev/null || echo "0.528")
    TOTAL_MONTHLY=$(echo "$TOTAL_DAILY * 30" | bc -l 2>/dev/null || echo "15.84")
    
    echo -e "Current hourly cost: ${YELLOW}$(format_cost $TOTAL_HOURLY)${NC}"
    echo -e "Current daily cost: ${YELLOW}$(format_cost $TOTAL_DAILY)${NC}"
    echo -e "Projected monthly: ${YELLOW}$(format_cost $TOTAL_MONTHLY)${NC}"
    
    if [ "$RUNNING_TASKS" -eq "0" ]; then
        echo ""
        echo -e "${GREEN}💰 ECS is stopped - saving \$36/month!${NC}"
    fi
}

# Main execution
main() {
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    # Check each service
    check_ecs_status
    check_alb_status
    check_lambda_status
    check_dynamodb_status
    check_recent_activity
    calculate_total_costs
    
    echo ""
    echo -e "${BLUE}=== Quick Commands ===${NC}"
    echo -e "Stop resources:  ${YELLOW}./investforge-shutdown.sh${NC}"
    echo -e "Start resources: ${YELLOW}./investforge-startup.sh${NC}"
    echo -e "View logs:       ${YELLOW}aws logs tail /ecs/financial-analysis --follow${NC}"
    echo ""
}

# Run main function
main