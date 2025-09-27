"""
Rate limiting utilities for API endpoints.
Uses Redis for distributed rate limiting across Lambda functions.
"""

import json
import time
import logging
from functools import wraps
from typing import Dict, Any, Optional, Callable
import redis
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class RateLimiter:
    """
    Token bucket rate limiter using Redis for distributed rate limiting.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize rate limiter with Redis client."""
        self.redis_client = redis_client or self._get_redis_client()
        self.enabled = self.redis_client is not None
    
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client from environment configuration."""
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            logger.warning("REDIS_URL not configured, rate limiting disabled")
            return None
        
        try:
            client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            client.ping()
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            return None
    
    def check_rate_limit(
        self,
        identifier: str,
        max_requests: int = 60,
        window_seconds: int = 60,
        burst_size: Optional[int] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limit using token bucket algorithm.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            burst_size: Maximum burst size (defaults to max_requests)
        
        Returns:
            Tuple of (allowed, metadata)
        """
        if not self.enabled:
            return True, {'rate_limit_enabled': False}
        
        burst_size = burst_size or max_requests
        key = f"rate_limit:{identifier}"
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Get current token count and last refill time
            pipe.hget(key, 'tokens')
            pipe.hget(key, 'last_refill')
            results = pipe.execute()
            
            current_tokens = float(results[0] or burst_size)
            last_refill = float(results[1] or time.time())
            
            # Calculate tokens to add based on time elapsed
            current_time = time.time()
            time_elapsed = current_time - last_refill
            refill_rate = max_requests / window_seconds
            tokens_to_add = time_elapsed * refill_rate
            
            # Update token count (capped at burst_size)
            new_tokens = min(burst_size, current_tokens + tokens_to_add)
            
            # Check if request can be allowed
            if new_tokens >= 1:
                # Consume one token
                new_tokens -= 1
                
                # Update Redis atomically
                pipe = self.redis_client.pipeline()
                pipe.hset(key, 'tokens', new_tokens)
                pipe.hset(key, 'last_refill', current_time)
                pipe.expire(key, window_seconds * 2)  # Expire after 2x window
                pipe.execute()
                
                metadata = {
                    'rate_limit_enabled': True,
                    'tokens_remaining': int(new_tokens),
                    'max_requests': max_requests,
                    'window_seconds': window_seconds,
                    'retry_after': None
                }
                
                return True, metadata
            else:
                # Calculate retry after
                tokens_needed = 1 - new_tokens
                retry_after = int(tokens_needed / refill_rate) + 1
                
                metadata = {
                    'rate_limit_enabled': True,
                    'tokens_remaining': 0,
                    'max_requests': max_requests,
                    'window_seconds': window_seconds,
                    'retry_after': retry_after
                }
                
                return False, metadata
                
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            # Fail open - allow request if Redis fails
            return True, {'rate_limit_enabled': False, 'error': str(e)}
    
    def reset_rate_limit(self, identifier: str) -> bool:
        """Reset rate limit for an identifier."""
        if not self.enabled:
            return False
        
        try:
            key = f"rate_limit:{identifier}"
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {str(e)}")
            return False


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(
    max_requests: int = 60,
    window_seconds: int = 60,
    identifier_func: Optional[Callable] = None,
    burst_size: Optional[int] = None
):
    """
    Decorator for rate limiting Lambda handlers.
    
    Args:
        max_requests: Maximum requests in window
        window_seconds: Time window in seconds
        identifier_func: Function to extract identifier from event
        burst_size: Maximum burst size
    """
    def decorator(func):
        @wraps(func)
        def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
            # Extract identifier
            if identifier_func:
                identifier = identifier_func(event)
            else:
                # Default: use source IP
                identifier = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
            
            # Check rate limit
            allowed, metadata = rate_limiter.check_rate_limit(
                identifier,
                max_requests=max_requests,
                window_seconds=window_seconds,
                burst_size=burst_size
            )
            
            if not allowed:
                return {
                    'statusCode': 429,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Retry-After': str(metadata.get('retry_after', 60)),
                        'X-RateLimit-Limit': str(metadata.get('max_requests', max_requests)),
                        'X-RateLimit-Remaining': '0',
                        'X-RateLimit-Reset': str(int(time.time() + metadata.get('retry_after', 60)))
                    },
                    'body': json.dumps({
                        'success': False,
                        'message': 'Too many requests. Please try again later.',
                        'retry_after': metadata.get('retry_after', 60)
                    })
                }
            
            # Add rate limit headers to response
            response = func(event, context)
            
            # Add rate limit headers
            if isinstance(response, dict) and 'headers' in response:
                response['headers'].update({
                    'X-RateLimit-Limit': str(metadata.get('max_requests', max_requests)),
                    'X-RateLimit-Remaining': str(metadata.get('tokens_remaining', 0)),
                    'X-RateLimit-Reset': str(int(time.time() + window_seconds))
                })
            
            return response
            
        return wrapper
    return decorator


def get_user_identifier(event: Dict[str, Any]) -> str:
    """Extract user identifier from authenticated request."""
    # Try to get user ID from authorizer
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('user_id')
    if user_id:
        return f"user:{user_id}"
    
    # Fall back to IP
    ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
    return f"ip:{ip}"


def get_ip_identifier(event: Dict[str, Any]) -> str:
    """Extract IP identifier from request."""
    ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
    return f"ip:{ip}"


# Common rate limit configurations
STRICT_RATE_LIMIT = {
    'max_requests': 10,
    'window_seconds': 60,
    'burst_size': 5
}

STANDARD_RATE_LIMIT = {
    'max_requests': 60,
    'window_seconds': 60,
    'burst_size': 20
}

RELAXED_RATE_LIMIT = {
    'max_requests': 300,
    'window_seconds': 60,
    'burst_size': 50
}

AUTH_RATE_LIMIT = {
    'max_requests': 5,
    'window_seconds': 300,  # 5 minutes
    'burst_size': 3
}