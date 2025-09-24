#!/usr/bin/env python3
"""
Check current ALB configuration and show what needs to be updated for InvestForge routing.
"""

import boto3
import json
from typing import Dict, List, Any

def get_albs() -> List[Dict[str, Any]]:
    """Get all Application Load Balancers."""
    elbv2 = boto3.client('elbv2')
    response = elbv2.describe_load_balancers()
    
    albs = [lb for lb in response['LoadBalancers'] if lb['Type'] == 'application']
    return albs

def get_listeners(alb_arn: str) -> List[Dict[str, Any]]:
    """Get listeners for an ALB."""
    elbv2 = boto3.client('elbv2')
    response = elbv2.describe_listeners(LoadBalancerArn=alb_arn)
    return response['Listeners']

def get_listener_rules(listener_arn: str) -> List[Dict[str, Any]]:
    """Get rules for a listener."""
    elbv2 = boto3.client('elbv2')
    response = elbv2.describe_rules(ListenerArn=listener_arn)
    return response['Rules']

def get_target_groups() -> List[Dict[str, Any]]:
    """Get all target groups."""
    elbv2 = boto3.client('elbv2')
    response = elbv2.describe_target_groups()
    return response['TargetGroups']

def get_lambda_functions() -> List[Dict[str, Any]]:
    """Get InvestForge Lambda functions."""
    lambda_client = boto3.client('lambda')
    functions = []
    
    investforge_functions = [
        'investforge-api-prod-health',
        'investforge-api-prod-signup',
        'investforge-api-prod-login', 
        'investforge-api-prod-join_waitlist',
        'investforge-api-prod-track_event',
        'investforge-api-prod-get_user'
    ]
    
    for func_name in investforge_functions:
        try:
            response = lambda_client.get_function(FunctionName=func_name)
            functions.append({
                'name': func_name,
                'arn': response['Configuration']['FunctionArn'],
                'state': response['Configuration']['State'],
                'runtime': response['Configuration']['Runtime']
            })
        except:
            functions.append({
                'name': func_name,
                'arn': None,
                'state': 'Not Found',
                'runtime': None
            })
    
    return functions

def find_investforge_alb(albs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Find InvestForge ALB."""
    # Look for ALB with investforge in name
    for alb in albs:
        if 'investforge' in alb['LoadBalancerName'].lower():
            return alb
    
    # If not found, return the first ALB (user can choose)
    if albs:
        return albs[0]
    
    return None

def analyze_current_setup():
    """Analyze current ALB setup."""
    print("🔍 InvestForge ALB Configuration Analysis")
    print("=" * 50)
    print()
    
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        region = boto3.Session().region_name or 'us-east-1'
        print(f"AWS Account: {identity['Account']}")
        print(f"Region: {region}")
        print()
    except Exception as e:
        print(f"❌ AWS credentials error: {e}")
        return
    
    # Get ALBs
    print("📋 Available Application Load Balancers:")
    albs = get_albs()
    
    if not albs:
        print("❌ No Application Load Balancers found")
        return
    
    for i, alb in enumerate(albs, 1):
        print(f"  {i}. {alb['LoadBalancerName']}")
        print(f"     ARN: {alb['LoadBalancerArn']}")
        print(f"     DNS: {alb['DNSName']}")
        print(f"     State: {alb['State']['Code']}")
        print(f"     VPC: {alb['VpcId']}")
        print()
    
    # Focus on InvestForge ALB
    investforge_alb = find_investforge_alb(albs)
    
    if not investforge_alb:
        print("⚠️  No ALB with 'investforge' in name found")
        print("Using first ALB for analysis...")
        investforge_alb = albs[0]
    
    print(f"🎯 Analyzing ALB: {investforge_alb['LoadBalancerName']}")
    print(f"ARN: {investforge_alb['LoadBalancerArn']}")
    print()
    
    # Get listeners
    print("🔊 ALB Listeners:")
    listeners = get_listeners(investforge_alb['LoadBalancerArn'])
    
    for listener in listeners:
        print(f"  Port {listener['Port']} ({listener['Protocol']})")
        print(f"    ARN: {listener['ListenerArn']}")
        
        if listener.get('Certificates'):
            print(f"    SSL Certificate: {listener['Certificates'][0]['CertificateArn']}")
        
        # Get rules for this listener
        rules = get_listener_rules(listener['ListenerArn'])
        print(f"    Rules: {len(rules)} total")
        
        for rule in rules:
            if rule['Priority'] == 'default':
                print(f"      Default: -> {rule['Actions'][0].get('TargetGroupArn', 'N/A')}")
            else:
                conditions = rule.get('Conditions', [])
                condition_str = ", ".join([f"{c['Field']}={c.get('Values', ['N/A'])[0]}" for c in conditions])
                target = rule['Actions'][0].get('TargetGroupArn', 'N/A')
                print(f"      Priority {rule['Priority']}: {condition_str} -> {target}")
        print()
    
    # Get target groups
    print("🎯 Target Groups:")
    target_groups = get_target_groups()
    
    # Filter for InvestForge or Lambda target groups
    relevant_tgs = []
    for tg in target_groups:
        if ('investforge' in tg['TargetGroupName'].lower() or 
            'lambda' in tg['TargetGroupName'].lower() or
            tg['TargetType'] == 'lambda'):
            relevant_tgs.append(tg)
    
    if relevant_tgs:
        for tg in relevant_tgs:
            print(f"  {tg['TargetGroupName']} ({tg['TargetType']})")
            print(f"    ARN: {tg['TargetGroupArn']}")
            print(f"    Protocol: {tg.get('Protocol', 'N/A')}:{tg.get('Port', 'N/A')}")
            print(f"    VPC: {tg.get('VpcId', 'N/A')}")
    else:
        print("  ❌ No Lambda target groups found")
    
    print()
    
    # Check Lambda functions
    print("⚡ InvestForge Lambda Functions:")
    lambda_functions = get_lambda_functions()
    
    for func in lambda_functions:
        status = "✅" if func['state'] == 'Active' else "❌"
        print(f"  {status} {func['name']}: {func['state']}")
        if func['arn']:
            print(f"      ARN: {func['arn']}")
    
    print()
    
    # Analysis and recommendations
    print("📊 Configuration Analysis:")
    print("-" * 30)
    
    # Check if Lambda target groups exist
    lambda_tgs = [tg for tg in relevant_tgs if tg['TargetType'] == 'lambda']
    if lambda_tgs:
        print(f"✅ Found {len(lambda_tgs)} Lambda target groups")
    else:
        print("❌ No Lambda target groups found - need to create them")
    
    # Check if path-based rules exist
    api_rules = []
    for listener in listeners:
        rules = get_listener_rules(listener['ListenerArn'])
        for rule in rules:
            conditions = rule.get('Conditions', [])
            for condition in conditions:
                if (condition['Field'] == 'path-pattern' and 
                    any('/api/' in value for value in condition.get('Values', []))):
                    api_rules.append(rule)
    
    if api_rules:
        print(f"✅ Found {len(api_rules)} API path rules")
    else:
        print("❌ No /api/* path rules found - need to create them")
    
    # Check active Lambda functions
    active_lambdas = [f for f in lambda_functions if f['state'] == 'Active']
    if len(active_lambdas) >= 4:
        print(f"✅ Found {len(active_lambdas)} active Lambda functions")
    else:
        print(f"⚠️  Only {len(active_lambdas)} active Lambda functions (expected 6+)")
    
    print()
    
    # Recommendations
    print("🚀 Next Steps:")
    print("-" * 15)
    
    if not lambda_tgs:
        print("1. Run: ./configure-alb-routing.sh")
        print("   This will create Lambda target groups and configure routing")
    else:
        print("1. ✅ Lambda target groups exist")
    
    if not api_rules:
        print("2. Configure path-based routing rules for /api/* paths")
    else:
        print("2. ✅ API path rules configured")
    
    if len(active_lambdas) < 4:
        print("3. Deploy missing Lambda functions:")
        for func in lambda_functions:
            if func['state'] != 'Active':
                print(f"   - {func['name']}")
        print("   Run: ./deploy-existing-infra.sh")
    else:
        print("3. ✅ Lambda functions deployed")
    
    print()
    print("🧪 Test Configuration:")
    if investforge_alb:
        alb_dns = investforge_alb['DNSName']
        print(f"curl https://{alb_dns}/api/health")
        print(f"curl https://{alb_dns}/app")
    
    print()
    print(f"🔧 Configure ALB Script: ./configure-alb-routing.sh")
    print(f"📊 Full Deployment: ./deploy-existing-infra.sh")

if __name__ == "__main__":
    analyze_current_setup()