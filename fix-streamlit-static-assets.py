#!/usr/bin/env python3
"""
Fix Streamlit static asset configuration for baseUrlPath.
The issue is that Streamlit generates /static/* URLs but they should be /app/static/*
when baseUrlPath=/app is set.
"""

import boto3
import json

def update_streamlit_config():
    """Update Streamlit configuration to properly handle static assets with baseUrlPath."""
    
    print("🔧 Fixing Streamlit Static Asset Configuration")
    print("=" * 50)
    
    # The issue is that Streamlit needs additional configuration for static assets
    # when using baseUrlPath. We need to add Streamlit server config.
    
    print("📋 Current issue:")
    print("   - Streamlit serves at /app (baseUrlPath=/app)")
    print("   - Static assets are generated as /static/* (incorrect)")
    print("   - They should be /app/static/* or served correctly at /static/*")
    print("")
    
    # Solution: Update the Streamlit command to include proper static asset handling
    updated_command = [
        "streamlit", "run", "app.py", 
        "--server.port=8080", 
        "--server.address=0.0.0.0", 
        "--server.baseUrlPath=/app",
        "--server.enableStaticServing=true"
    ]
    
    print("🔧 Updated Streamlit command:")
    print(f"   {' '.join(updated_command)}")
    print("")
    
    # Check current ECS task definition
    ecs = boto3.client('ecs')
    
    try:
        # Get current task
        tasks = ecs.list_tasks(cluster='financial-analysis-cluster')
        if not tasks['taskArns']:
            print("❌ No running tasks found")
            return False
            
        task_arn = tasks['taskArns'][0]
        task_details = ecs.describe_tasks(
            cluster='financial-analysis-cluster',
            tasks=[task_arn]
        )
        
        task_def_arn = task_details['tasks'][0]['taskDefinitionArn']
        print(f"📋 Current task definition: {task_def_arn}")
        
        # Get task definition
        task_def_response = ecs.describe_task_definition(taskDefinition=task_def_arn)
        task_def = task_def_response['taskDefinition']
        
        # Update container definition
        container_def = task_def['containerDefinitions'][0].copy()
        container_def['command'] = updated_command
        
        # Create new task definition
        new_task_def = {
            'family': task_def['family'],
            'networkMode': task_def['networkMode'],
            'requiresCompatibilities': task_def['requiresCompatibilities'],
            'cpu': task_def['cpu'],
            'memory': task_def['memory'],
            'executionRoleArn': task_def['executionRoleArn'],
            'taskRoleArn': task_def.get('taskRoleArn', task_def['executionRoleArn']),
            'containerDefinitions': [container_def]
        }
        
        print("📤 Registering new task definition...")
        new_task_response = ecs.register_task_definition(**new_task_def)
        new_task_def_arn = new_task_response['taskDefinition']['taskDefinitionArn']
        
        print(f"✅ New task definition: {new_task_def_arn}")
        
        # Stop current task to force restart with new definition
        print("🔄 Stopping current task to restart with new configuration...")
        ecs.stop_task(
            cluster='financial-analysis-cluster',
            task=task_arn,
            reason='Updating Streamlit static asset configuration'
        )
        
        # Start new task
        print("🚀 Starting new task with updated configuration...")
        run_task_response = ecs.run_task(
            cluster='financial-analysis-cluster',
            taskDefinition=new_task_def_arn,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': ['subnet-b1a31ebd'],  # Same subnet as current task
                    'securityGroups': ['sg-0a82dbb92feae4e72'],  # ECS security group
                    'assignPublicIp': 'ENABLED'
                }
            }
        )
        
        new_task_arn = run_task_response['tasks'][0]['taskArn']
        print(f"✅ New task started: {new_task_arn}")
        
        print("\n⏳ Waiting for task to start and register with ALB...")
        print("This will take 2-3 minutes.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating task: {e}")
        return False

def check_alternative_solution():
    """Check if we need alternative solution for static assets."""
    print("\n🔍 Alternative Solution Analysis")
    print("=" * 35)
    
    print("If the Streamlit config update doesn't work, the issue might be:")
    print("1. CloudFront cache behaviors for /static/* need adjustment")
    print("2. ALB health check path might be wrong")
    print("3. Streamlit version compatibility with baseUrlPath")
    print("")
    
    print("📋 Manual CloudFront fix (if needed):")
    print("Go to AWS Console → CloudFront → Distribution E9A4E00CLHHQQ")
    print("Update the /static/* behavior:")
    print("   - Path pattern: /static/*")
    print("   - Origin: ALB-investforge") 
    print("   - Cache policy: CachingDisabled")
    print("   - Origin request policy: AllViewer")
    print("   - Viewer protocol: Redirect HTTP to HTTPS")

def main():
    """Main function."""
    if update_streamlit_config():
        print("\n✅ Streamlit configuration updated!")
        print("\n🧪 After 2-3 minutes, test:")
        print("   https://investforge.io/app")
        print("   Static assets should load properly.")
        
        check_alternative_solution()
    else:
        print("\n❌ Failed to update Streamlit configuration")
        check_alternative_solution()

if __name__ == "__main__":
    main()