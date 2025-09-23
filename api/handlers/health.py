"""
Health check endpoint for ALB.
"""

import json
from typing import Dict, Any

from utils.response import success_response


def check(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Health check endpoint for load balancer."""
    return success_response(
        data={
            "status": "healthy",
            "service": "investforge-api",
            "timestamp": context.aws_request_id if context else "local"
        },
        message="Service is healthy"
    )