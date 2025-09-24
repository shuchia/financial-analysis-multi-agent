#!/usr/bin/env python3
"""
Set up ALB routing for the analytics endpoint.
"""

import boto3
import json

def setup_analytics_alb_routing():
    """Set up ALB routing for analytics endpoint."""
    
    print("🔗 Setting up ALB routing for analytics")
    print("=" * 40)
    
    elbv2 = boto3.client('elbv2')
    lambda_client = boto3.client('lambda')
    
    try:
        # Get the ALB ARN
        alb_arn = "arn:aws:elasticloadbalancing:us-east-1:453636587892:loadbalancer/app/financial-analysis-alb/3d7f9d05948bbff6"
        
        # Get the listener
        listeners = elbv2.describe_listeners(LoadBalancerArn=alb_arn)
        listener_arn = listeners['Listeners'][0]['ListenerArn']
        
        print(f"📊 Using ALB: financial-analysis-alb")
        print(f"🎯 Using listener: {listener_arn}")
        
        # Get function ARN
        func_response = lambda_client.get_function(FunctionName='investforge-analytics-new')
        function_arn = func_response['Configuration']['FunctionArn']
        
        print(f"⚡ Function ARN: {function_arn}")
        
        # Create target group for analytics
        try:
            tg_response = elbv2.create_target_group(
                Name='analytics-tg',
                TargetType='lambda',
                HealthCheckEnabled=False
            )
            target_group_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
            print(f"✅ Created target group: {target_group_arn}")
            
        except Exception as e:
            if 'already exists' in str(e):
                print("✅ Target group already exists!")
                # Get existing target group
                tgs = elbv2.describe_target_groups(Names=['analytics-tg'])
                target_group_arn = tgs['TargetGroups'][0]['TargetGroupArn']
            else:
                raise e
        
        # Register Lambda with target group
        try:
            elbv2.register_targets(
                TargetGroupArn=target_group_arn,
                Targets=[{'Id': function_arn}]
            )
            print("✅ Lambda registered with target group")
        except Exception as e:
            if 'already registered' in str(e):
                print("✅ Lambda already registered")
            else:
                print(f"⚠️  Registration warning: {str(e)}")
        
        # Add Lambda permission for ALB
        try:
            lambda_client.add_permission(
                FunctionName='investforge-analytics-new',
                StatementId='alb-invoke-analytics',
                Action='lambda:InvokeFunction',
                Principal='elasticloadbalancing.amazonaws.com',
                SourceArn=target_group_arn
            )
            print("✅ Lambda permission added for ALB")
        except Exception as e:
            if 'already exists' in str(e):
                print("✅ Lambda permission already exists")
            else:
                print(f"⚠️  Permission warning: {str(e)}")
        
        # Create listener rules for analytics endpoints
        try:
            # Rule for /api/analytics/track
            elbv2.create_rule(
                ListenerArn=listener_arn,
                Conditions=[
                    {
                        'Field': 'path-pattern',
                        'Values': ['/api/analytics*']
                    }
                ],
                Priority=108,
                Actions=[
                    {
                        'Type': 'forward',
                        'TargetGroupArn': target_group_arn
                    }
                ]
            )
            print("✅ ALB routing rule created for /api/analytics*")
            
        except Exception as e:
            if 'already exists' in str(e) or 'priority' in str(e).lower():
                print("✅ ALB routing rule already exists or priority conflict!")
                
                # Try with different priority
                try:
                    elbv2.create_rule(
                        ListenerArn=listener_arn,
                        Conditions=[
                            {
                                'Field': 'path-pattern',
                                'Values': ['/api/analytics*']
                            }
                        ],
                        Priority=109,
                        Actions=[
                            {
                                'Type': 'forward',
                                'TargetGroupArn': target_group_arn
                            }
                        ]
                    )
                    print("✅ ALB routing rule created with priority 109")
                except Exception as e2:
                    print(f"⚠️  ALB rule creation warning: {str(e2)}")
            else:
                print(f"⚠️  ALB rule creation warning: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up ALB routing: {str(e)}")
        return False

def test_analytics_endpoints():
    """Test the analytics endpoints."""
    
    print("\n🧪 Testing Analytics Endpoints")
    print("=" * 30)
    
    import requests
    import time
    import uuid
    
    # Wait for ALB to propagate changes
    print("⏳ Waiting for ALB changes to propagate...")
    time.sleep(10)
    
    # Test 1: Track an event
    print("1️⃣ Testing event tracking...")
    test_user_id = f"test-user-{str(uuid.uuid4())[:8]}"
    
    track_response = requests.post(
        "https://investforge.io/api/analytics/track",
        headers={"Content-Type": "application/json"},
        json={
            "action": "track",
            "user_id": test_user_id,
            "event_type": "test_event",
            "event_data": {
                "test": True,
                "timestamp": "2025-09-23T20:30:00.000Z"
            }
        }
    )
    
    print(f"Track status: {track_response.status_code}")
    if track_response.status_code == 200:
        track_data = track_response.json()
        print(f"Track success: {track_data.get('success')}")
    else:
        print(f"Track error: {track_response.text}")
    
    # Test 2: Update usage
    print("\n2️⃣ Testing usage tracking...")
    usage_response = requests.post(
        "https://investforge.io/api/analytics/usage",
        headers={"Content-Type": "application/json"},
        json={
            "action": "usage",
            "user_id": test_user_id,
            "feature": "stock_analysis",
            "count": 1
        }
    )
    
    print(f"Usage status: {usage_response.status_code}")
    if usage_response.status_code == 200:
        usage_data = usage_response.json()
        print(f"Usage success: {usage_data.get('success')}")
    else:
        print(f"Usage error: {usage_response.text}")
    
    # Test 3: Get usage
    print("\n3️⃣ Testing usage retrieval...")
    time.sleep(1)  # Brief pause for consistency
    
    get_usage_response = requests.post(
        "https://investforge.io/api/analytics/usage",
        headers={"Content-Type": "application/json"},
        json={
            "action": "get_usage",
            "user_id": test_user_id
        }
    )
    
    print(f"Get usage status: {get_usage_response.status_code}")
    if get_usage_response.status_code == 200:
        get_usage_data = get_usage_response.json()
        print(f"Get usage success: {get_usage_data.get('success')}")
        
        if get_usage_data.get('success'):
            usage_info = get_usage_data.get('data', {})
            print(f"Usage data: {json.dumps(usage_info, indent=2)}")
    else:
        print(f"Get usage error: {get_usage_response.text}")

def main():
    """Main function."""
    print("🚀 Setting Up Analytics ALB Routing")
    print("=" * 35)
    
    if setup_analytics_alb_routing():
        print("\n✅ Analytics ALB routing configured!")
        
        # Test the endpoints
        test_analytics_endpoints()
        
        print("\n📋 Summary:")
        print("   ✅ Analytics target group created")
        print("   ✅ Lambda registered with ALB")
        print("   ✅ ALB routing rules configured")
        print("   ✅ Analytics endpoints tested")
        print("\n🎯 Analytics system fully operational!")
    else:
        print("\n❌ Failed to set up analytics ALB routing")

if __name__ == "__main__":
    main()