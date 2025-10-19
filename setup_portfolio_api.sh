#!/bin/bash
set -e

API_ID="uniy9g4q4m"
ROOT_ID="koqbxa4v1j"
REGION="us-east-1"
ACCOUNT_ID="453636587892"

echo "Creating /portfolio resource..."
PORTFOLIO_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part portfolio \
  --region $REGION \
  --query 'id' \
  --output text)
echo "Created /portfolio: $PORTFOLIO_ID"

echo "Creating /portfolio/save resource..."
SAVE_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $PORTFOLIO_ID \
  --path-part save \
  --region $REGION \
  --query 'id' \
  --output text)
echo "Created /portfolio/save: $SAVE_ID"

echo "Creating /portfolio/latest resource..."
LATEST_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $PORTFOLIO_ID \
  --path-part latest \
  --region $REGION \
  --query 'id' \
  --output text)
echo "Created /portfolio/latest: $LATEST_ID"

echo "Creating /portfolio/{portfolio_id} resource..."
PORTFOLIO_PARAM_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $PORTFOLIO_ID \
  --path-part '{portfolio_id}' \
  --region $REGION \
  --query 'id' \
  --output text)
echo "Created /portfolio/{portfolio_id}: $PORTFOLIO_PARAM_ID"

# Create POST method for /portfolio/save
echo "Creating POST method for /portfolio/save..."
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $SAVE_ID \
  --http-method POST \
  --authorization-type NONE \
  --region $REGION

# Create Lambda integration for save
echo "Creating Lambda integration for save..."
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $SAVE_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:investforge-save-portfolio/invocations" \
  --region $REGION

# Create GET method for /portfolio/latest
echo "Creating GET method for /portfolio/latest..."
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $LATEST_ID \
  --http-method GET \
  --authorization-type NONE \
  --region $REGION

# Create Lambda integration for latest
echo "Creating Lambda integration for latest..."
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $LATEST_ID \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:investforge-get-latest-portfolio/invocations" \
  --region $REGION

# Create GET method for /portfolio/{portfolio_id}
echo "Creating GET method for /portfolio/{portfolio_id}..."
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $PORTFOLIO_PARAM_ID \
  --http-method GET \
  --authorization-type NONE \
  --region $REGION

# Create Lambda integration for get portfolio
echo "Creating Lambda integration for get portfolio..."
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $PORTFOLIO_PARAM_ID \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:investforge-get-portfolio/invocations" \
  --region $REGION

# Add Lambda permissions
echo "Adding Lambda permissions..."
aws lambda add-permission \
  --function-name investforge-save-portfolio \
  --statement-id apigateway-portfolio-save \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/*" \
  --region $REGION 2>/dev/null || echo "Permission already exists for save"

aws lambda add-permission \
  --function-name investforge-get-portfolio \
  --statement-id apigateway-portfolio-get \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/*" \
  --region $REGION 2>/dev/null || echo "Permission already exists for get"

aws lambda add-permission \
  --function-name investforge-get-latest-portfolio \
  --statement-id apigateway-portfolio-latest \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/*" \
  --region $REGION 2>/dev/null || echo "Permission already exists for latest"

# Deploy API
echo "Deploying API to prod stage..."
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION

echo "✅ API Gateway configuration complete!"
echo "Endpoints available at:"
echo "  POST https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/portfolio/save"
echo "  GET  https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/portfolio/latest"
echo "  GET  https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/portfolio/{portfolio_id}"
