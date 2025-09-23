"""
JWT token handling for API authentication.
"""

import jwt
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class JWTHandler:
    """Handles JWT token creation and validation."""
    
    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
        self.algorithm = 'HS256'
        self.access_token_expires = timedelta(hours=24)
        self.refresh_token_expires = timedelta(days=30)
    
    def create_access_token(self, user_id: str, user_data: Dict[str, Any]) -> str:
        """Create an access token."""
        payload = {
            'user_id': user_id,
            'user_data': user_data,
            'exp': datetime.utcnow() + self.access_token_expires,
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create a refresh token."""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + self.refresh_token_expires,
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create a new access token using a refresh token."""
        payload = self.verify_token(refresh_token)
        
        if not payload or payload.get('type') != 'refresh':
            return None
        
        user_id = payload.get('user_id')
        if not user_id:
            return None
        
        # In a real implementation, you'd fetch user_data from database
        # For now, we'll return a basic token
        user_data = {'user_id': user_id}
        
        return self.create_access_token(user_id, user_data)
    
    def extract_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract user information from a valid token."""
        payload = self.verify_token(token)
        
        if not payload or payload.get('type') != 'access':
            return None
        
        return {
            'user_id': payload.get('user_id'),
            'user_data': payload.get('user_data', {}),
            'exp': payload.get('exp'),
            'iat': payload.get('iat')
        }