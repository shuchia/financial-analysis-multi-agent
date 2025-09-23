"""
Redis client configuration for session management and caching.
"""

import os
import redis
from typing import Optional


class RedisClient:
    """Redis client singleton."""
    
    _instance: Optional[redis.Redis] = None
    
    @classmethod
    def get_instance(cls) -> redis.Redis:
        """Get Redis client instance."""
        if cls._instance is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            
            # Parse Redis URL
            if redis_url.startswith('redis://'):
                cls._instance = redis.from_url(redis_url, decode_responses=True)
            else:
                # For AWS ElastiCache or other Redis services
                host = os.getenv('REDIS_HOST', 'localhost')
                port = int(os.getenv('REDIS_PORT', 6379))
                password = os.getenv('REDIS_PASSWORD')
                
                cls._instance = redis.Redis(
                    host=host,
                    port=port,
                    password=password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
        
        return cls._instance


def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    return RedisClient.get_instance()


def test_redis_connection() -> bool:
    """Test Redis connection."""
    try:
        client = get_redis_client()
        client.ping()
        return True
    except redis.RedisError:
        return False