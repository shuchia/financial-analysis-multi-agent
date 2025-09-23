"""
User data models and validation.
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class UserSignup(BaseModel):
    """User signup request model."""
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    plan: str = 'free'
    referral_source: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    @validator('plan')
    def validate_plan(cls, v):
        valid_plans = ['free', 'growth', 'pro']
        if v not in valid_plans:
            raise ValueError(f'Plan must be one of: {valid_plans}')
        return v


class UserLogin(BaseModel):
    """User login request model."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """User update request model."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    plan: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    
    @validator('plan')
    def validate_plan(cls, v):
        if v is not None:
            valid_plans = ['free', 'growth', 'pro']
            if v not in valid_plans:
                raise ValueError(f'Plan must be one of: {valid_plans}')
        return v


class User:
    """User data class with utility methods."""
    
    def __init__(self, data: Dict[str, Any]):
        self.user_id = data.get('user_id')
        self.email = data.get('email')
        self.first_name = data.get('first_name')
        self.last_name = data.get('last_name')
        self.plan = data.get('plan', 'free')
        self.password_hash = data.get('password_hash')
        self.email_verified = data.get('email_verified', False)
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
        self.last_login = data.get('last_login')
        self.stripe_customer_id = data.get('stripe_customer_id')
        self.preferences = data.get('preferences', {})
        self.referral_source = data.get('referral_source')
    
    @classmethod
    def create_new(
        cls, 
        email: str, 
        password_hash: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        plan: str = 'free',
        referral_source: Optional[str] = None
    ) -> 'User':
        """Create a new user instance."""
        now = datetime.utcnow().isoformat()
        user_id = str(uuid.uuid4())
        
        data = {
            'user_id': user_id,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'plan': plan,
            'password_hash': password_hash,
            'email_verified': False,
            'created_at': now,
            'updated_at': now,
            'last_login': None,
            'stripe_customer_id': None,
            'preferences': {},
            'referral_source': referral_source
        }
        
        return cls(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'plan': self.plan,
            'password_hash': self.password_hash,
            'email_verified': self.email_verified,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'last_login': self.last_login,
            'stripe_customer_id': self.stripe_customer_id,
            'preferences': self.preferences,
            'referral_source': self.referral_source
        }
    
    def to_public_dict(self) -> Dict[str, Any]:
        """Convert user to public dictionary (without sensitive data)."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'plan': self.plan,
            'email_verified': self.email_verified,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'preferences': self.preferences
        }
    
    def update_login_time(self):
        """Update last login time."""
        self.last_login = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
    
    def update_fields(self, updates: Dict[str, Any]):
        """Update user fields."""
        for key, value in updates.items():
            if hasattr(self, key) and key not in ['user_id', 'email', 'created_at', 'password_hash']:
                setattr(self, key, value)
        
        self.updated_at = datetime.utcnow().isoformat()
    
    def get_plan_limits(self) -> Dict[str, int]:
        """Get usage limits for user's plan."""
        limits = {
            'free': {
                'analyses_per_month': 5,
                'backtests_per_month': 2,
                'portfolio_optimizations_per_month': 1,
                'api_calls_per_day': 0
            },
            'growth': {
                'analyses_per_month': -1,  # Unlimited
                'backtests_per_month': -1,
                'portfolio_optimizations_per_month': -1,
                'api_calls_per_day': 100
            },
            'pro': {
                'analyses_per_month': -1,
                'backtests_per_month': -1,
                'portfolio_optimizations_per_month': -1,
                'api_calls_per_day': 1000
            }
        }
        
        return limits.get(self.plan, limits['free'])