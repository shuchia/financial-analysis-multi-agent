"""
API response utilities for consistent response formatting.
"""

import json
from typing import Any, Dict, Optional


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200
) -> Dict[str, Any]:
    """Create a success response."""
    body = {
        "success": True,
        "message": message,
        "data": data
    }
    
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": json.dumps(body, default=str)
    }


def error_response(
    message: str = "An error occurred",
    status_code: int = 400,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create an error response."""
    body = {
        "success": False,
        "message": message,
        "error_code": error_code,
        "details": details
    }
    
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": json.dumps(body, default=str)
    }


def validation_error_response(errors: Dict[str, Any]) -> Dict[str, Any]:
    """Create a validation error response."""
    return error_response(
        message="Validation failed",
        status_code=422,
        error_code="VALIDATION_ERROR",
        details={"validation_errors": errors}
    )


def unauthorized_response(message: str = "Unauthorized") -> Dict[str, Any]:
    """Create an unauthorized response."""
    return error_response(
        message=message,
        status_code=401,
        error_code="UNAUTHORIZED"
    )


def forbidden_response(message: str = "Forbidden") -> Dict[str, Any]:
    """Create a forbidden response."""
    return error_response(
        message=message,
        status_code=403,
        error_code="FORBIDDEN"
    )


def not_found_response(message: str = "Not found") -> Dict[str, Any]:
    """Create a not found response."""
    return error_response(
        message=message,
        status_code=404,
        error_code="NOT_FOUND"
    )


def server_error_response(message: str = "Internal server error") -> Dict[str, Any]:
    """Create a server error response."""
    return error_response(
        message=message,
        status_code=500,
        error_code="INTERNAL_ERROR"
    )