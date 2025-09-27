# InvestForge Authentication System Deployment Guide

## Overview

This document describes the enhanced authentication system implementation for InvestForge, including deployment instructions, configuration requirements, and testing procedures.

## Features Implemented

### ✅ Core Authentication
- User signup with email/password
- User login with security features
- JWT-based authentication (access & refresh tokens)
- Password reset functionality
- Email verification

### ✅ Security Features
- Rate limiting with Redis (token bucket algorithm)
- Account lockout after failed attempts
- Password complexity validation
- Compromised password checking (Have I Been Pwned)
- IP-based suspicious activity detection

### ✅ OAuth Integration
- Google OAuth login
- Account linking/unlinking
- Seamless user experience

### ✅ Usage Tracking
- Feature usage limits by plan
- Analytics event tracking
- Usage increment/check handlers

### ✅ Testing
- Comprehensive unit tests
- Integration tests covering full user flows
- Mock-based testing approach

## Architecture

```
Frontend (Streamlit) ←→ API Gateway ←→ Lambda Functions ←→ DynamoDB
                                    ↓
                                  Redis (Rate Limiting & Security)
                                    ↓
                                  SES (Email)
```

## Database Schema

### Users Table (`investforge-users-simple`)
```json
{
  "user_id": "string (PK)",
  "email": "string (GSI)",
  "password_hash": "string",
  "first_name": "string",
  "last_name": "string",
  "plan": "string",
  "status": "string",
  "email_verified": "boolean",
  "google_id": "string",
  "profile_picture": "string",
  "created_at": "string",
  "updated_at": "string",
  "last_login": "string",
  "last_login_ip": "string"
}
```

### Password Resets Table (`investforge-api-dev-password-resets`)
```json
{
  "reset_token": "string (PK)",
  "user_id": "string",
  "expires_at": "string",
  "created_at": "string",
  "used": "boolean",
  "used_at": "string"
}
```

### Usage Table (`investforge-usage`)
```json
{
  "user_id": "string (PK)",
  "date_feature": "string (SK)", // Format: "YYYY-MM-DD#feature_name"
  "count": "number"
}
```

### Analytics Table (`investforge-analytics`)
```json
{
  "event_id": "string (PK)",
  "event_type": "string",
  "timestamp": "string",
  "user_id": "string",
  "event_data": "object",
  "source": "string"
}
```

## Environment Variables

### Required Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production

# Database Tables
DYNAMODB_TABLE_USERS=investforge-users-simple
DYNAMODB_TABLE_USAGE=investforge-usage
DYNAMODB_TABLE_ANALYTICS=investforge-analytics
DYNAMODB_TABLE_WAITLIST=investforge-api-dev-waitlist
DYNAMODB_TABLE_PASSWORD_RESETS=investforge-api-dev-password-resets

# Redis Configuration (for rate limiting and security)
REDIS_URL=redis://your-redis-cluster:6379

# Google OAuth
GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com

# Email Configuration
SENDER_EMAIL=noreply@investforge.io
APP_NAME=InvestForge
APP_URL=https://investforge.io

# AWS Configuration
AWS_REGION=us-east-1
```

### Optional Environment Variables

```bash
# Development/Testing
STAGE=dev
SERVICE_NAME=investforge-api

# Email Templates
SUPPORT_EMAIL=support@investforge.io
```

## Lambda Function Configuration

### API Gateway Routes

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/auth/signup` | `auth.signup` | User registration |
| POST | `/auth/login` | `auth.login` | User login |
| POST | `/auth/refresh` | `auth.refresh_token` | Token refresh |
| POST | `/auth/google` | `auth_google.handler` | Google OAuth |
| POST | `/auth/reset-request` | `auth_reset.request_password_reset` | Request password reset |
| POST | `/auth/reset-password` | `auth_reset.reset_password` | Reset password |
| POST | `/auth/verify-email` | `auth_reset.verify_email_token` | Verify email |
| POST | `/auth/resend-verification` | `auth_reset.resend_verification_email` | Resend verification |
| GET | `/auth/verify` | `auth_reset.verify_email_token` | Email verification (GET) |

### Lambda Function Settings

```yaml
Runtime: Python 3.11
Memory: 512 MB
Timeout: 30 seconds
Environment Variables: [See above section]
```

### IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/investforge-*",
        "arn:aws:dynamodb:*:*:table/investforge-*/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Redis Configuration

### ElastiCache Redis Cluster

```yaml
Node Type: cache.t3.micro (for development)
Redis Version: 7.x
Parameter Group: default.redis7.x
Subnet Group: private-subnets
Security Groups: redis-sg (port 6379)
```

### Security Group Rules

```yaml
Inbound Rules:
  - Type: Custom TCP
    Port: 6379
    Source: Lambda Security Group
```

## Deployment Steps

### 1. Infrastructure Setup

```bash
# Create DynamoDB tables
aws dynamodb create-table \
  --table-name investforge-api-dev-password-resets \
  --attribute-definitions AttributeName=reset_token,AttributeType=S \
  --key-schema AttributeName=reset_token,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Set up Redis cluster (via ElastiCache console or CloudFormation)

# Configure SES (verify domain and email addresses)
aws ses verify-domain-identity --domain investforge.io
```

### 2. Lambda Deployment

```bash
# Build deployment package
cd api/
zip -r ../auth-deployment.zip . -x "tests/*" "*.pyc" "__pycache__/*"

# Deploy to Lambda
aws lambda update-function-code \
  --function-name investforge-auth \
  --zip-file fileb://../auth-deployment.zip

# Update environment variables
aws lambda update-function-configuration \
  --function-name investforge-auth \
  --environment Variables="{JWT_SECRET_KEY=your-secret,REDIS_URL=redis://your-cluster:6379,...}"
```

### 3. API Gateway Configuration

```bash
# Deploy API Gateway stage
aws apigateway create-deployment \
  --rest-api-id your-api-id \
  --stage-name prod
```

### 4. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Add authorized origins: `https://investforge.io`
4. Add authorized redirect URIs: `https://investforge.io/auth/callback`
5. Set `GOOGLE_CLIENT_ID` environment variable

## Testing

### Unit Tests

```bash
# Run authentication tests
cd tests/
python -m unittest test_auth -v

# Run integration tests
python -m unittest test_integration_auth -v
```

### Manual Testing

1. **User Signup**
```bash
curl -X POST https://api.investforge.io/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "first_name": "Test",
    "last_name": "User",
    "plan": "free"
  }'
```

2. **User Login**
```bash
curl -X POST https://api.investforge.io/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

3. **Password Reset**
```bash
# Request reset
curl -X POST https://api.investforge.io/auth/reset-request \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Reset password
curl -X POST https://api.investforge.io/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "reset_token": "token-from-email",
    "new_password": "NewPass123!"
  }'
```

### Rate Limiting Test

```bash
# Test rate limiting (should get 429 after 5 requests)
for i in {1..10}; do
  curl -X POST https://api.investforge.io/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "wrong"}'
  echo ""
done
```

## Monitoring

### CloudWatch Metrics

Monitor these key metrics:
- Lambda invocation count and errors
- DynamoDB read/write capacity
- Redis cache hit ratio
- SES bounce/complaint rates

### Log Analysis

```bash
# View Lambda logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/investforge-auth \
  --start-time $(date -d '1 hour ago' +%s)000

# Check for authentication failures
aws logs filter-log-events \
  --log-group-name /aws/lambda/investforge-auth \
  --filter-pattern "Failed login attempt"
```

## Security Considerations

### Rate Limiting
- Login attempts: 5 per 5 minutes per IP
- Signup attempts: 10 per hour per IP  
- Password resets: 3 per 5 minutes per IP

### Account Security
- Account lockout after 5 failed attempts
- 15-minute lockout duration
- Suspicious activity detection (multiple IPs)

### Password Security
- Minimum 8 characters
- Must include uppercase, lowercase, number, special character
- Checked against compromised password database
- Bcrypt hashing with salt

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**
```
Check Redis cluster status and security groups
Verify REDIS_URL environment variable
```

2. **Email Delivery Issues**
```
Verify SES configuration and domain verification
Check bounce/complaint rates
Ensure proper IAM permissions
```

3. **Token Verification Failures**
```
Check JWT_SECRET_KEY consistency across deployments
Verify token expiration times
```

4. **Database Connection Issues**
```
Verify DynamoDB table names and regions
Check IAM permissions for DynamoDB access
```

### Debug Mode

Set these environment variables for debugging:
```bash
LOG_LEVEL=DEBUG
PYTHONPATH=/var/runtime
```

## Performance Optimization

### Database
- Use DynamoDB on-demand billing for variable loads
- Consider provisioned capacity for predictable traffic
- Implement database connection pooling

### Caching
- Redis for rate limiting and session data
- Consider CloudFront for static assets
- Implement proper cache invalidation

### Lambda
- Use appropriate memory allocation (512MB recommended)
- Implement Lambda warming for consistent performance
- Consider using Lambda layers for common dependencies

## Security Hardening

### Production Checklist

- [ ] Change all default secrets and keys
- [ ] Enable AWS CloudTrail for audit logging
- [ ] Set up AWS Config for compliance monitoring
- [ ] Implement AWS WAF for additional protection
- [ ] Enable VPC endpoints for DynamoDB access
- [ ] Use AWS Secrets Manager for sensitive credentials
- [ ] Set up backup strategies for DynamoDB
- [ ] Configure proper CORS policies
- [ ] Enable API Gateway throttling
- [ ] Set up monitoring and alerting

## Backup and Recovery

### Database Backups
```bash
# Enable point-in-time recovery
aws dynamodb update-continuous-backups \
  --table-name investforge-users-simple \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### Redis Backups
- Configure automatic snapshots
- Set appropriate retention periods
- Test recovery procedures

## Cost Optimization

### Estimated Monthly Costs (1000 active users)

- Lambda: ~$10
- DynamoDB: ~$25  
- Redis: ~$15
- SES: ~$1
- **Total: ~$51/month**

### Cost Reduction Strategies
- Use DynamoDB on-demand for variable workloads
- Implement proper caching to reduce database calls
- Monitor and optimize Lambda memory allocation
- Use reserved capacity for predictable usage patterns

---

## Next Steps

After successful deployment:

1. Implement admin dashboard (pending)
2. Add comprehensive audit logging (pending)  
3. Implement GDPR compliance features (pending)
4. Set up monitoring and alerting
5. Conduct security audit
6. Performance testing and optimization

## Support

For deployment issues or questions:
- Review CloudWatch logs
- Check the troubleshooting section
- Contact the development team
- Review AWS documentation for specific services