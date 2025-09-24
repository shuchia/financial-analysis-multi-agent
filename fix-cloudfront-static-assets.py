#!/usr/bin/env python3
"""
Fix CloudFront configuration to properly handle Streamlit static assets.
The issue is that Streamlit serves static assets from /static/* but CloudFront
is not configured to route these to the ALB.
"""

import boto3
import json
import time

def update_cloudfront_behavior():
    """Update CloudFront distribution to handle static assets."""
    cloudfront = boto3.client('cloudfront')
    distribution_id = "E9A4E00CLHHQQ"
    
    print("🔧 Fixing CloudFront Configuration for Static Assets")
    print("=" * 55)
    
    try:
        # Get current distribution configuration
        print("📋 Getting current CloudFront configuration...")
        response = cloudfront.get_distribution_config(Id=distribution_id)
        config = response['DistributionConfig']
        etag = response['ETag']
        
        print(f"✅ Retrieved configuration (ETag: {etag})")
        
        # Add cache behavior for static assets
        print("🔧 Adding cache behavior for /static/* paths...")
        
        # Check if /static/* behavior already exists
        static_behavior_exists = False
        for behavior in config.get('CacheBehaviors', {}).get('Items', []):
            if behavior['PathPattern'] == '/static/*':
                static_behavior_exists = True
                print("⚠️  /static/* behavior already exists")
                break
        
        if not static_behavior_exists:
            # Create new cache behavior for static assets
            static_behavior = {
                'PathPattern': '/static/*',
                'TargetOriginId': 'ALB-investforge',
                'ViewerProtocolPolicy': 'redirect-to-https',
                'AllowedMethods': {
                    'Quantity': 3,
                    'Items': ['GET', 'HEAD', 'OPTIONS'],
                    'CachedMethods': {
                        'Quantity': 2,
                        'Items': ['GET', 'HEAD']
                    }
                },
                'ForwardedValues': {
                    'QueryString': False,
                    'Cookies': {'Forward': 'none'},
                    'Headers': {
                        'Quantity': 3,
                        'Items': ['Host', 'Origin', 'Referer']
                    }
                },
                'TrustedSigners': {
                    'Enabled': False,
                    'Quantity': 0
                },
                'MinTTL': 86400,  # Cache static assets for 1 day
                'DefaultTTL': 86400,
                'MaxTTL': 31536000,  # Max 1 year
                'Compress': True
            }
            
            # Add the new behavior
            if 'CacheBehaviors' not in config:
                config['CacheBehaviors'] = {'Quantity': 0, 'Items': []}
            
            config['CacheBehaviors']['Items'].append(static_behavior)
            config['CacheBehaviors']['Quantity'] = len(config['CacheBehaviors']['Items'])
            
            print("✅ Added /static/* cache behavior")
        
        # Also add behavior for _stcore (Streamlit core assets)
        stcore_behavior_exists = False
        for behavior in config.get('CacheBehaviors', {}).get('Items', []):
            if behavior['PathPattern'] == '/_stcore/*':
                stcore_behavior_exists = True
                print("⚠️  /_stcore/* behavior already exists")
                break
        
        if not stcore_behavior_exists:
            stcore_behavior = {
                'PathPattern': '/_stcore/*',
                'TargetOriginId': 'ALB-investforge',
                'ViewerProtocolPolicy': 'redirect-to-https',
                'AllowedMethods': {
                    'Quantity': 3,
                    'Items': ['GET', 'HEAD', 'OPTIONS'],
                    'CachedMethods': {
                        'Quantity': 2,
                        'Items': ['GET', 'HEAD']
                    }
                },
                'ForwardedValues': {
                    'QueryString': False,
                    'Cookies': {'Forward': 'none'},
                    'Headers': {
                        'Quantity': 3,
                        'Items': ['Host', 'Origin', 'Referer']
                    }
                },
                'TrustedSigners': {
                    'Enabled': False,
                    'Quantity': 0
                },
                'MinTTL': 86400,
                'DefaultTTL': 86400,
                'MaxTTL': 31536000,
                'Compress': True
            }
            
            config['CacheBehaviors']['Items'].append(stcore_behavior)
            config['CacheBehaviors']['Quantity'] = len(config['CacheBehaviors']['Items'])
            
            print("✅ Added /_stcore/* cache behavior")
        
        # Update the distribution
        print("📤 Updating CloudFront distribution...")
        update_response = cloudfront.update_distribution(
            Id=distribution_id,
            DistributionConfig=config,
            IfMatch=etag
        )
        
        print("✅ CloudFront distribution updated successfully!")
        print(f"   Status: {update_response['Distribution']['Status']}")
        
        # Create invalidation to clear cache
        print("🔄 Creating invalidation for static assets...")
        invalidation_response = cloudfront.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                'Paths': {
                    'Quantity': 3,
                    'Items': ['/static/*', '/_stcore/*', '/app*']
                },
                'CallerReference': f'static-assets-fix-{int(time.time())}'
            }
        )
        
        invalidation_id = invalidation_response['Invalidation']['Id']
        print(f"✅ Invalidation created: {invalidation_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating CloudFront: {e}")
        return False

def check_streamlit_base_url():
    """Check if Streamlit needs base URL configuration."""
    print("\n🔍 Checking Streamlit Configuration")
    print("=" * 35)
    
    print("📋 Streamlit might need base URL configuration for CloudFront.")
    print("The app should be configured with --server.baseUrlPath=/app")
    
    # Check current ECS task definition
    ecs = boto3.client('ecs')
    
    try:
        # Get running tasks
        tasks = ecs.list_tasks(cluster='financial-analysis-cluster')
        if tasks['taskArns']:
            task_arn = tasks['taskArns'][0]
            task_details = ecs.describe_tasks(
                cluster='financial-analysis-cluster',
                tasks=[task_arn]
            )
            
            task_def_arn = task_details['tasks'][0]['taskDefinitionArn']
            print(f"📋 Current task definition: {task_def_arn}")
            
            # Get task definition details
            task_def = ecs.describe_task_definition(taskDefinition=task_def_arn)
            container_def = task_def['taskDefinition']['containerDefinitions'][0]
            
            print("📋 Current container command:")
            if 'command' in container_def:
                print(f"   {' '.join(container_def['command'])}")
            else:
                print("   No custom command specified")
            
            print("\n🔧 Recommended Streamlit command for CloudFront:")
            print('   ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.baseUrlPath=/app"]')
            
    except Exception as e:
        print(f"⚠️  Could not check ECS configuration: {e}")

def main():
    """Main function."""
    print("🚀 Fixing Streamlit Static Assets in CloudFront")
    print("=" * 50)
    
    # Update CloudFront configuration
    if update_cloudfront_behavior():
        print("\n✅ CloudFront configuration updated!")
        print("\n⏳ Changes will take 5-10 minutes to propagate.")
        print("\n🧪 After propagation, test:")
        print("   https://investforge.io/app")
        print("   The static assets should load properly.")
        
        # Check Streamlit configuration
        check_streamlit_base_url()
        
        print("\n📋 If static assets still don't load:")
        print("1. Update your Streamlit Dockerfile with:")
        print('   CMD ["streamlit", "run", "app.py", "--server.baseUrlPath=/app"]')
        print("2. Redeploy your ECS service")
        print("3. Wait for CloudFront propagation (5-10 minutes)")
        
    else:
        print("\n❌ Failed to update CloudFront configuration")

if __name__ == "__main__":
    main()