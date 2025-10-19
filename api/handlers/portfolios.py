"""
Portfolio management Lambda handlers for saving and retrieving portfolios.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any
import boto3
from boto3.dynamodb.conditions import Key

from utils.response import (
    success_response,
    error_response,
    validation_error_response,
    not_found_response,
    server_error_response
)


# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
portfolios_table_name = os.environ.get('DYNAMODB_TABLE_PORTFOLIOS', 'investforge-api-alb-dev-portfolios')
portfolios_table = dynamodb.Table(portfolios_table_name)


def _generate_portfolio_name(preferences: Dict[str, Any]) -> str:
    """Generate a default portfolio name from preferences."""
    risk = preferences.get('risk_profile', 'balanced').title()
    goals = preferences.get('investment_goals', ['investing'])

    # Extract primary goal and format it
    if goals and len(goals) > 0:
        primary_goal = goals[0].replace('_', ' ').title()
    else:
        primary_goal = 'Portfolio'

    year = datetime.now().year
    return f"{risk} {primary_goal} {year}"


def save_portfolio(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Save a portfolio snapshot to DynamoDB.

    POST /api/portfolio/save
    Body: {
        "user_id": "user@example.com",
        "name": "Optional custom name",
        "preferences": {...},
        "allocations": [...],
        "risk_metrics": {...},  // optional
        "optimization_results": {...},  // optional
        "tags": ["tag1", "tag2"],  // optional
        "notes": "Optional notes"  // optional
    }
    """
    try:
        # Parse request body
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            return validation_error_response({"body": "Request body is required"})

        # Validate required fields
        user_id = body.get('user_id')
        allocations = body.get('allocations')

        if not user_id:
            return validation_error_response({"user_id": "user_id is required"})

        if not allocations or not isinstance(allocations, list) or len(allocations) == 0:
            return validation_error_response({"allocations": "allocations must be a non-empty array"})

        # Generate portfolio_id
        portfolio_id = f"port_{uuid.uuid4().hex[:12]}"

        # Auto-generate name if not provided
        portfolio_name = body.get('name')
        if not portfolio_name or portfolio_name.strip() == "":
            preferences = body.get('preferences', {})
            portfolio_name = _generate_portfolio_name(preferences)

        # Create portfolio object
        portfolio = {
            'portfolio_id': portfolio_id,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'name': portfolio_name,
            'preferences': body.get('preferences', {}),
            'allocations': allocations,
            'status': 'active',
            'tags': body.get('tags', []),
            'notes': body.get('notes', '')
        }

        # Add optional fields if provided
        if body.get('risk_metrics'):
            portfolio['risk_metrics'] = body['risk_metrics']

        if body.get('optimization_results'):
            portfolio['optimization_results'] = body['optimization_results']

        # Save to DynamoDB
        portfolios_table.put_item(Item=portfolio)

        return success_response(
            data={
                'portfolio_id': portfolio_id,
                'name': portfolio_name
            },
            message='Portfolio saved successfully'
        )

    except json.JSONDecodeError as e:
        return error_response(
            message="Invalid JSON in request body",
            status_code=400,
            error_code="INVALID_JSON"
        )
    except Exception as e:
        print(f"Error saving portfolio: {str(e)}")
        return server_error_response(f"Failed to save portfolio: {str(e)}")


def get_portfolio(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Retrieve a specific portfolio by ID.

    GET /api/portfolio/{portfolio_id}
    """
    try:
        # Extract portfolio_id from path parameters
        path_parameters = event.get('pathParameters', {})
        portfolio_id = path_parameters.get('portfolio_id')

        if not portfolio_id:
            return validation_error_response({"portfolio_id": "portfolio_id is required in path"})

        # Get user_id from query parameters or headers for authorization
        # For now, we'll retrieve without authorization check
        # TODO: Add proper authorization to ensure user can only access their own portfolios

        # Query DynamoDB
        response = portfolios_table.query(
            KeyConditionExpression=Key('portfolio_id').eq(portfolio_id),
            Limit=1
        )

        items = response.get('Items', [])

        if not items:
            return not_found_response(f"Portfolio {portfolio_id} not found")

        portfolio = items[0]

        return success_response(
            data={'portfolio': portfolio},
            message='Portfolio retrieved successfully'
        )

    except Exception as e:
        print(f"Error retrieving portfolio: {str(e)}")
        return server_error_response(f"Failed to retrieve portfolio: {str(e)}")


def get_latest_portfolio(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Retrieve the most recent portfolio for a user.

    GET /api/portfolio/latest?user_id=user@example.com
    """
    try:
        # Extract user_id from query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        user_id = query_params.get('user_id')

        if not user_id:
            return validation_error_response({"user_id": "user_id is required as query parameter"})

        # Query DynamoDB using GSI UserPortfoliosByDate
        response = portfolios_table.query(
            IndexName='UserPortfoliosByDate',
            KeyConditionExpression=Key('user_id').eq(user_id),
            ScanIndexForward=False,  # Sort descending (most recent first)
            Limit=1
        )

        items = response.get('Items', [])

        if not items:
            return not_found_response(f"No portfolios found for user {user_id}")

        portfolio = items[0]

        return success_response(
            data={'portfolio': portfolio},
            message='Latest portfolio retrieved successfully'
        )

    except Exception as e:
        print(f"Error retrieving latest portfolio: {str(e)}")
        return server_error_response(f"Failed to retrieve latest portfolio: {str(e)}")
