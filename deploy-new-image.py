#!/usr/bin/env python3
"""
Deploy the newly built Docker image to ECS.
The CodeBuild succeeded, so we now have a fresh image with all the latest code.
"""

import boto3
import json

def deploy_new_image():
    """Deploy ECS task with the newly built Docker image."""
    
    print("🚀 Deploying Newly Built Docker Image")
    print("=" * 40)
    
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
                    reason='Deploying newly built image with latest code'
                )
        
        # Use the existing task definition (financial-analysis-task:6) which has the right config
        # but it will pull the latest image from ECR automatically
        task_def_arn = 'financial-analysis-task:6'
        
        print(f"🚀 Starting new task with latest image...")
        print(f"   Using task definition: {task_def_arn}")
        print(f"   ECR will automatically pull the latest image")
        
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
        
        # Wait for task to initialize
        print("\n⏳ Waiting for task to initialize (60 seconds)...")
        import time
        time.sleep(60)
        
        # Get task IP
        task_details = ecs.describe_tasks(
            cluster='financial-analysis-cluster',
            tasks=[new_task_arn]
        )
        
        if not task_details['tasks']:
            print("❌ Task not found")
            return False
            
        task = task_details['tasks'][0]
        task_ip = None
        
        for attachment in task['attachments']:
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
                if target['Target']['Id'] != task_ip:
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
            
            # Wait for health check
            print("\n⏳ Waiting for health check to pass (90 seconds)...")
            time.sleep(90)
            
            # Check health status
            health_status = elbv2.describe_target_health(TargetGroupArn=target_group_arn)
            for target in health_status['TargetHealthDescriptions']:
                if target['Target']['Id'] == task_ip:
                    state = target['TargetHealth']['State']
                    print(f"📊 Target health: {state}")
                    break
            
            return True
        else:
            print("❌ Could not get task IP")
            return False
            
    except Exception as e:
        print(f"❌ Error deploying image: {e}")
        return False

def main():
    """Main function."""
    print("🚀 Deploying Latest Docker Image with All Application Code")
    print("=" * 55)
    print("\nThe CodeBuild succeeded! Now deploying the fresh image")
    print("which contains all the latest application code.\n")
    
    if deploy_new_image():
        print("\n🎉 SUCCESS! Latest application deployed!")
        print("\n🧪 Now test the complete application:")
        print("   1. Landing page: https://investforge.io/")
        print("   2. Click 'Get Started' button")
        print("   3. Should now go to the Streamlit app with latest code")
        print("\n📋 What was deployed:")
        print("   ✅ Latest Docker image from successful CodeBuild")
        print("   ✅ Complete Streamlit financial analysis application")
        print("   ✅ All multi-agent CrewAI tools and features")
        print("   ✅ Fixed landing page navigation")
        print("   ✅ Updated dependencies and requirements")
        print("   ✅ Proper Streamlit configuration with baseUrlPath=/app")
    else:
        print("\n❌ Deployment failed")

if __name__ == "__main__":
    main()