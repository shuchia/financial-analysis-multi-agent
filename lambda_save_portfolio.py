"""
Lambda function for saving portfolio snapshots.
Compatible with existing Lambda infrastructure.
"""

import json
import os
import logging
from datetime import datetime
import boto3
import uuid

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda handler for saving portfolio snapshots.
    POST /api/portfolio/save
    """
    try:
        # CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        }

        # Handle preflight requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }

        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        # Extract required fields
        user_id = body.get('user_id', 'demo@investforge.ai')
        allocations = body.get('allocations', [])
        preferences = body.get('preferences', {})

        # Basic validation
        if not allocations:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Portfolio allocations are required'
                })
            }

        # Generate portfolio ID
        portfolio_id = f"port_{uuid.uuid4().hex[:12]}"

        # Auto-generate portfolio name if not provided
        portfolio_name = body.get('name')
        if not portfolio_name:
            # Generate name from preferences: "{Risk Profile} {Primary Goal} {Year}"
            risk_profile = preferences.get('risk_tolerance', 'Balanced').title()
            primary_goal = preferences.get('investment_goals', ['Growth'])[0] if isinstance(preferences.get('investment_goals'), list) and preferences.get('investment_goals') else 'Growth'
            year = datetime.utcnow().year
            portfolio_name = f"{risk_profile} {primary_goal} {year}"

        # Create portfolio data
        portfolio = {
            'portfolio_id': portfolio_id,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'name': portfolio_name,
            'preferences': preferences,
            'allocations': allocations,
            'status': 'active',
            'tags': body.get('tags', []),
            'notes': body.get('notes', '')
        }

        # Store in DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ.get('DYNAMODB_TABLE_PORTFOLIOS', 'investforge-portfolios-simple')
        table = dynamodb.Table(table_name)

        try:
            table.put_item(Item=portfolio)
            logger.info(f"Portfolio saved successfully: {portfolio_id}")
        except Exception as e:
            logger.error(f"Error saving portfolio: {str(e)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Failed to save portfolio'
                })
            }

        # Track analytics event
        try:
            analytics_table_name = os.environ.get('DYNAMODB_TABLE_ANALYTICS', 'investforge-analytics')
            analytics_table = dynamodb.Table(analytics_table_name)

            event_data = {
                'event_id': str(uuid.uuid4()),
                'event_type': 'portfolio_saved',
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'event_data': {
                    'portfolio_id': portfolio_id,
                    'allocations_count': len(allocations)
                },
                'source': 'lambda'
            }

            analytics_table.put_item(Item=event_data)
        except Exception as e:
            logger.warning(f"Failed to track analytics event: {str(e)}")

        # Return success response
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'Portfolio saved successfully',
                'data': {
                    'portfolio_id': portfolio_id,
                    'name': portfolio_name,
                    'created_at': portfolio['created_at']
                }
            })
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        logger.error(f"Save portfolio error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Internal server error'
            })
        }
