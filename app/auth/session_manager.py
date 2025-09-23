"""
Session management using Redis for user authentication and state.
"""

import json
import redis
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import streamlit as st
from utils.redis_client import get_redis_client


class SessionManager:
    """Manages user sessions with Redis backend."""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.session_duration = timedelta(days=30)  # 30 day sessions
    
    def create_session(self, user_id: str, user_data: Dict[str, Any]) -> str:
        """Create a new user session."""
        session_id = f"session:{user_id}:{datetime.now().timestamp()}"
        
        session_data = {
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + self.session_duration).isoformat(),
            'user_data': user_data
        }
        
        # Store session in Redis with expiration
        self.redis_client.setex(
            session_id,
            int(self.session_duration.total_seconds()),
            json.dumps(session_data)
        )
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data."""
        if not session_id:
            return None
            
        try:
            session_data = self.redis_client.get(session_id)
            if session_data:
                return json.loads(session_data)
        except (redis.RedisError, json.JSONDecodeError):
            return None
        
        return None
    
    def update_session(self, session_id: str, user_data: Dict[str, Any]) -> bool:
        """Update session data."""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session['user_data'].update(user_data)
        session['updated_at'] = datetime.now().isoformat()
        
        try:
            self.redis_client.setex(
                session_id,
                int(self.session_duration.total_seconds()),
                json.dumps(session)
            )
            return True
        except redis.RedisError:
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            self.redis_client.delete(session_id)
            return True
        except redis.RedisError:
            return False
    
    def extend_session(self, session_id: str) -> bool:
        """Extend session expiration."""
        try:
            self.redis_client.expire(
                session_id,
                int(self.session_duration.total_seconds())
            )
            return True
        except redis.RedisError:
            return False
    
    def get_current_session_id(self) -> Optional[str]:
        """Get current session ID from Streamlit session state."""
        return st.session_state.get('session_id')
    
    def set_current_session_id(self, session_id: str):
        """Set current session ID in Streamlit session state."""
        st.session_state.session_id = session_id
    
    def is_authenticated(self) -> bool:
        """Check if current user is authenticated."""
        session_id = self.get_current_session_id()
        if not session_id:
            return False
        
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Check if session is expired
        expires_at = datetime.fromisoformat(session['expires_at'])
        if datetime.now() > expires_at:
            self.delete_session(session_id)
            return False
        
        # Extend session on activity
        self.extend_session(session_id)
        return True
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user data."""
        session_id = self.get_current_session_id()
        if not session_id:
            return None
        
        session = self.get_session(session_id)
        if session:
            return session.get('user_data')
        
        return None
    
    def logout(self):
        """Log out current user."""
        session_id = self.get_current_session_id()
        if session_id:
            self.delete_session(session_id)
        
        # Clear Streamlit session state
        if 'session_id' in st.session_state:
            del st.session_state.session_id
        if 'user_data' in st.session_state:
            del st.session_state.user_data