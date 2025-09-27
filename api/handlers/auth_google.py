"""
Google OAuth authentication handler for InvestForge.
Handles Google Sign-In token verification and user account creation/linking.
"""

import json
import os
import logging
from typing import Dict, Any, Optional
import boto3
from google.auth.transport import requests
from google.oauth2 import id_token
import google.auth.exceptions

from utils.auth import generate_tokens, hash_password
from utils.database import db
from utils.response import success_response, error_response
from utils.validation import validate_email
from models.user import UserCreate

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle Google OAuth authentication.
    
    Expected body:
    {
        "id_token": "google_oauth_token",
        "plan": "free" (optional, defaults to free)
    }
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        google_token = body.get('id_token')
        
        if not google_token:
            return error_response('Google ID token is required', 400)
        
        # Get Google Client ID from environment
        google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
        if not google_client_id:
            logger.error("GOOGLE_CLIENT_ID not configured")
            return error_response('Google OAuth not configured', 500)
        
        try:
            # Verify the Google token
            idinfo = id_token.verify_oauth2_token(
                google_token, 
                requests.Request(), 
                google_client_id
            )
            
            # Token is valid, extract user information
            email = idinfo.get('email')
            email_verified = idinfo.get('email_verified', False)
            google_id = idinfo['sub']
            name = idinfo.get('name', '')
            given_name = idinfo.get('given_name', '')
            family_name = idinfo.get('family_name', '')
            picture = idinfo.get('picture', '')
            
            if not email:
                return error_response('Email not provided by Google', 400)
            
            if not email_verified:
                return error_response('Email not verified with Google', 400)
            
            # Validate email format
            if not validate_email(email):
                return error_response('Invalid email format', 400)
            
            # Check if user exists
            existing_user = db.get_user(email)
            
            if existing_user:
                # User exists - update Google ID if not set
                if not existing_user.get('google_id'):
                    updates = {
                        'google_id': google_id,
                        'profile_picture': picture,
                        'email_verified': True  # Google emails are pre-verified
                    }
                    if not existing_user.get('first_name') and given_name:
                        updates['first_name'] = given_name
                    if not existing_user.get('last_name') and family_name:
                        updates['last_name'] = family_name
                    
                    db.update_user(email, updates)
                    logger.info(f"Updated existing user with Google ID: {email}")
                
                # Check if account is active
                if existing_user.get('status') == 'suspended':
                    return error_response('Account is suspended', 403)
                
                user_data = existing_user
            else:
                # Create new user
                user_data = {
                    'email': email,
                    'google_id': google_id,
                    'first_name': given_name or name.split(' ')[0] if name else '',
                    'last_name': family_name or ' '.join(name.split(' ')[1:]) if name and ' ' in name else '',
                    'profile_picture': picture,
                    'plan': body.get('plan', 'free'),
                    'email_verified': True,  # Google emails are pre-verified
                    'auth_provider': 'google'
                }
                
                # Create user in database
                if not db.create_user(user_data):
                    return error_response('Failed to create user account', 500)
                
                logger.info(f"Created new user via Google OAuth: {email}")
                
                # Track signup event
                db.track_event({
                    'event_type': 'user_signup',
                    'user_id': user_data['user_id'],
                    'data': {
                        'method': 'google',
                        'plan': user_data['plan']
                    }
                })
            
            # Generate JWT tokens
            tokens = generate_tokens(email)
            
            # Track login event
            db.track_event({
                'event_type': 'user_login',
                'user_id': user_data['user_id'],
                'data': {
                    'method': 'google'
                }
            })
            
            # Prepare response data
            response_data = {
                'user': {
                    'user_id': user_data['user_id'],
                    'email': email,
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', ''),
                    'profile_picture': picture,
                    'plan': user_data.get('plan', 'free'),
                    'email_verified': True
                },
                'access_token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'token_type': 'Bearer',
                'expires_in': 86400  # 24 hours
            }
            
            return success_response(response_data, message='Login successful')
            
        except google.auth.exceptions.GoogleAuthError as e:
            logger.error(f"Google token verification failed: {str(e)}")
            return error_response('Invalid Google token', 401)
        except ValueError as e:
            logger.error(f"Token validation error: {str(e)}")
            return error_response('Invalid token format', 400)
            
    except json.JSONDecodeError:
        return error_response('Invalid JSON in request body', 400)
    except Exception as e:
        logger.error(f"Unexpected error in Google OAuth handler: {str(e)}")
        return error_response('Internal server error', 500)


def link_google_account_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Link an existing account with Google OAuth.
    Requires authentication.
    """
    try:
        # Get authenticated user
        user_id = event['requestContext']['authorizer']['user_id']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        google_token = body.get('id_token')
        
        if not google_token:
            return error_response('Google ID token is required', 400)
        
        # Get user data
        user = db.get_user_by_id(user_id)
        if not user:
            return error_response('User not found', 404)
        
        # Check if already linked
        if user.get('google_id'):
            return error_response('Google account already linked', 400)
        
        # Verify Google token
        google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
        try:
            idinfo = id_token.verify_oauth2_token(
                google_token,
                requests.Request(),
                google_client_id
            )
            
            google_id = idinfo['sub']
            picture = idinfo.get('picture', '')
            
            # Check if this Google ID is already linked to another account
            existing_google_user = db.get_user_by_google_id(google_id)
            if existing_google_user and existing_google_user['user_id'] != user_id:
                return error_response('This Google account is already linked to another user', 400)
            
            # Update user with Google ID
            updates = {
                'google_id': google_id,
                'profile_picture': picture
            }
            
            if db.update_user(user['email'], updates):
                logger.info(f"Linked Google account for user: {user['email']}")
                
                # Track event
                db.track_event({
                    'event_type': 'account_linked',
                    'user_id': user_id,
                    'data': {
                        'provider': 'google'
                    }
                })
                
                return success_response({
                    'message': 'Google account linked successfully',
                    'google_id': google_id
                })
            else:
                return error_response('Failed to link Google account', 500)
                
        except google.auth.exceptions.GoogleAuthError:
            return error_response('Invalid Google token', 401)
            
    except Exception as e:
        logger.error(f"Error linking Google account: {str(e)}")
        return error_response('Internal server error', 500)


def unlink_google_account_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Unlink Google account from user profile.
    Requires authentication and password to be set.
    """
    try:
        # Get authenticated user
        user_id = event['requestContext']['authorizer']['user_id']
        
        # Get user data
        user = db.get_user_by_id(user_id)
        if not user:
            return error_response('User not found', 404)
        
        # Check if Google is linked
        if not user.get('google_id'):
            return error_response('No Google account linked', 400)
        
        # Check if user has a password set (can't unlink if Google is only auth method)
        if not user.get('password_hash'):
            return error_response('Please set a password before unlinking Google account', 400)
        
        # Remove Google ID
        updates = {
            'google_id': None,
            'profile_picture': None
        }
        
        if db.update_user(user['email'], updates):
            logger.info(f"Unlinked Google account for user: {user['email']}")
            
            # Track event
            db.track_event({
                'event_type': 'account_unlinked',
                'user_id': user_id,
                'data': {
                    'provider': 'google'
                }
            })
            
            return success_response({
                'message': 'Google account unlinked successfully'
            })
        else:
            return error_response('Failed to unlink Google account', 500)
            
    except Exception as e:
        logger.error(f"Error unlinking Google account: {str(e)}")
        return error_response('Internal server error', 500)