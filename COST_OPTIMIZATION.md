# InvestForge Cost Optimization Guide

## Overview

InvestForge can be expensive to run continuously on AWS. This guide provides scripts and strategies to minimize costs while maintaining functionality.

## Cost Breakdown

### Always Running (Fixed Costs)
- **Application Load Balancer**: ~$16/month
- **Route 53 Hosted Zone**: ~$0.50/month
- **Domain Registration**: ~$12/year

### Variable Costs (Can Be Controlled)
- **ECS Fargate** (1 vCPU, 2GB RAM): ~$36/month if running 24/7
- **Lambda Functions**: Free tier (< 1M requests)
- **DynamoDB**: On-demand pricing (very low for this app)
- **CloudWatch Logs**: ~$0.50/GB stored

### Total Monthly Costs
- **24/7 Operation**: ~$53/month
- **Business Hours Only**: ~$24/month (save ~$27)
- **On-Demand Only**: ~$17/month (save ~$36)

## Cost-Saving Scripts

### 1. Manual Control Scripts

#### `./investforge-shutdown.sh`
Stops ECS service to save costs when not in use.
```bash
./investforge-shutdown.sh
```
- Saves current state
- Scales ECS to 0 tasks
- Shows cost savings estimate

#### `./investforge-startup.sh`
Restarts the application when needed.
```bash
./investforge-startup.sh
```
- Restores previous state
- Waits for health checks
- Verifies application is accessible

#### `./investforge-status.sh`
Shows current status and costs.
```bash
./investforge-status.sh
```
- Displays all resource states
- Shows current hourly/daily costs
- Lists recent activity

### 2. Automated Scheduling

#### `./investforge-schedule.sh`
Sets up automated start/stop times.
```bash
./investforge-schedule.sh
```

Options:
1. **Business Hours** (9 AM - 5 PM EST)
   - Saves ~$27/month
   - Perfect for development

2. **Extended Hours** (8 AM - 8 PM EST)
   - Saves ~$20/month
   - Good for demos

3. **Weekdays Only**
   - Saves ~$25/month
   - No weekend costs

4. **Custom Schedule**
   - Define your own times
   - Maximum flexibility

## Quick Start

### For Development (Maximum Savings)
```bash
# Stop when done working
./investforge-shutdown.sh

# Start when needed
./investforge-startup.sh

# Check status anytime
./investforge-status.sh
```

### For Production (Automated)
```bash
# Set up business hours schedule
./investforge-schedule.sh
# Choose option 1

# Override schedule if needed
./investforge-startup.sh  # Force start
./investforge-shutdown.sh # Force stop
```

## Best Practices

1. **Development Environment**
   - Always shut down when not actively developing
   - Use scheduled hours if working regularly

2. **Demo Environment**
   - Schedule around demo times
   - Use manual start for ad-hoc demos

3. **Production Environment**
   - Use business hours schedule
   - Monitor usage patterns
   - Adjust schedule based on actual usage

## Advanced Cost Optimization

### 1. Reduce ECS Resources
Edit `task-definition-secure.json`:
```json
"cpu": "512",    // Reduce from 1024
"memory": "1024" // Reduce from 2048
```
Saves additional ~$18/month

### 2. Use Spot Instances
For non-critical environments, consider Fargate Spot:
```json
"capacityProviderStrategy": [{
    "capacityProvider": "FARGATE_SPOT",
    "weight": 1
}]
```
Saves up to 70% on compute costs

### 3. Implement Caching
- Add CloudFront for static assets
- Cache API responses in ElastiCache
- Reduces compute time and costs

### 4. Optimize Lambda Functions
- Reduce memory allocation
- Use provisioned concurrency wisely
- Monitor cold starts

## Monitoring Costs

### AWS Cost Explorer
1. Go to AWS Console > Cost Explorer
2. Filter by service
3. Set up budget alerts

### CloudWatch Alarms
```bash
# Set up billing alarm for $50/month
aws cloudwatch put-metric-alarm \
  --alarm-name InvestForge-Billing \
  --alarm-description "Alert when InvestForge exceeds $50" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold
```

## Emergency Cost Control

If costs spike unexpectedly:

1. **Immediate Shutdown**
   ```bash
   ./investforge-shutdown.sh
   ```

2. **Check for Issues**
   ```bash
   ./investforge-status.sh
   aws logs tail /ecs/financial-analysis --since 1h
   ```

3. **Disable Scheduled Rules**
   ```bash
   aws events disable-rule --name investforge-scheduled-start
   aws events disable-rule --name investforge-scheduled-stop
   ```

## ROI Considerations

- **Active Development**: Save $36/month = $432/year
- **Business Hours Only**: Save $27/month = $324/year
- **Weekend Shutdown**: Save $10/month = $120/year

The scripts typically pay for themselves in less than an hour of setup time!

## Support

For issues or questions:
1. Check `investforge-ops.log` for history
2. Run `./investforge-status.sh` for current state
3. Review CloudWatch logs for detailed errors

Remember: The best optimization is turning off resources when not needed!