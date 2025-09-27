#!/bin/bash
# =====================================
# InvestForge Automated Schedule Setup
# Sets up automated start/stop schedule using AWS EventBridge
# =====================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== InvestForge Schedule Setup ===${NC}"
echo -e "Configure automated start/stop times to maximize cost savings"
echo ""

# Configuration
REGION="us-east-1"
LAMBDA_ROLE_NAME="InvestForgeSchedulerRole"
START_LAMBDA_NAME="investforge-scheduled-start"
STOP_LAMBDA_NAME="investforge-scheduled-stop"

# Function to create IAM role for Lambda
create_lambda_role() {
    echo -e "${YELLOW}Creating IAM role for scheduler Lambda...${NC}"
    
    # Check if role exists
    ROLE_EXISTS=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query "Role.RoleName" --output text 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$ROLE_EXISTS" = "NOT_FOUND" ]; then
        # Create trust policy
        cat > /tmp/trust-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
    }]
}
EOF
        
        # Create role
        aws iam create-role \
            --role-name $LAMBDA_ROLE_NAME \
            --assume-role-policy-document file:///tmp/trust-policy.json \
            --description "Role for InvestForge scheduler Lambda functions" \
            --output json > /dev/null
        
        # Attach policies
        aws iam attach-role-policy \
            --role-name $LAMBDA_ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
        
        # Create inline policy for ECS
        cat > /tmp/ecs-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": [
            "ecs:UpdateService",
            "ecs:DescribeServices",
            "ecs:DescribeClusters"
        ],
        "Resource": "*"
    }]
}
EOF
        
        aws iam put-role-policy \
            --role-name $LAMBDA_ROLE_NAME \
            --policy-name ECSUpdatePolicy \
            --policy-document file:///tmp/ecs-policy.json
        
        echo -e "${GREEN}✓ IAM role created${NC}"
        
        # Wait for role to propagate
        sleep 10
    else
        echo -e "${GREEN}✓ IAM role already exists${NC}"
    fi
}

# Function to create Lambda functions
create_lambda_functions() {
    echo -e "${YELLOW}Creating Lambda functions for scheduling...${NC}"
    
    # Get role ARN
    ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query "Role.Arn" --output text)
    
    # Create start function
    cat > /tmp/start-function.py <<EOF
import json
import boto3

def lambda_handler(event, context):
    ecs = boto3.client('ecs')
    
    try:
        # Start ECS service
        response = ecs.update_service(
            cluster='financial-analysis-cluster',
            service='financial-analysis-service',
            desiredCount=1
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps('InvestForge started successfully')
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error starting InvestForge: {str(e)}')
        }
EOF

    # Create stop function
    cat > /tmp/stop-function.py <<EOF
import json
import boto3

def lambda_handler(event, context):
    ecs = boto3.client('ecs')
    
    try:
        # Stop ECS service
        response = ecs.update_service(
            cluster='financial-analysis-cluster',
            service='financial-analysis-service',
            desiredCount=0
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps('InvestForge stopped successfully')
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error stopping InvestForge: {str(e)}')
        }
EOF

    # Zip the functions
    cd /tmp
    zip start-function.zip start-function.py
    zip stop-function.zip stop-function.py
    
    # Create/Update Lambda functions
    for func in "start" "stop"; do
        FUNC_NAME="investforge-scheduled-${func}"
        
        # Check if function exists
        FUNC_EXISTS=$(aws lambda get-function --function-name $FUNC_NAME --query "Configuration.FunctionName" --output text 2>/dev/null || echo "NOT_FOUND")
        
        if [ "$FUNC_EXISTS" = "NOT_FOUND" ]; then
            aws lambda create-function \
                --function-name $FUNC_NAME \
                --runtime python3.9 \
                --role $ROLE_ARN \
                --handler "${func}-function.lambda_handler" \
                --zip-file "fileb:///tmp/${func}-function.zip" \
                --description "Scheduled ${func} for InvestForge" \
                --timeout 60 \
                --region $REGION \
                --output json > /dev/null
            echo -e "${GREEN}✓ Created $FUNC_NAME Lambda function${NC}"
        else
            aws lambda update-function-code \
                --function-name $FUNC_NAME \
                --zip-file "fileb:///tmp/${func}-function.zip" \
                --region $REGION \
                --output json > /dev/null
            echo -e "${GREEN}✓ Updated $FUNC_NAME Lambda function${NC}"
        fi
    done
}

# Function to setup EventBridge rules
setup_eventbridge_rules() {
    echo ""
    echo -e "${BLUE}=== Schedule Configuration ===${NC}"
    echo "Choose your schedule (all times in UTC):"
    echo "1) Business hours only (9 AM - 5 PM EST = 2 PM - 10 PM UTC)"
    echo "2) Extended hours (8 AM - 8 PM EST = 1 PM - 1 AM UTC)"
    echo "3) Weekdays only (Monday-Friday)"
    echo "4) Custom schedule"
    echo "5) Skip scheduling (manual control only)"
    echo ""
    
    read -p "Select option (1-5): " SCHEDULE_OPTION
    
    case $SCHEDULE_OPTION in
        1)
            # Business hours
            START_CRON="cron(0 14 ? * MON-FRI *)"  # 2 PM UTC (9 AM EST)
            STOP_CRON="cron(0 22 ? * MON-FRI *)"   # 10 PM UTC (5 PM EST)
            SCHEDULE_DESC="Business hours (9 AM - 5 PM EST)"
            ;;
        2)
            # Extended hours
            START_CRON="cron(0 13 ? * * *)"        # 1 PM UTC (8 AM EST)
            STOP_CRON="cron(0 1 ? * * *)"          # 1 AM UTC (8 PM EST)
            SCHEDULE_DESC="Extended hours (8 AM - 8 PM EST)"
            ;;
        3)
            # Weekdays only
            START_CRON="cron(0 13 ? * MON-FRI *)"  # 1 PM UTC Monday-Friday
            STOP_CRON="cron(0 23 ? * MON-FRI *)"   # 11 PM UTC Monday-Friday
            SCHEDULE_DESC="Weekdays only"
            ;;
        4)
            # Custom
            echo ""
            echo "Enter custom cron expressions (UTC time)"
            echo "Format: cron(minute hour day month day-of-week year)"
            echo "Example: cron(0 14 ? * MON-FRI *) = 2 PM UTC weekdays"
            read -p "Start time cron: " START_CRON
            read -p "Stop time cron: " STOP_CRON
            SCHEDULE_DESC="Custom schedule"
            ;;
        5)
            echo -e "${YELLOW}Skipping schedule setup. Use manual scripts only.${NC}"
            return
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            return
            ;;
    esac
    
    echo -e "${YELLOW}Setting up schedule: $SCHEDULE_DESC${NC}"
    
    # Create EventBridge rules
    for action in "start" "stop"; do
        RULE_NAME="investforge-scheduled-${action}"
        LAMBDA_ARN=$(aws lambda get-function --function-name investforge-scheduled-${action} --query "Configuration.FunctionArn" --output text)
        
        if [ "$action" = "start" ]; then
            CRON_EXPR=$START_CRON
        else
            CRON_EXPR=$STOP_CRON
        fi
        
        # Create/Update rule
        aws events put-rule \
            --name $RULE_NAME \
            --schedule-expression "$CRON_EXPR" \
            --description "Scheduled $action for InvestForge - $SCHEDULE_DESC" \
            --state ENABLED \
            --region $REGION \
            --output json > /dev/null
        
        # Add Lambda permission
        aws lambda add-permission \
            --function-name investforge-scheduled-${action} \
            --statement-id AllowEventBridge-${action} \
            --action lambda:InvokeFunction \
            --principal events.amazonaws.com \
            --source-arn "arn:aws:events:${REGION}:453636587892:rule/${RULE_NAME}" \
            --region $REGION 2>/dev/null || true
        
        # Add target
        aws events put-targets \
            --rule $RULE_NAME \
            --targets "Id=1,Arn=${LAMBDA_ARN}" \
            --region $REGION \
            --output json > /dev/null
        
        echo -e "${GREEN}✓ Created $action rule: $CRON_EXPR${NC}"
    done
}

# Function to display schedule info
display_schedule_info() {
    echo ""
    echo -e "${BLUE}=== Current Schedule ===${NC}"
    
    for action in "start" "stop"; do
        RULE_NAME="investforge-scheduled-${action}"
        
        RULE_INFO=$(aws events describe-rule \
            --name $RULE_NAME \
            --region $REGION \
            --query "{schedule:ScheduleExpression,state:State}" \
            --output json 2>/dev/null || echo "{}")
        
        if [ "$RULE_INFO" != "{}" ]; then
            SCHEDULE=$(echo $RULE_INFO | jq -r '.schedule // "Not set"')
            STATE=$(echo $RULE_INFO | jq -r '.state // "Unknown"')
            
            echo -e "${action^} time: ${GREEN}$SCHEDULE${NC} (${STATE})"
        fi
    done
    
    echo ""
    echo -e "${YELLOW}Note: All times are in UTC${NC}"
    echo -e "Current UTC time: $(date -u '+%Y-%m-%d %H:%M:%S')"
}

# Function to calculate cost savings
calculate_schedule_savings() {
    echo ""
    echo -e "${BLUE}=== Estimated Savings with Schedule ===${NC}"
    
    case $SCHEDULE_OPTION in
        1)
            # Business hours: 8 hours/day, 5 days/week
            HOURS_PER_WEEK=40
            ;;
        2)
            # Extended hours: 12 hours/day, 7 days/week
            HOURS_PER_WEEK=84
            ;;
        3)
            # Weekdays: 10 hours/day, 5 days/week
            HOURS_PER_WEEK=50
            ;;
        *)
            HOURS_PER_WEEK=40  # Default estimate
            ;;
    esac
    
    HOURS_PER_MONTH=$(echo "$HOURS_PER_WEEK * 4.33" | bc -l 2>/dev/null || echo "173")
    RUNNING_COST=$(echo "$HOURS_PER_MONTH * 0.05" | bc -l 2>/dev/null || echo "8.65")
    TOTAL_HOURS=720  # Hours in a month
    SAVED_HOURS=$(echo "$TOTAL_HOURS - $HOURS_PER_MONTH" | bc -l 2>/dev/null || echo "547")
    SAVED_COST=$(echo "$SAVED_HOURS * 0.05" | bc -l 2>/dev/null || echo "27.35")
    
    printf "Running hours per month: %.0f\n" $HOURS_PER_MONTH
    printf "Running cost: \$%.2f\n" $RUNNING_COST
    printf "Saved hours: %.0f\n" $SAVED_HOURS
    printf "${GREEN}Monthly savings: \$%.2f${NC}\n" $SAVED_COST
}

# Main execution
main() {
    echo -e "${YELLOW}This will set up automated scheduling for InvestForge${NC}"
    echo ""
    
    # Create IAM role
    create_lambda_role
    
    # Create Lambda functions
    create_lambda_functions
    
    # Setup EventBridge rules
    setup_eventbridge_rules
    
    # Display current schedule
    display_schedule_info
    
    # Calculate savings
    if [ "$SCHEDULE_OPTION" != "5" ]; then
        calculate_schedule_savings
    fi
    
    echo ""
    echo -e "${GREEN}=== Setup Complete ===${NC}"
    echo ""
    echo -e "${BLUE}Manual control scripts:${NC}"
    echo -e "  ./investforge-shutdown.sh - Stop immediately"
    echo -e "  ./investforge-startup.sh  - Start immediately"
    echo -e "  ./investforge-status.sh   - Check current status"
    echo ""
    
    # Clean up
    rm -f /tmp/trust-policy.json /tmp/ecs-policy.json
    rm -f /tmp/start-function.* /tmp/stop-function.*
}

# Run main function
main