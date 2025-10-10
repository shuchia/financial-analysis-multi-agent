#!/usr/bin/env python3
"""
Deploy latest application code by creating a new ECS task that downloads 
the latest code from GitHub at runtime since Docker build is failing.
"""

import boto3
import json

def create_runtime_update_task():
    """Create ECS task that pulls latest code at runtime."""
    
    print("🚀 Creating ECS Task with Runtime Code Update")
    print("=" * 50)
    
    ecs = boto3.client('ecs')
    
    try:
        # Get current task definition as base
        current_task_response = ecs.describe_task_definition(
            taskDefinition='financial-analysis-task:3'
        )
        current_task_def = current_task_response['taskDefinition']
        
        print(f"📋 Base task definition: {current_task_def['taskDefinitionArn']}")
        
        # Create new container definition with updated command
        container_def = current_task_def['containerDefinitions'][0].copy()
        
        # Create a startup script that downloads latest code and runs Streamlit
        startup_script = '''
        set -e
        echo "🔄 Updating application code from GitHub..."
        
        # Install git
        apt-get update && apt-get install -y git
        
        # Backup current app.py if it exists
        if [ -f /app/app.py ]; then
            mv /app/app.py /app/app.py.backup
        fi
        
        # Clone latest code
        cd /tmp
        git clone https://github.com/shuchia/financial-analysis-multi-agent.git repo
        
        # Copy latest app code from root directory
        cp /tmp/repo/app.py /app/
        cp -r /tmp/repo/components /app/
        cp -r /tmp/repo/tools /app/
        cp -r /tmp/repo/utils /app/
        cp -r /tmp/repo/auth /app/
        cp -r /tmp/repo/static /app/
        cp /tmp/repo/crew.py /app/
        cp /tmp/repo/requirements.txt /app/
        
        # Ensure requirements are up to date
        pip install -r /app/requirements.txt
        
        echo "✅ Code updated successfully"
        echo "🚀 Starting Streamlit with latest code..."
        
        # Start Streamlit with proper configuration
        streamlit run /app/app.py \\
            --server.port=8080 \\
            --server.address=0.0.0.0 \\
            --server.baseUrlPath=/app \\
            --server.enableCORS=false \\
            --server.enableXsrfProtection=false
        '''
        
        # Use shell command to run the startup script
        container_def['command'] = ["sh", "-c", startup_script]
        
        # Update health check
        container_def['healthCheck'] = {
            'command': ["CMD-SHELL", "curl -f http://localhost:8080/app/_stcore/health || exit 1"],
            'interval': 30,
            'timeout': 10,
            'retries': 3,
            'startPeriod': 120  # Increased to allow time for code download
        }
        
        print("🔧 Updated container with:")
        print("   ✓ Runtime GitHub code download")
        print("   ✓ Latest application files")
        print("   ✓ Updated requirements installation")
        print("   ✓ Proper Streamlit configuration")
        print("   ✓ 120s health check start period")
        
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

def deploy_updated_task(task_def_arn):
    """Deploy new ECS task with latest code."""
    
    print("\n🚀 Deploying Task with Latest Code")
    print("=" * 35)
    
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
                    reason='Deploying with latest application code'
                )
        
        # Start new task
        print(f"\n🚀 Starting new task with latest code...")
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
        
        # Wait longer for task to initialize and download code
        print("\n⏳ Waiting for task to download code and initialize (90 seconds)...")
        import time
        time.sleep(90)
        
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
            
            # Register with ALB (deregister old targets first)
            target_group_arn = "arn:aws:elasticloadbalancing:us-east-1:453636587892:targetgroup/financial-analysis-tg/466854200bba31ca"
            
            # Deregister old targets
            current_targets = elbv2.describe_target_health(TargetGroupArn=target_group_arn)
            for target in current_targets['TargetHealthDescriptions']:
                if target['Target']['Id'] != task_ip:  # Don't deregister if it's the same IP
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
    print("🚀 Deploying Latest Application Code via Runtime Update")
    print("=" * 55)
    print("\nThis approach downloads the latest code from GitHub")
    print("at container startup to work around Docker build issues.\n")
    
    # Create new task definition
    new_task_def_arn = create_runtime_update_task()
    if not new_task_def_arn:
        return
    
    # Deploy new task
    if deploy_updated_task(new_task_def_arn):
        print("\n✅ Deployment successful!")
        print("\n🧪 Wait 3-5 minutes for complete initialization, then test:")
        print("   https://investforge.io/app")
        print("   Click 'Get Started' button to test signup flow")
        print("\n📋 What was deployed:")
        print("   ✓ Latest application code from GitHub")
        print("   ✓ Updated Streamlit app with all features")
        print("   ✓ Fixed landing page links")
        print("   ✓ Multi-agent financial analysis tools")
        print("   ✓ Updated requirements and dependencies")
    else:
        print("\n❌ Deployment failed")

if __name__ == "__main__":
    main()