"""
Lambda function for retrieving a specific portfolio.
Compatible with existing Lambda infrastructure.
"""

import json
import os
import logging
from decimal import Decimal
from urllib.parse import unquote
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
    Lambda handler for getting a portfolio by ID.
    GET /api/portfolio/{portfolio_id}
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

        # Log the incoming event for debugging
        logger.info(f"Event keys: {list(event.keys())}")
        logger.info(f"Path params: {event.get('pathParameters')}")

        # Extract portfolio_id from path parameters
        path_parameters = event.get('pathParameters', {})
        portfolio_id = path_parameters.get('portfolio_id')

        # URL-decode the portfolio_id (ALB may URL-encode path parameters)
        if portfolio_id:
            portfolio_id = unquote(portfolio_id)

        logger.info(f"Extracted portfolio_id: {portfolio_id}")

        if not portfolio_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Portfolio ID is required'
                })
            }

        # Connect to DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ.get('DYNAMODB_TABLE_PORTFOLIOS', 'investforge-portfolios-simple')
        table = dynamodb.Table(table_name)

        # Query portfolio by ID
        try:
            response = table.query(
                KeyConditionExpression=Key('portfolio_id').eq(portfolio_id),
                Limit=1
            )

            items = response.get('Items', [])

            if not items:
                return {
                    'statusCode': 404,
                    'headers': headers,
                    'body': json.dumps({
                        'success': False,
                        'message': 'Portfolio not found'
                    })
                }

            portfolio = items[0]
            # Convert Decimals to float/int for JSON serialization
            portfolio = convert_decimals_to_float(portfolio)
            logger.info(f"Portfolio retrieved: {portfolio_id}")

        except Exception as e:
            logger.error(f"Error retrieving portfolio: {str(e)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Failed to retrieve portfolio'
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
        logger.error(f"Get portfolio error: {str(e)}")
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
