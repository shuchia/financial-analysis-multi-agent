"""
Lambda function for retrieving the latest portfolio for a user.
Compatible with existing Lambda infrastructure.
"""

import json
import os
import logging
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def convert_decimals_to_float(obj):
    """
    Recursively convert all Decimal values to float for JSON serialization.
    """
    if isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj

def lambda_handler(event, context):
    """
    Lambda handler for getting the latest portfolio for a user.
    GET /api/portfolio/latest?user_id=user@example.com
    """
    try:
        # CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        }

        # Handle preflight requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }

        # Extract user_id from query parameters
        query_parameters = event.get('queryStringParameters', {}) or {}
        user_id = query_parameters.get('user_id', 'demo@investforge.ai')

        if not user_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'User ID is required'
                })
            }

        # Connect to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ.get('DYNAMODB_TABLE_PORTFOLIOS', 'investforge-portfolios-simple')
        table = dynamodb.Table(table_name)

        # Query latest portfolio using GSI
        try:
            response = table.query(
                IndexName='UserPortfoliosByDate',
                KeyConditionExpression=Key('user_id').eq(user_id),
                ScanIndexForward=False,  # Sort descending (most recent first)
                Limit=1
            )

            items = response.get('Items', [])

            if not items:
                return {
                    'statusCode': 404,
                    'headers': headers,
                    'body': json.dumps({
                        'success': False,
                        'message': 'No portfolios found for this user'
                    })
                }

            portfolio = items[0]
            # Convert Decimals to float/int for JSON serialization
            portfolio = convert_decimals_to_float(portfolio)
            logger.info(f"Latest portfolio retrieved for user: {user_id}")

        except Exception as e:
            logger.error(f"Error retrieving latest portfolio: {str(e)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Failed to retrieve latest portfolio'
                })
            }

        # Return success response
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'data': {
                    'portfolio': portfolio
                }
            })
        }

    except Exception as e:
        logger.error(f"Get latest portfolio error: {str(e)}")
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
