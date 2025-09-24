#!/usr/bin/env python3
"""
Add ALB routing for preferences endpoint.
"""

import boto3
import json

def add_preferences_routing():
    """Add ALB routing rules for preferences endpoint."""
    
    print("🔗 Setting up ALB routing for preferences")
    print("=" * 42)
    
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
        func_response = lambda_client.get_function(FunctionName='investforge-preferences')
        function_arn = func_response['Configuration']['FunctionArn']
        
        print(f"⚡ Function ARN: {function_arn}")
        
        # Create target group
        try:
            tg_response = elbv2.create_target_group(
                Name='preferences-tg',
                TargetType='lambda',
                HealthCheckEnabled=False
            )
            target_group_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
            print(f"✅ Created target group: {target_group_arn}")
            
        except Exception as e:
            if 'already exists' in str(e):
                print("✅ Target group already exists!")
                # Get existing target group
                tgs = elbv2.describe_target_groups(Names=['preferences-tg'])
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
                FunctionName='investforge-preferences',
                StatementId='alb-invoke-preferences',
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
        
        # Create listener rule
        try:
            elbv2.create_rule(
                ListenerArn=listener_arn,
                Conditions=[
                    {
                        'Field': 'path-pattern',
                        'Values': ['/api/users/preferences*']
                    }
                ],
                Priority=106,  # Use a unique priority
                Actions=[
                    {
                        'Type': 'forward',
                        'TargetGroupArn': target_group_arn
                    }
                ]
            )
            print("✅ ALB routing rule created for /api/users/preferences*")
            
        except Exception as e:
            if 'already exists' in str(e) or 'priority' in str(e).lower():
                print("✅ ALB routing rule already exists or priority conflict!")
                
                # Try with a different priority
                try:
                    elbv2.create_rule(
                        ListenerArn=listener_arn,
                        Conditions=[
                            {
                                'Field': 'path-pattern',
                                'Values': ['/api/users/preferences*']
                            }
                        ],
                        Priority=107,  # Try different priority
                        Actions=[
                            {
                                'Type': 'forward',
                                'TargetGroupArn': target_group_arn
                            }
                        ]
                    )
                    print("✅ ALB routing rule created with priority 107")
                except Exception as e2:
                    print(f"⚠️  ALB rule creation warning: {str(e2)}")
            else:
                print(f"⚠️  ALB rule creation warning: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up ALB routing: {str(e)}")
        return False

if __name__ == "__main__":
    add_preferences_routing()