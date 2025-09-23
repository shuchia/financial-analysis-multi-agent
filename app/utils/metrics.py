"""
Analytics and metrics tracking utilities.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from .redis_client import get_redis_client
from .constants import REDIS_KEYS


def track_event(event_type: str, event_data: Dict[str, Any], user_id: Optional[str] = None):
    """Track an analytics event."""
    redis_client = get_redis_client()
    
    event = {
        'event_type': event_type,
        'event_data': event_data,
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id
    }
    
    # Store in Redis with date-based key for easy aggregation
    date_key = datetime.now().strftime('%Y-%m-%d')
    analytics_key = REDIS_KEYS['analytics'].format(event_type, date_key)
    
    try:
        # Add to list of events for the day
        redis_client.lpush(analytics_key, json.dumps(event))
        
        # Set expiration for 90 days
        redis_client.expire(analytics_key, 90 * 24 * 60 * 60)
        
    except Exception:
        # Fail silently for analytics
        pass


def track_user_action(action: str, user_id: str, metadata: Optional[Dict[str, Any]] = None):
    """Track a specific user action."""
    event_data = {
        'action': action,
        'metadata': metadata or {}
    }
    
    track_event('user_action', event_data, user_id)


def track_signup(user_id: str, plan: str, referral_source: Optional[str] = None):
    """Track user signup."""
    event_data = {
        'plan': plan,
        'referral_source': referral_source
    }
    
    track_event('signup', event_data, user_id)


def track_upgrade(user_id: str, from_plan: str, to_plan: str):
    """Track plan upgrade."""
    event_data = {
        'from_plan': from_plan,
        'to_plan': to_plan
    }
    
    track_event('upgrade', event_data, user_id)


def track_analysis(user_id: str, symbol: str, analysis_type: str, duration_seconds: float):
    """Track stock analysis completion."""
    event_data = {
        'symbol': symbol,
        'analysis_type': analysis_type,
        'duration_seconds': duration_seconds
    }
    
    track_event('analysis', event_data, user_id)


def track_feature_usage(user_id: str, feature: str, metadata: Optional[Dict[str, Any]] = None):
    """Track feature usage."""
    event_data = {
        'feature': feature,
        'metadata': metadata or {}
    }
    
    track_event('feature_usage', event_data, user_id)


def get_user_analytics(user_id: str, days: int = 30) -> Dict[str, Any]:
    """Get analytics for a specific user."""
    redis_client = get_redis_client()
    analytics = {
        'total_analyses': 0,
        'features_used': set(),
        'last_active': None,
        'signup_date': None
    }
    
    # This would need more sophisticated querying in production
    # For now, return basic structure
    return analytics


def get_daily_stats(date: str) -> Dict[str, int]:
    """Get daily analytics stats."""
    redis_client = get_redis_client()
    
    stats = {
        'signups': 0,
        'analyses': 0,
        'upgrades': 0,
        'active_users': 0
    }
    
    try:
        # Get events for the day
        for event_type in ['signup', 'analysis', 'upgrade', 'user_action']:
            key = REDIS_KEYS['analytics'].format(event_type, date)
            count = redis_client.llen(key)
            if event_type in stats:
                stats[event_type + 's'] = count
        
    except Exception:
        # Return zeros on error
        pass
    
    return stats