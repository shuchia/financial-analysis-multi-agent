"""
Authentication handlers for user signup, login, and token management.
Enhanced with rate limiting, account lockout, and security features.
"""

import json
import os
import logging
from typing import Dict, Any
from datetime import datetime
from pydantic import ValidationError

from utils.response import (
    success_response, error_response, validation_error_response,
    unauthorized_response, server_error_response
)
from utils.database import db
from utils.auth import jwt_manager, password_manager, extract_token_from_event
from utils.rate_limiter import rate_limit, get_ip_identifier, AUTH_RATE_LIMIT
from utils.account_security import account_security, check_password_complexity, is_password_compromised
from models.user import User, UserSignup, UserLogin

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@rate_limit(max_requests=10, window_seconds=3600, identifier_func=get_ip_identifier)
def signup(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle user signup with rate limiting."""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate input
        try:
            signup_data = UserSignup(**body)
        except ValidationError as e:
            return validation_error_response(e.errors())
        
        # Check if user already exists
        existing_user = db.get_user_by_email(signup_data.email)
        if existing_user:
            return error_response(
                message="User with this email already exists",
                status_code=409,
                error_code="USER_EXISTS"
            )
        
        # Hash password
        password_hash = password_manager.hash_password(signup_data.password)
        
        # Create new user
        user = User.create_new(
            email=signup_data.email,
            password_hash=password_hash,
            first_name=signup_data.first_name,
            last_name=signup_data.last_name,
            plan=signup_data.plan,
            referral_source=signup_data.referral_source
        )
        
        # Save to database
        if not db.create_user(user.to_dict()):
            return server_error_response("Failed to create user")
        
        # Create tokens
        access_token = jwt_manager.create_access_token(
            user.user_id, 
            user.to_public_dict()
        )
        refresh_token = jwt_manager.create_refresh_token(user.user_id)
        
        # Track signup event
        from handlers.analytics import track_signup_event
        track_signup_event(user.user_id, signup_data.plan, signup_data.referral_source)
        
        return success_response(
            data={
                "user": user.to_public_dict(),
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer"
            },
            message="Account created successfully",
            status_code=201
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Signup error: {str(e)}")
        return server_error_response("Internal server error")


@rate_limit(**AUTH_RATE_LIMIT, identifier_func=get_ip_identifier)
def login(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle user login with enhanced security."""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate input
        try:
            login_data = UserLogin(**body)
        except ValidationError as e:
            return validation_error_response(e.errors())
        
        # Get IP address for security logging
        ip_address = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
        user_agent = event.get('requestContext', {}).get('identity', {}).get('userAgent', 'unknown')
        
        # Check account lockout
        is_locked, lock_reason = account_security.check_account_lockout(login_data.email)
        if is_locked:
            logger.warning(f"Login attempt on locked account: {login_data.email} from {ip_address}")
            return error_response(lock_reason, 423)  # 423 = Locked
        
        # Get user by email
        user_data = db.get_user_by_email(login_data.email)
        if not user_data:
            # Record failed attempt even for non-existent users to prevent enumeration
            account_security.record_failed_attempt(login_data.email, ip_address, user_agent)
            return unauthorized_response("Invalid email or password")
        
        user = User(user_data)
        
        # Check if account is suspended
        if user_data.get('status') == 'suspended':
            logger.warning(f"Login attempt on suspended account: {login_data.email}")
            return error_response("Account is suspended", 403)
        
        # Verify password
        if not password_manager.verify_password(login_data.password, user.password_hash):
            # Record failed attempt
            account_locked, security_message = account_security.record_failed_attempt(
                login_data.email, ip_address, user_agent
            )
            
            logger.warning(f"Failed login attempt for {login_data.email} from {ip_address}")
            
            if account_locked:
                return error_response(security_message, 423)  # Account locked
            else:
                return unauthorized_response(security_message)
        
        # Successful login - clear any failed attempts
        account_security.clear_failed_attempts(login_data.email)
        
        # Update last login
        user.update_login_time()
        db.update_user(user.user_id, {
            'last_login': user.last_login,
            'updated_at': user.updated_at,
            'last_login_ip': ip_address
        })
        
        # Create tokens
        access_token = jwt_manager.create_access_token(
            user.user_id, 
            user.to_public_dict()
        )
        refresh_token = jwt_manager.create_refresh_token(user.user_id)
        
        # Track login event
        from handlers.analytics import track_login_event
        track_login_event(user.user_id)
        
        logger.info(f"Successful login for {login_data.email} from {ip_address}")
        
        return success_response(
            data={
                "user": user.to_public_dict(),
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer"
            },
            message="Login successful"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return server_error_response("Internal server error")


def refresh_token(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle token refresh."""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        refresh_token = body.get('refresh_token')
        
        if not refresh_token:
            return error_response("Refresh token is required", 400)
        
        # Verify refresh token
        payload = jwt_manager.verify_token(refresh_token)
        if not payload or payload.get('type') != 'refresh':
            return unauthorized_response("Invalid or expired refresh token")
        
        user_id = payload.get('user_id')
        if not user_id:
            return unauthorized_response("Invalid token payload")
        
        # Get user data
        user_data = db.get_user(user_id)
        if not user_data:
            return unauthorized_response("User not found")
        
        user = User(user_data)
        
        # Create new access token
        access_token = jwt_manager.create_access_token(
            user.user_id, 
            user.to_public_dict()
        )
        
        return success_response(
            data={
                "access_token": access_token,
                "token_type": "Bearer"
            },
            message="Token refreshed successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Token refresh error: {str(e)}")
        return server_error_response("Internal server error")


def verify_email(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle email verification."""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        token = body.get('token')
        
        if not token:
            return error_response("Verification token is required", 400)
        
        # Verify token (in production, this would be a different type of token)
        payload = jwt_manager.verify_token(token)
        if not payload:
            return error_response("Invalid or expired verification token", 400)
        
        user_id = payload.get('user_id')
        if not user_id:
            return error_response("Invalid token payload", 400)
        
        # Update user email verification status
        success = db.update_user(user_id, {
            'email_verified': True,
            'updated_at': datetime.utcnow().isoformat()
        })
        
        if not success:
            return server_error_response("Failed to verify email")
        
        return success_response(
            message="Email verified successfully"
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Email verification error: {str(e)}")
        return server_error_response("Internal server error")


def authorizer(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda authorizer for API Gateway."""
    try:
        # Extract token from event
        token = extract_token_from_event(event)
        if not token:
            raise Exception("No token provided")
        
        # Verify token
        user_info = jwt_manager.extract_user_from_token(token)
        if not user_info:
            raise Exception("Invalid token")
        
        # Build policy
        policy = {
            "principalId": user_info['user_id'],
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Allow",
                        "Resource": event['methodArn']
                    }
                ]
            },
            "context": user_info
        }
        
        return policy
        
    except Exception as e:
        print(f"Authorization error: {str(e)}")
        # Return deny policy
        return {
            "principalId": "user",
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Deny",
                        "Resource": event['methodArn']
                    }
                ]
            }
        }