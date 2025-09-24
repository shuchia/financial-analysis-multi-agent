#!/bin/bash

# Configure ALB Path-Based Routing for InvestForge
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${BLUE}🔧 Configuring ALB Path-Based Routing for InvestForge${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""

# Configuration
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Function to find ALB by name or tags
find_alb() {
    echo -e "${BLUE}🔍 Looking for existing ALB...${NC}"
    
    # Try to find ALB with investforge in name
    ALB_ARN=$(aws elbv2 describe-load-balancers --query "LoadBalancers[?contains(LoadBalancerName, 'investforge')].LoadBalancerArn" --output text --region $REGION | head -1)
    
    if [[ -z "$ALB_ARN" || "$ALB_ARN" == "None" ]]; then
        # Try to find any ALB (user can specify)
        echo -e "${YELLOW}⚠️  No ALB found with 'investforge' in name${NC}"
        echo "Available ALBs:"
        aws elbv2 describe-load-balancers --query "LoadBalancers[?Type=='application'].[LoadBalancerName,LoadBalancerArn]" --output table --region $REGION
        echo ""
        read -p "Please enter the ALB ARN or name: " USER_ALB
        
        if [[ $USER_ALB == arn:* ]]; then
            ALB_ARN=$USER_ALB
        else
            ALB_ARN=$(aws elbv2 describe-load-balancers --names "$USER_ALB" --query "LoadBalancers[0].LoadBalancerArn" --output text --region $REGION 2>/dev/null || echo "")
        fi
    fi
    
    if [[ -z "$ALB_ARN" || "$ALB_ARN" == "None" ]]; then
        echo -e "${RED}❌ Could not find specified ALB${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Found ALB: $ALB_ARN${NC}"
    return 0
}

# Function to get ALB listener
get_https_listener() {
    echo -e "${BLUE}🔍 Finding HTTPS listener...${NC}"
    
    LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --query "Listeners[?Port==\`443\`].ListenerArn" --output text --region $REGION | head -1)
    
    if [[ -z "$LISTENER_ARN" || "$LISTENER_ARN" == "None" ]]; then
        echo -e "${YELLOW}⚠️  No HTTPS listener found, checking for HTTP listener...${NC}"
        LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --query "Listeners[?Port==\`80\`].ListenerArn" --output text --region $REGION | head -1)
    fi
    
    if [[ -z "$LISTENER_ARN" || "$LISTENER_ARN" == "None" ]]; then
        echo -e "${RED}❌ No HTTP/HTTPS listener found on ALB${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Found listener: $LISTENER_ARN${NC}"
    return 0
}

# Function to find Lambda target groups
find_lambda_target_groups() {
    echo -e "${BLUE}🔍 Finding Lambda target groups...${NC}"
    
    # Look for target groups created by our deployment
    HEALTH_TG_ARN=$(aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName, 'lambda-health')].TargetGroupArn" --output text --region $REGION | head -1)
    AUTH_TG_ARN=$(aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName, 'lambda-auth')].TargetGroupArn" --output text --region $REGION | head -1)
    WAITLIST_TG_ARN=$(aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName, 'lambda-waitlist')].TargetGroupArn" --output text --region $REGION | head -1)
    ANALYTICS_TG_ARN=$(aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName, 'lambda-analytics')].TargetGroupArn" --output text --region $REGION | head -1)
    
    # If not found, try investforge prefix
    if [[ -z "$HEALTH_TG_ARN" || "$HEALTH_TG_ARN" == "None" ]]; then
        HEALTH_TG_ARN=$(aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName, 'investforge') && contains(TargetGroupName, 'health')].TargetGroupArn" --output text --region $REGION | head -1)
    fi
    
    if [[ -z "$AUTH_TG_ARN" || "$AUTH_TG_ARN" == "None" ]]; then
        AUTH_TG_ARN=$(aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName, 'investforge') && contains(TargetGroupName, 'auth')].TargetGroupArn" --output text --region $REGION | head -1)
    fi
    
    if [[ -z "$WAITLIST_TG_ARN" || "$WAITLIST_TG_ARN" == "None" ]]; then
        WAITLIST_TG_ARN=$(aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName, 'investforge') && contains(TargetGroupName, 'waitlist')].TargetGroupArn" --output text --region $REGION | head -1)
    fi
    
    if [[ -z "$ANALYTICS_TG_ARN" || "$ANALYTICS_TG_ARN" == "None" ]]; then
        ANALYTICS_TG_ARN=$(aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName, 'investforge') && contains(TargetGroupName, 'analytics')].TargetGroupArn" --output text --region $REGION | head -1)
    fi
    
    echo "Found target groups:"
    echo "  Health: $HEALTH_TG_ARN"
    echo "  Auth: $AUTH_TG_ARN"
    echo "  Waitlist: $WAITLIST_TG_ARN"
    echo "  Analytics: $ANALYTICS_TG_ARN"
    echo ""
}

# Function to create Lambda target groups if they don't exist
create_lambda_target_groups() {
    echo -e "${BLUE}🏗️  Creating Lambda target groups...${NC}"
    
    # Get VPC ID from ALB
    VPC_ID=$(aws elbv2 describe-load-balancers --load-balancer-arns "$ALB_ARN" --query "LoadBalancers[0].VpcId" --output text --region $REGION)
    
    # Create target groups for each Lambda function
    if [[ -z "$HEALTH_TG_ARN" || "$HEALTH_TG_ARN" == "None" ]]; then
        HEALTH_TG_ARN=$(aws elbv2 create-target-group \
            --name "investforge-lambda-health" \
            --target-type lambda \
            --vpc-id "$VPC_ID" \
            --region $REGION \
            --query "TargetGroups[0].TargetGroupArn" \
            --output text)
        echo -e "${GREEN}✅ Created health target group: $HEALTH_TG_ARN${NC}"
    fi
    
    if [[ -z "$AUTH_TG_ARN" || "$AUTH_TG_ARN" == "None" ]]; then
        AUTH_TG_ARN=$(aws elbv2 create-target-group \
            --name "investforge-lambda-auth" \
            --target-type lambda \
            --vpc-id "$VPC_ID" \
            --region $REGION \
            --query "TargetGroups[0].TargetGroupArn" \
            --output text)
        echo -e "${GREEN}✅ Created auth target group: $AUTH_TG_ARN${NC}"
    fi
    
    if [[ -z "$WAITLIST_TG_ARN" || "$WAITLIST_TG_ARN" == "None" ]]; then
        WAITLIST_TG_ARN=$(aws elbv2 create-target-group \
            --name "investforge-lambda-waitlist" \
            --target-type lambda \
            --vpc-id "$VPC_ID" \
            --region $REGION \
            --query "TargetGroups[0].TargetGroupArn" \
            --output text)
        echo -e "${GREEN}✅ Created waitlist target group: $WAITLIST_TG_ARN${NC}"
    fi
    
    if [[ -z "$ANALYTICS_TG_ARN" || "$ANALYTICS_TG_ARN" == "None" ]]; then
        ANALYTICS_TG_ARN=$(aws elbv2 create-target-group \
            --name "investforge-lambda-analytics" \
            --target-type lambda \
            --vpc-id "$VPC_ID" \
            --region $REGION \
            --query "TargetGroups[0].TargetGroupArn" \
            --output text)
        echo -e "${GREEN}✅ Created analytics target group: $ANALYTICS_TG_ARN${NC}"
    fi
}

# Function to register Lambda functions with target groups
register_lambda_functions() {
    echo -e "${BLUE}🔗 Registering Lambda functions with target groups...${NC}"
    
    # Get Lambda function ARNs
    HEALTH_LAMBDA_ARN=$(aws lambda get-function --function-name "investforge-api-prod-health" --query "Configuration.FunctionArn" --output text --region $REGION 2>/dev/null || echo "")
    SIGNUP_LAMBDA_ARN=$(aws lambda get-function --function-name "investforge-api-prod-signup" --query "Configuration.FunctionArn" --output text --region $REGION 2>/dev/null || echo "")
    WAITLIST_LAMBDA_ARN=$(aws lambda get-function --function-name "investforge-api-prod-join_waitlist" --query "Configuration.FunctionArn" --output text --region $REGION 2>/dev/null || echo "")
    ANALYTICS_LAMBDA_ARN=$(aws lambda get-function --function-name "investforge-api-prod-track_event" --query "Configuration.FunctionArn" --output text --region $REGION 2>/dev/null || echo "")
    
    # Register functions with target groups
    if [[ -n "$HEALTH_LAMBDA_ARN" && "$HEALTH_LAMBDA_ARN" != "None" && -n "$HEALTH_TG_ARN" ]]; then
        aws elbv2 register-targets --target-group-arn "$HEALTH_TG_ARN" --targets Id="$HEALTH_LAMBDA_ARN" --region $REGION
        aws lambda add-permission --function-name "$HEALTH_LAMBDA_ARN" --statement-id "alb-health-$(date +%s)" --action lambda:InvokeFunction --principal elasticloadbalancing.amazonaws.com --source-arn "$HEALTH_TG_ARN" --region $REGION 2>/dev/null || true
        echo -e "${GREEN}✅ Registered health function${NC}"
    fi
    
    if [[ -n "$SIGNUP_LAMBDA_ARN" && "$SIGNUP_LAMBDA_ARN" != "None" && -n "$AUTH_TG_ARN" ]]; then
        aws elbv2 register-targets --target-group-arn "$AUTH_TG_ARN" --targets Id="$SIGNUP_LAMBDA_ARN" --region $REGION
        aws lambda add-permission --function-name "$SIGNUP_LAMBDA_ARN" --statement-id "alb-auth-$(date +%s)" --action lambda:InvokeFunction --principal elasticloadbalancing.amazonaws.com --source-arn "$AUTH_TG_ARN" --region $REGION 2>/dev/null || true
        echo -e "${GREEN}✅ Registered auth function${NC}"
    fi
    
    if [[ -n "$WAITLIST_LAMBDA_ARN" && "$WAITLIST_LAMBDA_ARN" != "None" && -n "$WAITLIST_TG_ARN" ]]; then
        aws elbv2 register-targets --target-group-arn "$WAITLIST_TG_ARN" --targets Id="$WAITLIST_LAMBDA_ARN" --region $REGION
        aws lambda add-permission --function-name "$WAITLIST_LAMBDA_ARN" --statement-id "alb-waitlist-$(date +%s)" --action lambda:InvokeFunction --principal elasticloadbalancing.amazonaws.com --source-arn "$WAITLIST_TG_ARN" --region $REGION 2>/dev/null || true
        echo -e "${GREEN}✅ Registered waitlist function${NC}"
    fi
    
    if [[ -n "$ANALYTICS_LAMBDA_ARN" && "$ANALYTICS_LAMBDA_ARN" != "None" && -n "$ANALYTICS_TG_ARN" ]]; then
        aws elbv2 register-targets --target-group-arn "$ANALYTICS_TG_ARN" --targets Id="$ANALYTICS_LAMBDA_ARN" --region $REGION
        aws lambda add-permission --function-name "$ANALYTICS_LAMBDA_ARN" --statement-id "alb-analytics-$(date +%s)" --action lambda:InvokeFunction --principal elasticloadbalancing.amazonaws.com --source-arn "$ANALYTICS_TG_ARN" --region $REGION 2>/dev/null || true
        echo -e "${GREEN}✅ Registered analytics function${NC}"
    fi
}

# Function to get existing listener rules
get_existing_rules() {
    echo -e "${BLUE}🔍 Checking existing listener rules...${NC}"
    
    aws elbv2 describe-rules --listener-arn "$LISTENER_ARN" --query "Rules[?Priority!='default'].[Priority,Conditions[0].Values[0]]" --output table --region $REGION
    echo ""
}

# Function to create listener rules
create_listener_rules() {
    echo -e "${BLUE}📋 Creating ALB listener rules...${NC}"
    
    # Get next available priority
    HIGHEST_PRIORITY=$(aws elbv2 describe-rules --listener-arn "$LISTENER_ARN" --query "Rules[?Priority!='default'].Priority" --output text --region $REGION | sort -n | tail -1)
    NEXT_PRIORITY=$((HIGHEST_PRIORITY + 100))
    
    echo "Starting rule priority: $NEXT_PRIORITY"
    
    # Rule 1: /api/health* -> Health Lambda
    if [[ -n "$HEALTH_TG_ARN" && "$HEALTH_TG_ARN" != "None" ]]; then
        aws elbv2 create-rule \
            --listener-arn "$LISTENER_ARN" \
            --priority $NEXT_PRIORITY \
            --conditions Field=path-pattern,Values="/api/health*" \
            --actions Type=forward,TargetGroupArn="$HEALTH_TG_ARN" \
            --region $REGION
        echo -e "${GREEN}✅ Created rule: /api/health* -> Health Lambda (Priority: $NEXT_PRIORITY)${NC}"
        NEXT_PRIORITY=$((NEXT_PRIORITY + 1))
    fi
    
    # Rule 2: /api/auth/* -> Auth Lambda
    if [[ -n "$AUTH_TG_ARN" && "$AUTH_TG_ARN" != "None" ]]; then
        aws elbv2 create-rule \
            --listener-arn "$LISTENER_ARN" \
            --priority $NEXT_PRIORITY \
            --conditions Field=path-pattern,Values="/api/auth/*" \
            --actions Type=forward,TargetGroupArn="$AUTH_TG_ARN" \
            --region $REGION
        echo -e "${GREEN}✅ Created rule: /api/auth/* -> Auth Lambda (Priority: $NEXT_PRIORITY)${NC}"
        NEXT_PRIORITY=$((NEXT_PRIORITY + 1))
    fi
    
    # Rule 3: /api/waitlist/* -> Waitlist Lambda
    if [[ -n "$WAITLIST_TG_ARN" && "$WAITLIST_TG_ARN" != "None" ]]; then
        aws elbv2 create-rule \
            --listener-arn "$LISTENER_ARN" \
            --priority $NEXT_PRIORITY \
            --conditions Field=path-pattern,Values="/api/waitlist/*" \
            --actions Type=forward,TargetGroupArn="$WAITLIST_TG_ARN" \
            --region $REGION
        echo -e "${GREEN}✅ Created rule: /api/waitlist/* -> Waitlist Lambda (Priority: $NEXT_PRIORITY)${NC}"
        NEXT_PRIORITY=$((NEXT_PRIORITY + 1))
    fi
    
    # Rule 4: /api/analytics/* -> Analytics Lambda
    if [[ -n "$ANALYTICS_TG_ARN" && "$ANALYTICS_TG_ARN" != "None" ]]; then
        aws elbv2 create-rule \
            --listener-arn "$LISTENER_ARN" \
            --priority $NEXT_PRIORITY \
            --conditions Field=path-pattern,Values="/api/analytics/*" \
            --actions Type=forward,TargetGroupArn="$ANALYTICS_TG_ARN" \
            --region $REGION
        echo -e "${GREEN}✅ Created rule: /api/analytics/* -> Analytics Lambda (Priority: $NEXT_PRIORITY)${NC}"
        NEXT_PRIORITY=$((NEXT_PRIORITY + 1))
    fi
    
    echo ""
    echo -e "${GREEN}✅ All listener rules created successfully!${NC}"
}

# Function to test the configuration
test_configuration() {
    echo -e "${BLUE}🧪 Testing ALB configuration...${NC}"
    
    # Get ALB DNS name
    ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns "$ALB_ARN" --query "LoadBalancers[0].DNSName" --output text --region $REGION)
    
    echo "ALB DNS: $ALB_DNS"
    echo ""
    echo "Test URLs (replace with your domain if using CloudFront):"
    echo "  Health: https://$ALB_DNS/api/health"
    echo "  Auth: https://$ALB_DNS/api/auth/signup (POST)"
    echo "  Waitlist: https://$ALB_DNS/api/waitlist/join (POST)"
    echo "  Analytics: https://$ALB_DNS/api/analytics/track (POST)"
    echo ""
    
    # Try to test health endpoint
    echo "Testing health endpoint..."
    if curl -f -s "https://$ALB_DNS/api/health" -m 10 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health endpoint is responding${NC}"
    else
        echo -e "${YELLOW}⚠️  Health endpoint test failed (may need time to propagate)${NC}"
    fi
}

# Main execution
main() {
    find_alb
    get_https_listener
    get_existing_rules
    find_lambda_target_groups
    create_lambda_target_groups
    register_lambda_functions
    create_listener_rules
    test_configuration
    
    echo ""
    echo -e "${GREEN}🎉 ALB Path-Based Routing Configuration Complete!${NC}"
    echo ""
    echo -e "${BLUE}📋 Configuration Summary:${NC}"
    echo "ALB ARN: $ALB_ARN"
    echo "Listener ARN: $LISTENER_ARN"
    echo ""
    echo -e "${BLUE}📝 What was configured:${NC}"
    echo "✅ Lambda target groups created/found"
    echo "✅ Lambda functions registered with target groups"
    echo "✅ ALB listener rules created for path-based routing"
    echo "✅ Lambda permissions configured for ALB invocation"
    echo ""
    echo -e "${YELLOW}⚠️  Important Notes:${NC}"
    echo "1. Rules may take 1-2 minutes to become active"
    echo "2. Test endpoints after propagation"
    echo "3. Your existing ECS service should still work on other paths"
    echo "4. Consider adding a rule for /app/* -> ECS target group if needed"
}

main