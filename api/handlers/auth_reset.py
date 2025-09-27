"""
Password reset and email verification handlers for authentication system.
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

from utils.response import success_response, error_response, validation_error_response
from utils.database import db
from utils.auth import jwt_manager, password_manager
from utils.email import send_password_reset_email, send_verification_email
from utils.account_security import check_password_complexity, is_password_compromised
from utils.rate_limiter import rate_limit, get_ip_identifier
from models.user import User

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@rate_limit(max_requests=3, window_seconds=300, identifier_func=get_ip_identifier)
def request_password_reset(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Request password reset email.
    Rate limited to prevent abuse.
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').strip().lower()
        
        if not email:
            return error_response("Email is required", 400)
        
        # Get user by email (but don't reveal if user exists)
        user_data = db.get_user_by_email(email)
        
        # Always return success to prevent email enumeration
        # But only send email if user actually exists
        if user_data and user_data.get('status') == 'active':
            user = User(user_data)
            
            # Generate reset token (valid for 1 hour)
            reset_token = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            # Store reset token in database
            reset_data = {
                'user_id': user.user_id,
                'reset_token': reset_token,
                'expires_at': expires_at.isoformat(),
                'created_at': datetime.utcnow().isoformat(),
                'used': False
            }
            
            if db.create_password_reset(reset_data):
                # Send reset email
                try:
                    send_password_reset_email(
                        email=email,
                        reset_token=reset_token,
                        user_name=user.first_name or 'User'
                    )
                    logger.info(f"Password reset email sent to {email}")
                except Exception as e:
                    logger.error(f"Failed to send reset email: {str(e)}")
                    return error_response("Failed to send reset email", 500)
            else:
                logger.error(f"Failed to store reset token for {email}")
                return error_response("Failed to process reset request", 500)
        else:
            logger.info(f"Password reset requested for non-existent/inactive user: {email}")
        
        # Always return success message
        return success_response(
            message="If an account exists with this email, a password reset link has been sent.",
            data={"email": email}
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        return error_response("Internal server error", 500)


@rate_limit(max_requests=5, window_seconds=300, identifier_func=get_ip_identifier)
def reset_password(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Reset password using reset token.
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        reset_token = body.get('reset_token')
        new_password = body.get('new_password')
        
        if not reset_token:
            return error_response("Reset token is required", 400)
        
        if not new_password:
            return error_response("New password is required", 400)
        
        # Validate password complexity
        is_valid, complexity_error = check_password_complexity(new_password)
        if not is_valid:
            return error_response(complexity_error, 400)
        
        # Check if password is compromised
        if is_password_compromised(new_password):
            return error_response(
                "This password has been found in data breaches. Please choose a different password.",
                400
            )
        
        # Get and validate reset token
        reset_data = db.get_password_reset(reset_token)
        if not reset_data:
            return error_response("Invalid or expired reset token", 400)
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(reset_data['expires_at'])
        if datetime.utcnow() > expires_at:
            # Clean up expired token
            db.delete_password_reset(reset_token)
            return error_response("Reset token has expired", 400)
        
        # Check if token has been used
        if reset_data.get('used'):
            return error_response("Reset token has already been used", 400)
        
        # Get user
        user_data = db.get_user(reset_data['user_id'])
        if not user_data:
            return error_response("User not found", 404)
        
        user = User(user_data)
        
        # Hash new password
        password_hash = password_manager.hash_password(new_password)
        
        # Update user password
        update_success = db.update_user(user.user_id, {
            'password_hash': password_hash,
            'password_changed_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        })
        
        if not update_success:
            return error_response("Failed to update password", 500)
        
        # Mark reset token as used
        db.update_password_reset(reset_token, {
            'used': True,
            'used_at': datetime.utcnow().isoformat()
        })
        
        # Clear any account lockouts since password was successfully reset
        from utils.account_security import account_security
        account_security.clear_failed_attempts(user.email)
        
        # Track password reset event
        from handlers.analytics import track_password_reset_event
        track_password_reset_event(user.user_id)
        
        logger.info(f"Password successfully reset for user: {user.email}")
        
        return success_response(
            message="Password has been reset successfully. You can now log in with your new password.",
            data={"email": user.email}
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return error_response("Internal server error", 500)


@rate_limit(max_requests=3, window_seconds=300, identifier_func=get_ip_identifier)
def resend_verification_email(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Resend email verification link.
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        email = body.get('email', '').strip().lower()
        
        if not email:
            return error_response("Email is required", 400)
        
        # Get user by email
        user_data = db.get_user_by_email(email)
        if not user_data:
            # Don't reveal if user exists
            return success_response(
                message="If an account exists with this email, a verification link has been sent."
            )
        
        user = User(user_data)
        
        # Check if already verified
        if user_data.get('email_verified'):
            return error_response("Email is already verified", 400)
        
        # Generate verification token
        verification_token = jwt_manager.create_verification_token(user.user_id)
        
        # Send verification email
        try:
            send_verification_email(
                email=email,
                verification_token=verification_token,
                user_name=user.first_name or 'User'
            )
            logger.info(f"Verification email resent to {email}")
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")
            return error_response("Failed to send verification email", 500)
        
        return success_response(
            message="Verification email has been sent.",
            data={"email": email}
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        logger.error(f"Resend verification error: {str(e)}")
        return error_response("Internal server error", 500)


def verify_email_token(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Verify email using verification token.
    """
    try:
        # Parse request body or query parameters
        token = None
        
        # Try to get token from body first
        if event.get('body'):
            body = json.loads(event['body'])
            token = body.get('token')
        
        # Fall back to query parameters
        if not token and event.get('queryStringParameters'):
            token = event['queryStringParameters'].get('token')
        
        if not token:
            return error_response("Verification token is required", 400)
        
        # Verify token
        payload = jwt_manager.verify_verification_token(token)
        if not payload:
            return error_response("Invalid or expired verification token", 400)
        
        user_id = payload.get('user_id')
        if not user_id:
            return error_response("Invalid token payload", 400)
        
        # Get user
        user_data = db.get_user(user_id)
        if not user_data:
            return error_response("User not found", 404)
        
        user = User(user_data)
        
        # Check if already verified
        if user_data.get('email_verified'):
            return success_response(
                message="Email is already verified.",
                data={"email": user.email}
            )
        
        # Update user verification status
        update_success = db.update_user(user.user_id, {
            'email_verified': True,
            'email_verified_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        })
        
        if not update_success:
            return error_response("Failed to verify email", 500)
        
        # Track email verification event
        from handlers.analytics import track_email_verification_event
        track_email_verification_event(user.user_id)
        
        logger.info(f"Email verified for user: {user.email}")
        
        return success_response(
            message="Email has been verified successfully.",
            data={
                "email": user.email,
                "verified_at": datetime.utcnow().isoformat()
            }
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        return error_response("Internal server error", 500)


def check_reset_token_validity(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Check if a password reset token is valid (without using it).
    """
    try:
        # Parse request body or query parameters
        token = None
        
        if event.get('body'):
            body = json.loads(event['body'])
            token = body.get('reset_token')
        
        if not token and event.get('queryStringParameters'):
            token = event['queryStringParameters'].get('token')
        
        if not token:
            return error_response("Reset token is required", 400)
        
        # Get reset token data
        reset_data = db.get_password_reset(token)
        if not reset_data:
            return success_response(
                data={"valid": False, "reason": "Token not found"}
            )
        
        # Check if expired
        expires_at = datetime.fromisoformat(reset_data['expires_at'])
        if datetime.utcnow() > expires_at:
            return success_response(
                data={"valid": False, "reason": "Token expired"}
            )
        
        # Check if already used
        if reset_data.get('used'):
            return success_response(
                data={"valid": False, "reason": "Token already used"}
            )
        
        # Token is valid
        return success_response(
            data={
                "valid": True,
                "expires_at": reset_data['expires_at'],
                "email": reset_data.get('email', '')
            }
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        logger.error(f"Reset token check error: {str(e)}")
        return error_response("Internal server error", 500)