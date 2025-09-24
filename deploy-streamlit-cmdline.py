#!/usr/bin/env python3
"""
Deploy ECS task with command-line Streamlit configuration.
Since Docker build is failing, we'll update the task definition to use
the correct command-line arguments.
"""

import boto3
import json

def create_new_task_definition():
    """Create new task definition with command-line Streamlit config."""
    
    print("🔧 Creating ECS Task Definition with Command-Line Config")
    print("=" * 60)
    
    ecs = boto3.client('ecs')
    
    try:
        # Get current task definition
        current_task_response = ecs.describe_task_definition(
            taskDefinition='financial-analysis-task:3'
        )
        current_task_def = current_task_response['taskDefinition']
        
        print(f"📋 Base task definition: {current_task_def['taskDefinitionArn']}")
        
        # Create new container definition with updated command
        container_def = current_task_def['containerDefinitions'][0].copy()
        
        # Use command-line arguments for Streamlit configuration
        container_def['command'] = [
            "streamlit", "run", "app.py",
            "--server.port=8080",
            "--server.address=0.0.0.0", 
            "--server.baseUrlPath=/app",
            "--server.enableCORS=false",
            "--server.enableXsrfProtection=false"
        ]
        
        # Update health check
        container_def['healthCheck'] = {
            'command': ["CMD-SHELL", "curl -f http://localhost:8080/app/_stcore/health || exit 1"],
            'interval': 30,
            'timeout': 10,
            'retries': 3,
            'startPeriod': 30
        }
        
        print("🔧 Updated container with:")
        print("   ✓ Command-line Streamlit configuration")
        print("   ✓ baseUrlPath=/app")
        print("   ✓ Health check path: /app/_stcore/health")
        print("   ✓ 30s start period")
        
        # Create new task definition
        new_task_def = {
            'family': current_task_def['family'],
            'networkMode': current_task_def['networkMode'],
            'requiresCompatibilities': current_task_def['requiresCompatibilities'],
            'cpu': current_task_def['cpu'],
            'memory': current_task_def['memory'],
            'executionRoleArn': current_task_def['executionRoleArn'],
            'containerDefinitions': [container_def]
        }
        
        # Add task role if it exists
        if 'taskRoleArn' in current_task_def:
            new_task_def['taskRoleArn'] = current_task_def['taskRoleArn']
        
        print("\n📤 Registering new task definition...")
        new_task_response = ecs.register_task_definition(**new_task_def)
        new_task_def_arn = new_task_response['taskDefinition']['taskDefinitionArn']
        
        print(f"✅ New task definition: {new_task_def_arn}")
        
        return new_task_def_arn
        
    except Exception as e:
        print(f"❌ Error creating task definition: {e}")
        return None

def deploy_new_task(task_def_arn):
    """Deploy new ECS task and register with ALB."""
    
    print("\n🚀 Deploying New ECS Task")
    print("=" * 30)
    
    ecs = boto3.client('ecs')
    elbv2 = boto3.client('elbv2')
    
    try:
        # Stop current tasks
        current_tasks = ecs.list_tasks(cluster='financial-analysis-cluster')
        
        if current_tasks['taskArns']:
            print("🛑 Stopping current tasks...")
            for task_arn in current_tasks['taskArns']:
                ecs.stop_task(
                    cluster='financial-analysis-cluster',
                    task=task_arn,
                    reason='Deploying with command-line Streamlit config'
                )
        
        # Start new task
        print(f"\n🚀 Starting new task...")
        run_task_response = ecs.run_task(
            cluster='financial-analysis-cluster',
            taskDefinition=task_def_arn,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': ['subnet-b1a31ebd'],
                    'securityGroups': ['sg-0999dd77451bb6be2'],
                    'assignPublicIp': 'ENABLED'
                }
            }
        )
        
        new_task = run_task_response['tasks'][0]
        new_task_arn = new_task['taskArn']
        print(f"✅ Task started: {new_task_arn}")
        
        # Wait for task to get IP
        print("\n⏳ Waiting for task to initialize (45 seconds)...")
        import time
        time.sleep(45)
        
        # Get task IP
        task_details = ecs.describe_tasks(
            cluster='financial-analysis-cluster',
            tasks=[new_task_arn]
        )
        
        task_ip = None
        for attachment in task_details['tasks'][0]['attachments']:
            for detail in attachment['details']:
                if detail['name'] == 'privateIPv4Address':
                    task_ip = detail['value']
                    break
            if task_ip:
                break
        
        if task_ip:
            print(f"📋 Task IP: {task_ip}")
            
            # Register with ALB
            target_group_arn = "arn:aws:elasticloadbalancing:us-east-1:453636587892:targetgroup/financial-analysis-tg/466854200bba31ca"
            
            # Deregister old targets
            current_targets = elbv2.describe_target_health(TargetGroupArn=target_group_arn)
            for target in current_targets['TargetHealthDescriptions']:
                print(f"🔄 Deregistering old target: {target['Target']['Id']}")
                elbv2.deregister_targets(
                    TargetGroupArn=target_group_arn,
                    Targets=[target['Target']]
                )
            
            # Register new target
            print(f"\n🔗 Registering new target: {task_ip}:8080")
            elbv2.register_targets(
                TargetGroupArn=target_group_arn,
                Targets=[{'Id': task_ip, 'Port': 8080}]
            )
            
            print("✅ Task registered with ALB")
            return True
        else:
            print("❌ Could not get task IP")
            return False
            
    except Exception as e:
        print(f"❌ Error deploying task: {e}")
        return False

def main():
    """Main function."""
    print("🚀 Deploying Streamlit with Command-Line Configuration")
    print("=" * 55)
    print("\nSince Docker build is failing, we'll deploy directly")
    print("with the existing image but new configuration.\n")
    
    # Create new task definition
    new_task_def_arn = create_new_task_definition()
    if not new_task_def_arn:
        return
    
    # Deploy new task
    if deploy_new_task(new_task_def_arn):
        print("\n✅ Deployment successful!")
        print("\n🧪 Wait 2-3 minutes for health checks, then test:")
        print("   https://investforge.io/app")
        print("   https://investforge.io/api/health")
        print("   https://investforge.io/")
        print("\n📋 What was deployed:")
        print("   ✓ Streamlit with --server.baseUrlPath=/app")
        print("   ✓ CORS and XSRF protection disabled")
        print("   ✓ Health check on /app/_stcore/health")
        print("   ✓ 30s start period for proper initialization")
    else:
        print("\n❌ Deployment failed")

if __name__ == "__main__":
    main()