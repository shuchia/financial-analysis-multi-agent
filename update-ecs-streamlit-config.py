#!/usr/bin/env python3
"""
Update ECS task definition to use Streamlit configuration file.
Since CodeBuild failed due to Docker Hub rate limits, we'll create a new 
task definition that includes the Streamlit config file directly.
"""

import boto3
import json

def update_ecs_task_definition():
    """Update ECS task definition with new Streamlit configuration."""
    
    print("🔧 Updating ECS Task Definition for Streamlit Config")
    print("=" * 55)
    
    ecs = boto3.client('ecs')
    
    try:
        # Get current task definition
        current_task_response = ecs.describe_task_definition(
            taskDefinition='financial-analysis-task:3'
        )
        current_task_def = current_task_response['taskDefinition']
        
        print(f"📋 Current task definition: {current_task_def['taskDefinitionArn']}")
        
        # Create new container definition with updated command
        container_def = current_task_def['containerDefinitions'][0].copy()
        
        # Update the command to use a config file approach
        # Since we can't rebuild the image, we'll create the config file at runtime
        new_command = [
            "sh", "-c", """
            mkdir -p .streamlit && cat > .streamlit/config.toml << 'EOF'
[server]
port = 8080
address = "0.0.0.0"
baseUrlPath = "/app"
enableStaticServing = true
enableCORS = false

[browser]
gatherUsageStats = false

[client]
toolbarMode = "minimal"

[theme]
base = "light"
EOF
            streamlit run app.py
            """
        ]
        
        container_def['command'] = new_command
        
        print("🔧 Updated container command to create config file at runtime")
        
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
        
        print("📤 Registering new task definition...")
        new_task_response = ecs.register_task_definition(**new_task_def)
        new_task_def_arn = new_task_response['taskDefinition']['taskDefinitionArn']
        
        print(f"✅ New task definition: {new_task_def_arn}")
        
        return new_task_def_arn
        
    except Exception as e:
        print(f"❌ Error updating task definition: {e}")
        return None

def restart_ecs_task(task_def_arn):
    """Restart ECS task with new task definition."""
    
    print("\n🔄 Restarting ECS Task with New Configuration")
    print("=" * 45)
    
    ecs = boto3.client('ecs')
    
    try:
        # Stop current task
        current_tasks = ecs.list_tasks(cluster='financial-analysis-cluster')
        
        if current_tasks['taskArns']:
            current_task_arn = current_tasks['taskArns'][0]
            print(f"🛑 Stopping current task: {current_task_arn}")
            
            ecs.stop_task(
                cluster='financial-analysis-cluster',
                task=current_task_arn,
                reason='Updating Streamlit configuration for static assets'
            )
            
            print("⏳ Waiting for task to stop...")
            
        # Start new task with updated definition
        print(f"🚀 Starting new task with: {task_def_arn}")
        
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
        
        new_task_arn = run_task_response['tasks'][0]['taskArn']
        print(f"✅ New task started: {new_task_arn}")
        
        print("\n⏳ Task is starting... This will take 2-3 minutes.")
        print("The task needs to:")
        print("1. Start container")
        print("2. Create Streamlit config file")
        print("3. Start Streamlit with new configuration")
        print("4. Register with ALB target group")
        
        return new_task_arn
        
    except Exception as e:
        print(f"❌ Error restarting task: {e}")
        return None

def register_new_task_with_alb(task_arn):
    """Register new task with ALB target group."""
    
    print("\n🔗 Registering New Task with ALB")
    print("=" * 35)
    
    ecs = boto3.client('ecs')
    elbv2 = boto3.client('elbv2')
    
    try:
        # Wait a bit for task to get IP
        import time
        print("⏳ Waiting for task to get network interface...")
        time.sleep(30)
        
        # Get task details
        task_details = ecs.describe_tasks(
            cluster='financial-analysis-cluster',
            tasks=[task_arn]
        )
        
        if not task_details['tasks']:
            print("❌ Task not found")
            return False
            
        task = task_details['tasks'][0]
        
        # Get IP address
        if not task['attachments']:
            print("❌ Task has no network attachments yet")
            return False
            
        task_ip = None
        for attachment in task['attachments']:
            for detail in attachment['details']:
                if detail['name'] == 'privateIPv4Address':
                    task_ip = detail['value']
                    break
            if task_ip:
                break
        
        if not task_ip:
            print("❌ Could not get task IP address")
            return False
            
        print(f"📋 Task IP: {task_ip}")
        
        # Register with ALB target group
        target_group_arn = "arn:aws:elasticloadbalancing:us-east-1:453636587892:targetgroup/financial-analysis-tg/466854200bba31ca"
        
        print(f"🔗 Registering {task_ip}:8080 with ALB target group...")
        elbv2.register_targets(
            TargetGroupArn=target_group_arn,
            Targets=[
                {
                    'Id': task_ip,
                    'Port': 8080
                }
            ]
        )
        
        print("✅ Task registered with ALB target group")
        print("\n⏳ Waiting for health check... (30-60 seconds)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error registering task with ALB: {e}")
        return False

def main():
    """Main function."""
    print("🚀 Updating Streamlit Configuration via ECS Task Definition")
    print("=" * 60)
    
    # Update task definition
    new_task_def_arn = update_ecs_task_definition()
    if not new_task_def_arn:
        print("\n❌ Failed to update task definition")
        return
    
    # Restart task
    new_task_arn = restart_ecs_task(new_task_def_arn)
    if not new_task_arn:
        print("\n❌ Failed to restart task")
        return
    
    # Register with ALB
    if register_new_task_with_alb(new_task_arn):
        print("\n✅ ECS task updated successfully!")
        print("\n🧪 After 2-3 minutes, test:")
        print("   https://investforge.io/app")
        print("   The static assets should now load properly with baseUrlPath configuration.")
        
        print("\n📋 What was changed:")
        print("   ✅ Added Streamlit config file creation at runtime")
        print("   ✅ Enabled proper baseUrlPath handling")
        print("   ✅ Configured static asset serving")
        print("   ✅ Registered new task with ALB")
    else:
        print("\n⚠️  Task updated but ALB registration may need manual verification")

if __name__ == "__main__":
    main()