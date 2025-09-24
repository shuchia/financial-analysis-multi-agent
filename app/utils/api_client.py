"""
API client for communicating with the InvestForge backend.
"""

import os
import json
import requests
from typing import Dict, Any, Optional
import streamlit as st
from datetime import datetime, timedelta


class APIClient:
    """Client for InvestForge API communication."""
    
    def __init__(self):
        # Use the unified domain with /api path
        self.base_url = os.getenv('API_BASE_URL', 'https://investforge.io/api')
        if 'localhost' in self.base_url:
            self.base_url = 'http://localhost:8080/api'
        self.timeout = 30
        self._check_and_refresh_token()
    
    def _get_headers(self, include_auth: bool = True) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if include_auth and 'access_token' in st.session_state:
            headers['Authorization'] = f"Bearer {st.session_state.access_token}"
        
        return headers
    
    def _check_and_refresh_token(self):
        """Check if token needs refresh and refresh if needed."""
        if 'access_token' not in st.session_state:
            return
        
        # Check if we have token expiry info
        if 'token_expires_at' in st.session_state:
            expires_at = datetime.fromisoformat(st.session_state.token_expires_at)
            # Refresh if token expires in less than 5 minutes
            if datetime.utcnow() + timedelta(minutes=5) > expires_at:
                self.refresh_token()
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and errors."""
        try:
            if response.status_code == 401:
                # Try to refresh token and retry
                if self.refresh_token():
                    return None  # Caller should retry
                else:
                    # Clear session and redirect to login
                    for key in ['access_token', 'refresh_token', 'user_data', 'token_expires_at']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.error("Session expired. Please log in again.")
                    st.session_state.page = 'login'
                    st.rerun()
            
            # Handle specific error codes with better messages
            if response.status_code == 409:
                # Parse the error response to get the specific message
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', 'Conflict error occurred')
                    if 'already exists' in error_message.lower():
                        st.error("An account with this email already exists. Please try logging in instead.")
                    else:
                        st.error(f"Conflict: {error_message}")
                except:
                    st.error("An account with this email already exists. Please try logging in instead.")
                return None
            
            elif response.status_code == 400:
                # Parse validation errors
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', 'Invalid request')
                    st.error(f"Validation Error: {error_message}")
                except:
                    st.error("Invalid request. Please check your input.")
                return None
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            # Only show generic error for actual network/unexpected errors
            if response.status_code not in [400, 409]:
                st.error(f"API Error: {str(e)}")
            return None
    
    # Authentication endpoints
    
    def signup(self, email: str, password: str, first_name: str = None, 
               last_name: str = None, plan: str = 'free') -> Optional[Dict[str, Any]]:
        """Sign up a new user."""
        try:
            response = requests.post(
                f"{self.base_url}/auth/signup",
                headers=self._get_headers(include_auth=False),
                json={
                    'email': email,
                    'password': password,
                    'first_name': first_name,
                    'last_name': last_name,
                    'plan': plan
                },
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result and result.get('success'):
                # Store tokens and user data
                data = result['data']
                st.session_state.access_token = data['access_token']
                st.session_state.refresh_token = data['refresh_token']
                st.session_state.user_data = data['user']
                # Calculate token expiry (24 hours)
                st.session_state.token_expires_at = (
                    datetime.utcnow() + timedelta(hours=24)
                ).isoformat()
                return data
            
            return None
            
        except Exception as e:
            st.error(f"Signup failed: {str(e)}")
            return None
    
    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Log in a user."""
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                headers=self._get_headers(include_auth=False),
                json={
                    'email': email,
                    'password': password
                },
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result and result.get('success'):
                # Store tokens and user data
                data = result['data']
                st.session_state.access_token = data['access_token']
                st.session_state.refresh_token = data['refresh_token']
                st.session_state.user_data = data['user']
                # Calculate token expiry (24 hours)
                st.session_state.token_expires_at = (
                    datetime.utcnow() + timedelta(hours=24)
                ).isoformat()
                return data
            
            return None
            
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
            return None
    
    def refresh_token(self) -> bool:
        """Refresh the access token."""
        if 'refresh_token' not in st.session_state:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/refresh",
                headers=self._get_headers(include_auth=False),
                json={
                    'refresh_token': st.session_state.refresh_token
                },
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result and result.get('success'):
                # Update access token
                st.session_state.access_token = result['data']['access_token']
                st.session_state.token_expires_at = (
                    datetime.utcnow() + timedelta(hours=24)
                ).isoformat()
                return True
            
            return False
            
        except Exception:
            return False
    
    def logout(self):
        """Log out the current user."""
        # Clear session state
        for key in ['access_token', 'refresh_token', 'user_data', 'token_expires_at']:
            if key in st.session_state:
                del st.session_state[key]
    
    # User management endpoints
    
    def get_user(self) -> Optional[Dict[str, Any]]:
        """Get current user profile."""
        try:
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result is None:  # Token was refreshed, retry
                response = requests.get(
                    f"{self.base_url}/users/me",
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                result = self._handle_response(response)
            
            if result and result.get('success'):
                return result['data']
            
            return None
            
        except Exception as e:
            st.error(f"Failed to get user profile: {str(e)}")
            return None
    
    def update_user(self, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user profile."""
        try:
            response = requests.put(
                f"{self.base_url}/users/me",
                headers=self._get_headers(),
                json=updates,
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result and result.get('success'):
                # Update session state
                st.session_state.user_data.update(result['data'])
                return result['data']
            
            return None
            
        except Exception as e:
            st.error(f"Failed to update profile: {str(e)}")
            return None
    
    # Usage tracking endpoints
    
    def get_usage(self, period: str = 'current_month') -> Optional[Dict[str, Any]]:
        """Get usage statistics."""
        try:
            response = requests.get(
                f"{self.base_url}/users/usage",
                headers=self._get_headers(),
                params={'period': period},
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result and result.get('success'):
                return result['data']
            
            return None
            
        except Exception as e:
            st.error(f"Failed to get usage data: {str(e)}")
            return None
    
    def increment_usage(self, feature: str, count: int = 1) -> Optional[Dict[str, Any]]:
        """Increment usage for a feature."""
        try:
            response = requests.post(
                f"{self.base_url}/users/usage/{feature}",
                headers=self._get_headers(),
                json={'increment': count},
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result and result.get('success'):
                return result['data']
            
            return None
            
        except Exception as e:
            st.error(f"Failed to track usage: {str(e)}")
            return None
    
    def check_usage_limit(self, feature: str, count: int = 1) -> Optional[Dict[str, Any]]:
        """Check if user can perform an action based on usage limits."""
        try:
            response = requests.get(
                f"{self.base_url}/users/usage/check",
                headers=self._get_headers(),
                params={'feature': feature, 'count': count},
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result and result.get('success'):
                return result['data']
            
            return None
            
        except Exception as e:
            st.error(f"Failed to check usage limit: {str(e)}")
            return None
    
    # Payment endpoints
    
    def create_checkout_session(self, plan: str) -> Optional[Dict[str, Any]]:
        """Create Stripe checkout session for plan upgrade."""
        try:
            success_url = f"{os.getenv('APP_URL', 'https://app.investforge.io')}/payment-success"
            cancel_url = f"{os.getenv('APP_URL', 'https://app.investforge.io')}/payment-cancel"
            
            response = requests.post(
                f"{self.base_url}/stripe/create-checkout-session",
                headers=self._get_headers(),
                json={
                    'plan': plan,
                    'success_url': success_url,
                    'cancel_url': cancel_url
                },
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result and result.get('success'):
                return result['data']
            
            return None
            
        except Exception as e:
            st.error(f"Failed to create checkout session: {str(e)}")
            return None
    
    # Analytics endpoints
    
    def track_event(self, event_type: str, event_data: Dict[str, Any] = None) -> bool:
        """Track an analytics event."""
        try:
            user_id = st.session_state.get('user_data', {}).get('user_id')
            
            response = requests.post(
                f"{self.base_url}/analytics/track",
                headers=self._get_headers(),
                json={
                    'event_type': event_type,
                    'event_data': event_data or {},
                    'user_id': user_id
                },
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            return result is not None and result.get('success', False)
            
        except Exception:
            # Don't show error for analytics failures
            return False
    
    # User preferences endpoints
    
    def get_user_preferences(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user preferences."""
        try:
            response = requests.post(
                f"{self.base_url}/users/preferences",
                headers=self._get_headers(include_auth=False),
                json={'email': email, 'action': 'get'},
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result and result.get('success'):
                return result['data']
            
            return None
            
        except Exception as e:
            st.error(f"Failed to get preferences: {str(e)}")
            return None
    
    def save_user_preferences(self, email: str, preferences: Dict[str, Any]) -> bool:
        """Save user preferences."""
        try:
            response = requests.post(
                f"{self.base_url}/users/preferences",
                headers=self._get_headers(include_auth=False),
                json={
                    'email': email,
                    'preferences': preferences
                },
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            return result is not None and result.get('success', False)
            
        except Exception as e:
            st.error(f"Failed to save preferences: {str(e)}")
            return False

    # Waitlist endpoints
    
    def join_waitlist(self, email: str, source: str = 'website') -> Optional[Dict[str, Any]]:
        """Join the waitlist."""
        try:
            response = requests.post(
                f"{self.base_url}/waitlist/join",
                headers=self._get_headers(include_auth=False),
                json={
                    'email': email,
                    'source': source
                },
                timeout=self.timeout
            )
            
            result = self._handle_response(response)
            if result and result.get('success'):
                return result['data']
            
            return None
            
        except Exception as e:
            st.error(f"Failed to join waitlist: {str(e)}")
            return None


    # Enhanced analytics methods
    
    def track_signup_event(self, user_id: str, plan: str, referral_source: str = None) -> bool:
        """Track user signup event."""
        return self.track_event('user_signup', {
            'plan': plan,
            'referral_source': referral_source,
            'timestamp': datetime.now().isoformat()
        })
    
    def track_login_event(self, user_id: str) -> bool:
        """Track user login event."""
        return self.track_event('user_login', {
            'timestamp': datetime.now().isoformat()
        })
    
    def track_analysis_event(self, user_id: str, symbol: str, analysis_type: str) -> bool:
        """Track stock analysis event."""
        return self.track_event('stock_analysis', {
            'symbol': symbol,
            'analysis_type': analysis_type,
            'timestamp': datetime.now().isoformat()
        })
    
    def track_preferences_event(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Track preferences completion event."""
        return self.track_event('preferences_completed', {
            'experience': preferences.get('experience'),
            'risk_tolerance': preferences.get('risk_tolerance'),
            'initial_amount': preferences.get('initial_amount'),
            'timestamp': datetime.now().isoformat()
        })
    
    def increment_feature_usage(self, user_id: str, feature: str, count: int = 1) -> bool:
        """Increment usage count for a feature."""
        try:
            response = requests.post(
                f"{self.base_url}/analytics/usage",
                headers=self._get_headers(include_auth=False),
                json={
                    'action': 'usage',
                    'user_id': user_id,
                    'feature': feature,
                    'count': count
                },
                timeout=self.timeout
            )
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def get_user_usage(self, user_id: str, month: str = None) -> Optional[Dict[str, Any]]:
        """Get user usage statistics."""
        try:
            payload = {
                'action': 'get_usage',
                'user_id': user_id
            }
            if month:
                payload['month'] = month
            
            response = requests.post(
                f"{self.base_url}/analytics/usage",
                headers=self._get_headers(include_auth=False),
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result['data']
            
            return None
            
        except Exception:
            return None


# Global API client instance
api_client = APIClient()