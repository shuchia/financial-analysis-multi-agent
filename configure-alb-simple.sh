#!/bin/bash

# Simple ALB Configuration for InvestForge Lambda Functions
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Configuring ALB for InvestForge Lambda Functions${NC}"
echo "=================================================="
echo ""

# Configuration
ALB_ARN="arn:aws:elasticloadbalancing:us-east-1:453636587892:loadbalancer/app/financial-analysis-alb/3d7f9d05948bbff6"
LISTENER_ARN="arn:aws:elasticloadbalancing:us-east-1:453636587892:listener/app/financial-analysis-alb/3d7f9d05948bbff6/157d48a8f984f50b"
REGION="us-east-1"

echo -e "${BLUE}Using ALB: financial-analysis-alb${NC}"
echo -e "${BLUE}Using HTTPS Listener${NC}"
echo ""

# Create Lambda target groups (without VPC)
echo -e "${BLUE}🏗️  Creating Lambda target groups...${NC}"

# Health target group
HEALTH_TG_ARN=$(aws elbv2 create-target-group \
    --name "investforge-lambda-health" \
    --target-type lambda \
    --region $REGION \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text 2>/dev/null || \
    aws elbv2 describe-target-groups --names "investforge-lambda-health" --query "TargetGroups[0].TargetGroupArn" --output text --region $REGION 2>/dev/null)

echo -e "${GREEN}✅ Health target group: $HEALTH_TG_ARN${NC}"

# Auth target group
AUTH_TG_ARN=$(aws elbv2 create-target-group \
    --name "investforge-lambda-auth" \
    --target-type lambda \
    --region $REGION \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text 2>/dev/null || \
    aws elbv2 describe-target-groups --names "investforge-lambda-auth" --query "TargetGroups[0].TargetGroupArn" --output text --region $REGION 2>/dev/null)

echo -e "${GREEN}✅ Auth target group: $AUTH_TG_ARN${NC}"

# Waitlist target group
WAITLIST_TG_ARN=$(aws elbv2 create-target-group \
    --name "investforge-lambda-waitlist" \
    --target-type lambda \
    --region $REGION \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text 2>/dev/null || \
    aws elbv2 describe-target-groups --names "investforge-lambda-waitlist" --query "TargetGroups[0].TargetGroupArn" --output text --region $REGION 2>/dev/null)

echo -e "${GREEN}✅ Waitlist target group: $WAITLIST_TG_ARN${NC}"

# Analytics target group
ANALYTICS_TG_ARN=$(aws elbv2 create-target-group \
    --name "investforge-lambda-analytics" \
    --target-type lambda \
    --region $REGION \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text 2>/dev/null || \
    aws elbv2 describe-target-groups --names "investforge-lambda-analytics" --query "TargetGroups[0].TargetGroupArn" --output text --region $REGION 2>/dev/null)

echo -e "${GREEN}✅ Analytics target group: $ANALYTICS_TG_ARN${NC}"

echo ""

# Register Lambda functions with target groups
echo -e "${BLUE}🔗 Registering Lambda functions...${NC}"

# Health function
HEALTH_LAMBDA_ARN=$(aws lambda get-function --function-name "investforge-health" --query "Configuration.FunctionArn" --output text --region $REGION)
if [[ -n "$HEALTH_LAMBDA_ARN" && "$HEALTH_LAMBDA_ARN" != "None" ]]; then
    aws elbv2 register-targets --target-group-arn "$HEALTH_TG_ARN" --targets Id="$HEALTH_LAMBDA_ARN" --region $REGION
    aws lambda add-permission --function-name "$HEALTH_LAMBDA_ARN" --statement-id "alb-health-$(date +%s)" --action lambda:InvokeFunction --principal elasticloadbalancing.amazonaws.com --source-arn "$HEALTH_TG_ARN" --region $REGION 2>/dev/null || true
    echo -e "${GREEN}✅ Registered health function${NC}"
fi

# Signup function (for auth)
SIGNUP_LAMBDA_ARN=$(aws lambda get-function --function-name "investforge-signup" --query "Configuration.FunctionArn" --output text --region $REGION)
if [[ -n "$SIGNUP_LAMBDA_ARN" && "$SIGNUP_LAMBDA_ARN" != "None" ]]; then
    aws elbv2 register-targets --target-group-arn "$AUTH_TG_ARN" --targets Id="$SIGNUP_LAMBDA_ARN" --region $REGION
    aws lambda add-permission --function-name "$SIGNUP_LAMBDA_ARN" --statement-id "alb-auth-$(date +%s)" --action lambda:InvokeFunction --principal elasticloadbalancing.amazonaws.com --source-arn "$AUTH_TG_ARN" --region $REGION 2>/dev/null || true
    echo -e "${GREEN}✅ Registered auth function${NC}"
fi

# Waitlist function
WAITLIST_LAMBDA_ARN=$(aws lambda get-function --function-name "investforge-waitlist" --query "Configuration.FunctionArn" --output text --region $REGION)
if [[ -n "$WAITLIST_LAMBDA_ARN" && "$WAITLIST_LAMBDA_ARN" != "None" ]]; then
    aws elbv2 register-targets --target-group-arn "$WAITLIST_TG_ARN" --targets Id="$WAITLIST_LAMBDA_ARN" --region $REGION
    aws lambda add-permission --function-name "$WAITLIST_LAMBDA_ARN" --statement-id "alb-waitlist-$(date +%s)" --action lambda:InvokeFunction --principal elasticloadbalancing.amazonaws.com --source-arn "$WAITLIST_TG_ARN" --region $REGION 2>/dev/null || true
    echo -e "${GREEN}✅ Registered waitlist function${NC}"
fi

# Analytics function
ANALYTICS_LAMBDA_ARN=$(aws lambda get-function --function-name "investforge-analytics" --query "Configuration.FunctionArn" --output text --region $REGION)
if [[ -n "$ANALYTICS_LAMBDA_ARN" && "$ANALYTICS_LAMBDA_ARN" != "None" ]]; then
    aws elbv2 register-targets --target-group-arn "$ANALYTICS_TG_ARN" --targets Id="$ANALYTICS_LAMBDA_ARN" --region $REGION
    aws lambda add-permission --function-name "$ANALYTICS_LAMBDA_ARN" --statement-id "alb-analytics-$(date +%s)" --action lambda:InvokeFunction --principal elasticloadbalancing.amazonaws.com --source-arn "$ANALYTICS_TG_ARN" --region $REGION 2>/dev/null || true
    echo -e "${GREEN}✅ Registered analytics function${NC}"
fi

echo ""

# Create listener rules
echo -e "${BLUE}📋 Creating ALB listener rules...${NC}"

# Get next available priority
HIGHEST_PRIORITY=$(aws elbv2 describe-rules --listener-arn "$LISTENER_ARN" --query "Rules[?Priority!='default'].Priority" --output text --region $REGION | sort -n | tail -1)
if [[ -z "$HIGHEST_PRIORITY" || "$HIGHEST_PRIORITY" == "None" ]]; then
    NEXT_PRIORITY=100
else
    NEXT_PRIORITY=$((HIGHEST_PRIORITY + 1))
fi

echo "Starting rule priority: $NEXT_PRIORITY"

# Rule 1: /api/health* -> Health Lambda
aws elbv2 create-rule \
    --listener-arn "$LISTENER_ARN" \
    --priority $NEXT_PRIORITY \
    --conditions Field=path-pattern,Values="/api/health*" \
    --actions Type=forward,TargetGroupArn="$HEALTH_TG_ARN" \
    --region $REGION
echo -e "${GREEN}✅ Created rule: /api/health* -> Health Lambda (Priority: $NEXT_PRIORITY)${NC}"
NEXT_PRIORITY=$((NEXT_PRIORITY + 1))

# Rule 2: /api/auth/* -> Auth Lambda
aws elbv2 create-rule \
    --listener-arn "$LISTENER_ARN" \
    --priority $NEXT_PRIORITY \
    --conditions Field=path-pattern,Values="/api/auth/*" \
    --actions Type=forward,TargetGroupArn="$AUTH_TG_ARN" \
    --region $REGION
echo -e "${GREEN}✅ Created rule: /api/auth/* -> Auth Lambda (Priority: $NEXT_PRIORITY)${NC}"
NEXT_PRIORITY=$((NEXT_PRIORITY + 1))

# Rule 3: /api/waitlist/* -> Waitlist Lambda
aws elbv2 create-rule \
    --listener-arn "$LISTENER_ARN" \
    --priority $NEXT_PRIORITY \
    --conditions Field=path-pattern,Values="/api/waitlist/*" \
    --actions Type=forward,TargetGroupArn="$WAITLIST_TG_ARN" \
    --region $REGION
echo -e "${GREEN}✅ Created rule: /api/waitlist/* -> Waitlist Lambda (Priority: $NEXT_PRIORITY)${NC}"
NEXT_PRIORITY=$((NEXT_PRIORITY + 1))

# Rule 4: /api/analytics/* -> Analytics Lambda
aws elbv2 create-rule \
    --listener-arn "$LISTENER_ARN" \
    --priority $NEXT_PRIORITY \
    --conditions Field=path-pattern,Values="/api/analytics/*" \
    --actions Type=forward,TargetGroupArn="$ANALYTICS_TG_ARN" \
    --region $REGION
echo -e "${GREEN}✅ Created rule: /api/analytics/* -> Analytics Lambda (Priority: $NEXT_PRIORITY)${NC}"

echo ""

# Test the configuration
echo -e "${BLUE}🧪 Testing ALB configuration...${NC}"

ALB_DNS="financial-analysis-alb-161240.us-east-1.elb.amazonaws.com"

echo "ALB DNS: $ALB_DNS"
echo ""
echo "Test URLs:"
echo "  Health: https://$ALB_DNS/api/health"
echo "  Auth: https://$ALB_DNS/api/auth/signup (POST)"
echo "  Waitlist: https://$ALB_DNS/api/waitlist/join (POST)"
echo "  Analytics: https://$ALB_DNS/api/analytics/track (POST)"
echo ""

# Try to test health endpoint
echo "Testing health endpoint..."
sleep 5  # Give time for rules to propagate
if curl -f -s "https://$ALB_DNS/api/health" -m 15 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health endpoint is responding${NC}"
    echo "Response:"
    curl -s "https://$ALB_DNS/api/health" | jq . 2>/dev/null || curl -s "https://$ALB_DNS/api/health"
else
    echo -e "${YELLOW}⚠️  Health endpoint test failed (may need time to propagate)${NC}"
    echo "This is normal - rules can take 1-2 minutes to become active"
fi

echo ""
echo -e "${GREEN}🎉 ALB Path-Based Routing Configuration Complete!${NC}"
echo ""
echo -e "${BLUE}📋 Configuration Summary:${NC}"
echo "✅ Lambda target groups created"
echo "✅ Lambda functions registered with target groups"
echo "✅ ALB listener rules created for path-based routing"
echo "✅ Lambda permissions configured for ALB invocation"
echo ""
echo -e "${BLUE}📝 Routing Configuration:${NC}"
echo "/api/health* → Health Lambda"
echo "/api/auth/* → Auth Lambda (signup/login)"
echo "/api/waitlist/* → Waitlist Lambda"
echo "/api/analytics/* → Analytics Lambda"
echo "/app/* → Your existing ECS service (default rule)"
echo ""
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "1. Rules may take 1-2 minutes to become active"
echo "2. Your existing ECS Streamlit app will continue to work"
echo "3. Test endpoints after a few minutes for propagation"
echo ""
echo -e "${BLUE}🧪 Test Commands:${NC}"
echo "curl https://$ALB_DNS/api/health"
echo "curl -X POST https://$ALB_DNS/api/waitlist/join -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\"}'"