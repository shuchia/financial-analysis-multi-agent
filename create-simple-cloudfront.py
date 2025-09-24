#!/usr/bin/env python3
"""
Create a simple CloudFront distribution manually for InvestForge unified architecture.
"""

import boto3
import json
import time
import os
from datetime import datetime

def create_s3_bucket_for_landing():
    """Create S3 bucket for landing page."""
    s3 = boto3.client('s3')
    bucket_name = 'investforge-simple-landing'
    
    try:
        # Create bucket
        s3.create_bucket(Bucket=bucket_name)
        print(f"✅ Created S3 bucket: {bucket_name}")
        
        # Enable website hosting
        s3.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                'IndexDocument': {'Suffix': 'index.html'},
                'ErrorDocument': {'Key': 'error.html'}
            }
        )
        
        # Upload landing page
        s3.upload_file('landing/index.html', bucket_name, 'index.html', 
                      ExtraArgs={'ContentType': 'text/html'})
        
        if os.path.exists('landing/css/styles.css'):
            s3.upload_file('landing/css/styles.css', bucket_name, 'css/styles.css',
                          ExtraArgs={'ContentType': 'text/css'})
        
        if os.path.exists('landing/js/main.js'):
            s3.upload_file('landing/js/main.js', bucket_name, 'js/main.js',
                          ExtraArgs={'ContentType': 'application/javascript'})
        
        print(f"✅ Uploaded landing page content")
        return bucket_name
        
    except Exception as e:
        print(f"❌ S3 bucket creation failed: {e}")
        return None

def create_cloudfront_distribution(bucket_name, alb_domain):
    """Create CloudFront distribution."""
    cloudfront = boto3.client('cloudfront')
    
    # Get regional domain name for S3
    s3_domain = f"{bucket_name}.s3.us-east-1.amazonaws.com"
    
    distribution_config = {
        'CallerReference': f'investforge-{int(time.time())}',
        'Aliases': {
            'Quantity': 1,
            'Items': ['investforge.io']
        },
        'DefaultRootObject': 'index.html',
        'Comment': 'InvestForge unified architecture',
        'Enabled': True,
        'Origins': {
            'Quantity': 2,
            'Items': [
                {
                    'Id': 'S3-investforge-landing',
                    'DomainName': s3_domain,
                    'CustomOriginConfig': {
                        'HTTPPort': 80,
                        'HTTPSPort': 443,
                        'OriginProtocolPolicy': 'http-only'
                    }
                },
                {
                    'Id': 'ALB-investforge',
                    'DomainName': alb_domain,
                    'CustomOriginConfig': {
                        'HTTPPort': 80,
                        'HTTPSPort': 443,
                        'OriginProtocolPolicy': 'https-only'
                    }
                }
            ]
        },
        'DefaultCacheBehavior': {
            'TargetOriginId': 'S3-investforge-landing',
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
                'Cookies': {'Forward': 'none'}
            },
            'TrustedSigners': {
                'Enabled': False,
                'Quantity': 0
            },
            'MinTTL': 0,
            'DefaultTTL': 86400,
            'MaxTTL': 31536000,
            'Compress': True
        },
        'CacheBehaviors': {
            'Quantity': 2,
            'Items': [
                {
                    'PathPattern': '/app*',
                    'TargetOriginId': 'ALB-investforge',
                    'ViewerProtocolPolicy': 'redirect-to-https',
                    'AllowedMethods': {
                        'Quantity': 7,
                        'Items': ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT'],
                        'CachedMethods': {
                            'Quantity': 2,
                            'Items': ['GET', 'HEAD']
                        }
                    },
                    'ForwardedValues': {
                        'QueryString': True,
                        'Cookies': {'Forward': 'all'},
                        'Headers': {
                            'Quantity': 4,
                            'Items': ['Authorization', 'Content-Type', 'Host', 'Origin']
                        }
                    },
                    'TrustedSigners': {
                        'Enabled': False,
                        'Quantity': 0
                    },
                    'MinTTL': 0,
                    'DefaultTTL': 0,
                    'MaxTTL': 0,
                    'Compress': True
                },
                {
                    'PathPattern': '/api*',
                    'TargetOriginId': 'ALB-investforge',
                    'ViewerProtocolPolicy': 'redirect-to-https',
                    'AllowedMethods': {
                        'Quantity': 7,
                        'Items': ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT'],
                        'CachedMethods': {
                            'Quantity': 2,
                            'Items': ['GET', 'HEAD']
                        }
                    },
                    'ForwardedValues': {
                        'QueryString': True,
                        'Cookies': {'Forward': 'all'},
                        'Headers': {
                            'Quantity': 4,
                            'Items': ['Authorization', 'Content-Type', 'Host', 'Origin']
                        }
                    },
                    'TrustedSigners': {
                        'Enabled': False,
                        'Quantity': 0
                    },
                    'MinTTL': 0,
                    'DefaultTTL': 0,
                    'MaxTTL': 0,
                    'Compress': True
                }
            ]
        },
        'ViewerCertificate': {
            'ACMCertificateArn': 'arn:aws:acm:us-east-1:453636587892:certificate/aed2413b-1d49-41bb-9291-d9acc4c0818e',
            'SSLSupportMethod': 'sni-only',
            'MinimumProtocolVersion': 'TLSv1.2_2021'
        },
        'WebACLId': '',
        'HttpVersion': 'http2',
        'IsIPV6Enabled': True,
        'PriceClass': 'PriceClass_100'
    }
    
    try:
        response = cloudfront.create_distribution(DistributionConfig=distribution_config)
        distribution_id = response['Distribution']['Id']
        domain_name = response['Distribution']['DomainName']
        
        print(f"✅ Created CloudFront distribution: {distribution_id}")
        print(f"   Domain: {domain_name}")
        
        return distribution_id, domain_name
        
    except Exception as e:
        print(f"❌ CloudFront creation failed: {e}")
        return None, None

def update_route53(cloudfront_domain):
    """Update Route 53 to point to CloudFront."""
    route53 = boto3.client('route53')
    
    change_batch = {
        'Changes': [
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': 'investforge.io',
                    'Type': 'A',
                    'AliasTarget': {
                        'DNSName': cloudfront_domain,
                        'HostedZoneId': 'Z2FDTNDATAQYW2',  # CloudFront hosted zone
                        'EvaluateTargetHealth': False
                    }
                }
            }
        ]
    }
    
    try:
        response = route53.change_resource_record_sets(
            HostedZoneId='Z08211553JYQ7LH5RQ3VV',
            ChangeBatch=change_batch
        )
        
        change_id = response['ChangeInfo']['Id']
        print(f"✅ Route 53 updated: {change_id}")
        
        # Wait for change to propagate
        print("⏳ Waiting for Route 53 propagation...")
        route53.get_waiter('resource_record_sets_changed').wait(Id=change_id)
        print("✅ Route 53 propagation completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Route 53 update failed: {e}")
        return False

def main():
    """Main function."""
    print("🚀 Creating Simple CloudFront Distribution for InvestForge")
    print("=" * 60)
    
    import os
    os.chdir('/Users/shuchiagarwal/Documents/Financial-Analysis--Multi-Agent-Open-Source-LLM')
    
    alb_domain = 'financial-analysis-alb-161240.us-east-1.elb.amazonaws.com'
    
    # Step 1: Create S3 bucket
    print("\n1️⃣ Creating S3 bucket for landing page...")
    bucket_name = create_s3_bucket_for_landing()
    
    if not bucket_name:
        print("❌ Failed to create S3 bucket")
        return
    
    # Step 2: Create CloudFront distribution
    print("\n2️⃣ Creating CloudFront distribution...")
    distribution_id, cloudfront_domain = create_cloudfront_distribution(bucket_name, alb_domain)
    
    if not distribution_id:
        print("❌ Failed to create CloudFront distribution")
        return
    
    # Step 3: Update Route 53
    print("\n3️⃣ Updating Route 53...")
    if update_route53(cloudfront_domain):
        print("\n🎉 CloudFront deployment completed!")
        print(f"   CloudFront ID: {distribution_id}")
        print(f"   CloudFront Domain: {cloudfront_domain}")
        print(f"   S3 Bucket: {bucket_name}")
        print("\n📋 Architecture Status:")
        print("✅ investforge.io/ → S3 (landing page)")
        print("✅ investforge.io/app* → ALB → ECS (Streamlit)")
        print("✅ investforge.io/api* → ALB → Lambda")
        print("\n⏳ CloudFront deployment takes 10-15 minutes to fully propagate.")
        print("🧪 Test after propagation: https://investforge.io/")
    else:
        print("❌ Failed to update Route 53")

if __name__ == "__main__":
    main()