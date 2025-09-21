# InvestForge.io Production Deployment Guide

🚀 **Live Production Site**: [https://investforge.io](https://investforge.io)

This guide documents the enterprise-grade AWS deployment architecture for the Financial Analysis Multi-Agent application, now live as **InvestForge.io**.

## Production Architecture Overview

### Current Live Infrastructure

**InvestForge.io** runs on a secure, scalable AWS architecture:

```
Internet Users
     ↓
Route 53 DNS (investforge.io)
     ↓
Application Load Balancer (ALB)
  - SSL/TLS Termination (AWS ACM)
  - WAF Protection
  - Multi-AZ Distribution
     ↓
ECS Fargate Cluster
  - Auto-scaling (1-10 containers)
  - Private Security Groups
  - CloudWatch Monitoring
     ↓
Supporting Services:
- ECR (Container Registry)
- Secrets Manager (Configuration)
- CodeBuild (CI/CD Pipeline)
- CloudWatch (Logs & Metrics)
```

### Infrastructure Components

#### Domain & DNS
- **Domain**: `investforge.io` (registered via Route 53)
- **DNS**: Route 53 hosted zone with A records pointing to ALB
- **SSL Certificate**: AWS Certificate Manager (free, auto-renewing)

#### Load Balancing & Security
- **ALB**: `financial-analysis-alb-161240.us-east-1.elb.amazonaws.com`
- **SSL Policy**: TLS 1.2+ with HTTP/2 support
- **WAF**: Web Application Firewall with managed rule sets
- **Security Groups**: Least-privilege network access

#### Container Platform
- **Compute**: ECS Fargate (1024 CPU, 2048 MB RAM)
- **Registry**: Amazon ECR (`financial-analysis-app` repository)
- **Scaling**: Automatic based on CPU/memory utilization
- **Health Checks**: Application-level monitoring

#### CI/CD & Deployment
- **Build**: AWS CodeBuild project (`financial-analysis-build`)
- **Source**: GitHub integration with webhook triggers
- **Pipeline**: Automated Docker builds and ECR pushes

## Prerequisites for Replication

1. **AWS CLI** installed and configured
2. **AWS Account** with administrative permissions
3. **Domain Name** (or use Route 53 registration)
4. **Docker** installed (for local testing)

## Required AWS Permissions

For replicating this deployment, your AWS user/role needs:

### Core Services
- `route53:*` (DNS management)
- `acm:*` (SSL certificates)
- `elasticloadbalancing:*` (ALB)
- `ecs:*` (Container orchestration)
- `ecr:*` (Container registry)

### Security & Monitoring
- `wafv2:*` (Web Application Firewall)
- `iam:*` (Role management)
- `secretsmanager:*` (Configuration secrets)
- `logs:*` (CloudWatch logs)

### CI/CD
- `codebuild:*` (Build automation)
- `events:*` (GitHub webhooks)

## Production Deployment Architecture

### Current Live Setup (InvestForge.io)

The following components are currently running in production:

#### 1. Domain & SSL Setup
```bash
# Domain: investforge.io (Route 53 registered)
# Hosted Zone: Z08211553JYQ7LH5RQ3VV
# SSL Certificate: ACM auto-renewing
```

#### 2. Load Balancer Configuration
```bash
# ALB: financial-analysis-alb
# Target Group: financial-analysis-tg (port 8080)
# Listeners:
#   - HTTP (80) → HTTPS (301 redirect)
#   - HTTPS (443) → ECS Fargate containers
```

#### 3. ECS Fargate Deployment
```bash
# Cluster: financial-analysis-cluster
# Service: Auto-scaling (min: 1, max: 10)
# Task Definition: financial-analysis-task (1024 CPU, 2048 MB)
# Security Group: ALB access only
```

### Environment & Security Configuration

The production deployment uses AWS IAM roles for secure service access:

**IAM Roles:**
- `FinancialAnalysisECSExecutionRole`: Container execution permissions
- `FinancialAnalysisECSTaskRole`: AWS Bedrock access for AI functionality
- `FinancialAnalysisCodeBuildRole`: CI/CD pipeline permissions

**Secrets Management:**
- AWS Secrets Manager stores sensitive configuration
- No hardcoded credentials in containers
- Environment variables injected securely at runtime

### Cost Breakdown (Monthly)

| Service | Cost | Description |
|---------|------|-------------|
| ECS Fargate | ~$36 | 1024 CPU, 2048 MB RAM |
| Application Load Balancer | ~$25 | Multi-AZ, health checks |
| Route 53 | ~$0.50 | DNS queries |
| ACM SSL Certificate | Free | Auto-renewing |
| WAF | ~$4 | Security rules and requests |
| ECR | ~$0.10 | Container image storage |
| CloudWatch | ~$1 | Logs and metrics |
| **Total Base** | **~$67/month** | **Fixed infrastructure** |
| **AWS Bedrock** | **$5-200/month** | **Usage-based (AI analysis)** |
| **Domain Registration** | **$71/year** | **InvestForge.io domain** |

### CI/CD Pipeline

The production deployment includes automated CI/CD:

#### CodeBuild Configuration
```bash
# Project: financial-analysis-build
# Source: GitHub webhook (main branch)
# Build: Docker image creation
# Deploy: Push to ECR → ECS auto-deploy
```

#### Deployment Process
1. **Code Push**: Developer pushes to GitHub main branch
2. **Build Trigger**: CodeBuild automatically starts
3. **Container Build**: Creates optimized Docker image
4. **ECR Push**: Uploads image to Amazon ECR
5. **ECS Deploy**: ECS Fargate pulls new image and deploys
6. **Health Check**: ALB verifies application health
7. **Live Update**: Traffic routes to new containers

### Monitoring & Alerting

#### CloudWatch Integration
- **Application Logs**: Centralized logging with retention
- **Performance Metrics**: CPU, memory, response times
- **Error Tracking**: Exception monitoring and alerting
- **Custom Dashboards**: Real-time infrastructure overview

#### Health Monitoring
- **ALB Health Checks**: Automatic unhealthy instance replacement
- **ECS Service Health**: Container restart on failures
- **SSL Certificate**: Automatic renewal notifications

## Local Testing

Before deploying, test the container locally:

```bash
# Build the Docker image
docker build -t financial-analysis-app .

# Run locally with environment variables
docker run -p 8080:8080 \\
  -e AWS_ACCESS_KEY_ID=your_key \\
  -e AWS_SECRET_ACCESS_KEY=your_secret \\
  -e AWS_DEFAULT_REGION=us-east-1 \\
  financial-analysis-app
```

Visit `http://localhost:8080` to test the application.

## Configuration Files

### Current Production Files
- `Dockerfile`: Container configuration optimized for ECS Fargate
- `buildspec.yml`: CodeBuild configuration for CI/CD pipeline
- `task-definition.json`: ECS Fargate task configuration (not in repo for security)
- `.env.template`: Template for environment variables
- `.dockerignore`: Files to exclude from Docker build

### Removed Files (Legacy App Runner)
- `apprunner.yaml`: Removed (migrated to ECS Fargate)
- `.streamlit/config.toml`: Removed (App Runner specific)

## Troubleshooting

### Common Issues (Production)

1. **SSL Certificate Issues**
   - Check ACM certificate status in AWS Console
   - Verify domain DNS is pointing to correct ALB
   - SSL validation requires proper DNS propagation

2. **Container Health Issues**
   - Check ECS service events in AWS Console
   - Review CloudWatch logs: `/ecs/financial-analysis`
   - Verify container has proper IAM permissions for Bedrock

3. **Load Balancer Issues**
   - Check ALB target group health in AWS Console
   - Verify security group allows traffic from ALB to containers
   - Ensure containers are running on port 8080

4. **CI/CD Pipeline Issues**
   - Check CodeBuild project logs for build failures
   - Verify GitHub webhook is properly configured
   - Ensure ECR repository permissions allow pushes

### Monitoring & Logs

#### CloudWatch Logs
```bash
# View application logs
aws logs describe-log-groups --log-group-name-prefix "/ecs/financial-analysis"

# Stream recent logs
aws logs tail /ecs/financial-analysis --since 1h --follow
```

#### ECS Service Status
```bash
# Check ECS service health
aws ecs describe-services --cluster financial-analysis-cluster --services financial-analysis-service

# View running tasks
aws ecs list-tasks --cluster financial-analysis-cluster
```

#### Load Balancer Health
```bash
# Check target group health
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:us-east-1:...:targetgroup/financial-analysis-tg/...
```

## Security Architecture

### Multi-Layer Security
1. **Network Security**
   - Private security groups with least-privilege access
   - ALB isolates containers from direct internet access
   - WAF protects against common web attacks

2. **Authentication & Authorization**
   - IAM roles for all AWS service access
   - No hardcoded credentials in containers or code
   - AWS Secrets Manager for sensitive configuration

3. **Encryption**
   - HTTPS/TLS encryption for all external traffic
   - AWS ACM manages SSL certificates with auto-renewal
   - Container-to-container communication over private networks

4. **Monitoring & Compliance**
   - CloudTrail logging for all API calls
   - CloudWatch monitoring for security events
   - Resource tagging for compliance and billing separation

### Resource Tagging Strategy
All production resources are tagged for:
- **Project**: FinancialAnalysis
- **Environment**: Production
- **Owner**: FinancialTeam
- **CostCenter**: FinancialAnalysisApp

## Cost Optimization Strategies

### Current Configuration
- **ECS Fargate**: 1024 CPU, 2048 MB RAM (optimal for AI workloads)
- **Auto-scaling**: Scales based on CPU/memory utilization
- **Spot Instances**: Could reduce costs by ~70% (not recommended for production)

### Optimization Opportunities
1. **Resource Right-sizing**: Monitor CloudWatch metrics to optimize CPU/memory
2. **Reserved Capacity**: ECS savings plans for predictable workloads
3. **Data Transfer**: Use CloudFront CDN to reduce bandwidth costs
4. **Log Retention**: Configure appropriate CloudWatch log retention periods

### Cost Monitoring
- **AWS Cost Explorer**: Filter by `CostCenter: FinancialAnalysisApp`
- **Budgets**: Set up alerts for cost thresholds
- **Resource Tags**: Track costs by service and environment

## Updates and Maintenance

### Automated Updates (Production)
1. **Code Changes**: Push to GitHub main branch
2. **Automatic Build**: CodeBuild triggers automatically
3. **Container Update**: New image pushed to ECR
4. **Rolling Deployment**: ECS Fargate updates containers with zero downtime
5. **Health Monitoring**: ALB verifies new containers before routing traffic

### Manual Operations
```bash
# Force new deployment with same task definition
aws ecs update-service --cluster financial-analysis-cluster --service financial-analysis-service --force-new-deployment

# Scale service manually
aws ecs update-service --cluster financial-analysis-cluster --service financial-analysis-service --desired-count 3

# View deployment status
aws ecs describe-services --cluster financial-analysis-cluster --services financial-analysis-service
```

### Maintenance Windows
- **SSL Certificates**: Automatically renewed by ACM
- **OS Updates**: Handled by AWS Fargate platform
- **Application Updates**: Deployed via CI/CD pipeline
- **Security Patches**: Applied during container rebuilds

---

## Summary

**InvestForge.io** represents a production-grade deployment of the Financial Analysis Multi-Agent application, featuring:

✅ **Enterprise Architecture**: ECS Fargate + ALB + Route 53 + ACM
✅ **Security**: WAF + Security Groups + IAM Roles + HTTPS
✅ **Scalability**: Auto-scaling containers with load balancing  
✅ **Monitoring**: CloudWatch logs, metrics, and health checks
✅ **CI/CD**: Automated GitHub → CodeBuild → ECR → ECS pipeline
✅ **Cost Control**: Resource tagging and optimization strategies

**Live Production URL**: [https://investforge.io](https://investforge.io)