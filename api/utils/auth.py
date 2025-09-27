"""
Authentication utilities for JWT handling.
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class JWTManager:
    """JWT token management."""
    
    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
        self.algorithm = 'HS256'
        self.access_token_expires = timedelta(hours=24)
        self.refresh_token_expires = timedelta(days=30)
        self.verification_token_expires = timedelta(hours=24)
    
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
    
    def create_verification_token(self, user_id: str) -> str:
        """Create an email verification token."""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + self.verification_token_expires,
            'iat': datetime.utcnow(),
            'type': 'verification'
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
    
    def verify_verification_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify an email verification token."""
        payload = self.verify_token(token)
        
        if not payload or payload.get('type') != 'verification':
            return None
        
        return payload


class PasswordManager:
    """Password hashing and verification."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def extract_token_from_event(event: Dict[str, Any]) -> Optional[str]:
    """Extract JWT token from Lambda event."""
    # Try Authorization header first
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization') or headers.get('authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header[7:]
    
    # Try query parameters
    query_params = event.get('queryStringParameters', {}) or {}
    token = query_params.get('token')
    
    if token:
        return token
    
    return None


def get_user_from_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract user information from Lambda authorizer context."""
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer', {})
    
    if 'user_id' in authorizer:
        return {
            'user_id': authorizer['user_id'],
            'user_data': authorizer.get('user_data', {}),
            'exp': authorizer.get('exp'),
            'iat': authorizer.get('iat')
        }
    
    return None


def generate_tokens(user_id: str, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Generate access and refresh tokens for a user."""
    if user_data is None:
        # If no user data provided, get from database
        from utils.database import db
        user_record = db.get_user(user_id)
        if user_record:
            from models.user import User
            user = User(user_record)
            user_data = user.to_public_dict()
        else:
            user_data = {}
    
    access_token = jwt_manager.create_access_token(user_id, user_data)
    refresh_token = jwt_manager.create_refresh_token(user_id)
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }


def hash_password(password: str) -> str:
    """Helper function for password hashing."""
    return password_manager.hash_password(password)


def verify_password(password: str, hashed: str) -> bool:
    """Helper function for password verification."""
    return password_manager.verify_password(password, hashed)


# Global instances
jwt_manager = JWTManager()
password_manager = PasswordManager()