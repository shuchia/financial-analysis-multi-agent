# InvestForge User Management System - Updated Implementation Plan

## Overview

This document outlines the remaining implementation work for InvestForge's user management system. The core authentication infrastructure is already implemented, so this plan focuses on enhancements and missing features.

## Current Implementation Status

### ✅ Already Implemented

#### Core Authentication
- JWT-based authentication (24h access tokens, 30-day refresh tokens)
- Email/password signup and login with bcrypt hashing
- User CRUD operations with DynamoDB backend
- Lambda authorizer for protected routes
- Streamlit session management with Redis
- API client with automatic token refresh

#### Database Infrastructure
- DynamoDB tables: `investforge-users-simple`, `investforge-usage`, `investforge-analytics`, `investforge-api-dev-waitlist`
- User email indexing and efficient queries
- Usage tracking with real-time enforcement

#### User Features
- Plan-based limits (free: 5 analyses/month, growth: unlimited)
- Basic user preferences storage
- Onboarding flow with preference collection
- Waitlist system with position tracking
- Analytics event tracking

### 🚧 Remaining Implementation Work

## 1. Google OAuth Integration (Priority: High)

### 1.1 Backend Implementation

#### Lambda Function: `/api/auth/google`
```python
# handlers/auth_google.py
import os
from google.auth.transport import requests
from google.oauth2 import id_token
import json
from utils.database import db
from utils.auth import generate_tokens

def handler(event, context):
    """Handle Google OAuth authentication"""
    
    body = json.loads(event['body'])
    google_token = body.get('id_token')
    
    try:
        # Verify Google token
        idinfo = id_token.verify_oauth2_token(
            google_token, 
            requests.Request(), 
            os.environ['GOOGLE_CLIENT_ID']
        )
        
        # Extract user info
        email = idinfo['email']
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')
        
        # Check if user exists
        existing_user = db.get_user(email)
        
        if existing_user:
            # Update Google ID if not set
            if not existing_user.get('google_id'):
                db.update_user(email, {
                    'google_id': idinfo['sub'],
                    'profile_picture': picture
                })
        else:
            # Create new user
            user_data = {
                'email': email,
                'google_id': idinfo['sub'],
                'name': name,
                'profile_picture': picture,
                'plan': 'free',
                'email_verified': True  # Google emails are pre-verified
            }
            db.create_user(user_data)
        
        # Generate JWT tokens
        tokens = generate_tokens(email)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'data': {
                    'access_token': tokens['access_token'],
                    'refresh_token': tokens['refresh_token'],
                    'user': {
                        'email': email,
                        'name': name,
                        'picture': picture
                    }
                }
            })
        }
        
    except ValueError as e:
        # Invalid token
        return {
            'statusCode': 401,
            'body': json.dumps({
                'success': False,
                'message': 'Invalid Google token'
            })
        }
```

#### Environment Variables Required
```yaml
GOOGLE_CLIENT_ID: "your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET: "your-client-secret"
```

### 1.2 Frontend Implementation

#### Update `app/app.py` Login Page
```python
# Add Google Sign-In button to login form
def show_google_signin():
    """Display Google Sign-In button"""
    
    # Load Google Client ID from environment
    google_client_id = os.getenv('GOOGLE_CLIENT_ID')
    
    if google_client_id:
        st.markdown("""
        <div id="g_id_onload"
             data-client_id="{}"
             data-callback="handleGoogleSignIn">
        </div>
        <div class="g_id_signin" data-type="standard"></div>
        
        <script src="https://accounts.google.com/gsi/client" async defer></script>
        <script>
            function handleGoogleSignIn(response) {
                // Send token to backend
                fetch('/api/auth/google', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id_token: response.credential})
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        // Store tokens and redirect
                        window.location.reload();
                    }
                });
            }
        </script>
        """.format(google_client_id), unsafe_allow_html=True)
```

## 2. Enhanced Security Features (Priority: High)

### 2.1 Rate Limiting

#### Lambda Middleware: `utils/rate_limiter.py`
```python
import time
import json
from functools import wraps
from utils.redis_client import redis_client

class RateLimiter:
    def __init__(self, max_requests=60, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def check_rate_limit(self, identifier):
        """Check if request is within rate limit"""
        key = f"rate_limit:{identifier}"
        
        # Get current count
        current = redis_client.get(key)
        if current is None:
            # First request
            redis_client.setex(key, self.window_seconds, 1)
            return True
        
        current_count = int(current)
        if current_count >= self.max_requests:
            return False
        
        # Increment counter
        redis_client.incr(key)
        return True

def rate_limit(max_requests=60, window_seconds=60):
    """Decorator for rate limiting Lambda functions"""
    limiter = RateLimiter(max_requests, window_seconds)
    
    def decorator(func):
        @wraps(func)
        def wrapper(event, context):
            # Get identifier (IP or user ID)
            identifier = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
            
            if not limiter.check_rate_limit(identifier):
                return {
                    'statusCode': 429,
                    'body': json.dumps({
                        'success': False,
                        'message': 'Too many requests. Please try again later.'
                    })
                }
            
            return func(event, context)
        return wrapper
    return decorator
```

### 2.2 Account Lockout

#### Update Login Handler
```python
# Add to handlers/auth.py login function

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes

def check_account_lockout(email):
    """Check if account is locked due to failed attempts"""
    lockout_key = f"lockout:{email}"
    attempts_key = f"attempts:{email}"
    
    # Check if locked
    if redis_client.exists(lockout_key):
        return True, "Account temporarily locked. Please try again later."
    
    return False, None

def record_failed_attempt(email):
    """Record failed login attempt"""
    attempts_key = f"attempts:{email}"
    
    # Increment attempts
    attempts = redis_client.incr(attempts_key)
    redis_client.expire(attempts_key, 900)  # Reset after 15 minutes
    
    if attempts >= MAX_LOGIN_ATTEMPTS:
        # Lock account
        lockout_key = f"lockout:{email}"
        redis_client.setex(lockout_key, LOCKOUT_DURATION, 1)
        
        # Send security alert email
        send_security_alert(email, "Multiple failed login attempts")
        
        return True, f"Account locked after {MAX_LOGIN_ATTEMPTS} failed attempts"
    
    return False, f"{MAX_LOGIN_ATTEMPTS - attempts} attempts remaining"

def clear_failed_attempts(email):
    """Clear failed attempts on successful login"""
    redis_client.delete(f"attempts:{email}")
```

## 3. Complete Email Workflows (Priority: Medium)

### 3.1 Email Verification Flow

#### Current Gap
- Verification emails are sent but the verification endpoint is incomplete
- Need to complete the verification landing page

#### Implementation
```python
# handlers/verify_email.py
def verify_email_handler(event, context):
    """Handle email verification"""
    
    token = event['queryStringParameters'].get('token')
    if not token:
        return redirect_to_app_with_error("Invalid verification link")
    
    # Decode token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        email = payload.get('email')
        
        # Update user
        db.update_user(email, {'email_verified': True})
        
        # Auto-login user
        tokens = generate_tokens(email)
        
        # Redirect to app with tokens
        return {
            'statusCode': 302,
            'headers': {
                'Location': f"{APP_URL}?verified=true&token={tokens['access_token']}"
            }
        }
        
    except jwt.ExpiredSignatureError:
        return redirect_to_app_with_error("Verification link expired")
```

### 3.2 Password Reset Flow

#### Email Template
```html
<!-- templates/password_reset.html -->
<h2>Reset Your Password</h2>
<p>Hi there,</p>
<p>You requested to reset your password for InvestForge. Click the link below to set a new password:</p>
<p><a href="{{ reset_link }}" style="background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
<p>This link will expire in 1 hour.</p>
<p>If you didn't request this, please ignore this email.</p>
```

#### Reset Handler
```python
# handlers/reset_password.py
def request_reset_handler(event, context):
    """Send password reset email"""
    
    body = json.loads(event['body'])
    email = body.get('email')
    
    # Check if user exists
    user = db.get_user(email)
    if not user:
        # Don't reveal if email exists
        return success_response("If account exists, reset email sent")
    
    # Generate reset token
    reset_token = generate_reset_token(email)
    
    # Send email
    send_reset_email(email, reset_token)
    
    # Log event
    log_security_event('password_reset_requested', email)
    
    return success_response("Password reset email sent")
```

## 4. Admin Dashboard (Priority: Medium)

### 4.1 Admin API Endpoints

#### User Management
```python
# handlers/admin.py
@require_admin
def list_users_handler(event, context):
    """List all users with filters"""
    
    filters = event.get('queryStringParameters', {})
    
    # Parse filters
    plan = filters.get('plan')
    status = filters.get('status')
    search = filters.get('search')
    page = int(filters.get('page', 1))
    limit = int(filters.get('limit', 50))
    
    # Query users
    users = db.list_users(
        plan=plan,
        status=status,
        search=search,
        limit=limit,
        offset=(page - 1) * limit
    )
    
    # Remove sensitive data
    for user in users:
        user.pop('password_hash', None)
        user.pop('refresh_token', None)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'data': users,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': db.count_users(filters)
            }
        })
    }
```

### 4.2 Admin UI (Streamlit Page)

```python
# app/pages/admin.py
import streamlit as st
from utils.auth import require_admin_role

@require_admin_role
def admin_dashboard():
    st.title("🛠️ Admin Dashboard")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Users", "Waitlist", "Analytics", "Audit Logs"])
    
    with tab1:
        show_user_management()
    
    with tab2:
        show_waitlist_management()
    
    with tab3:
        show_analytics_dashboard()
    
    with tab4:
        show_audit_logs()

def show_user_management():
    """User management interface"""
    
    # Search and filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("Search users", placeholder="Email or name")
    with col2:
        plan_filter = st.selectbox("Plan", ["All", "free", "growth", "enterprise"])
    with col3:
        status_filter = st.selectbox("Status", ["All", "active", "suspended", "deleted"])
    
    # Get users
    users = api_client.admin_get_users(
        search=search,
        plan=plan_filter if plan_filter != "All" else None,
        status=status_filter if status_filter != "All" else None
    )
    
    # Display users table
    if users:
        df = pd.DataFrame(users)
        
        # Add actions
        for idx, user in df.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"{user['email']} ({user['plan']})")
            with col2:
                if st.button("Edit", key=f"edit_{idx}"):
                    show_edit_user_modal(user)
            with col3:
                if st.button("Suspend", key=f"suspend_{idx}"):
                    suspend_user(user['user_id'])
```

## 5. Enhanced Preference System (Priority: Low)

### 5.1 Extended Preference Schema

```python
# Update DynamoDB preferences structure
PREFERENCE_SCHEMA = {
    "investment_preferences": {
        "experience_level": ["beginner", "intermediate", "advanced", "professional"],
        "goals": {
            "long_term_wealth": bool,
            "passive_income": bool,
            "retirement": bool,
            "education": bool,
            "real_estate": bool,
            "short_term": bool,
            "learning": bool
        },
        "risk_tolerance": int,  # 1-10
        "investment_amount": str,
        "time_horizon": ["< 1 year", "1-3 years", "3-5 years", "5-10 years", "> 10 years"]
    },
    "analysis_preferences": {
        "default_depth": ["quick", "standard", "comprehensive"],
        "include_competitors": bool,
        "include_sentiment": bool,
        "technical_indicators": ["rsi", "macd", "bollinger", "ema", "sma"],
        "fundamental_metrics": ["pe", "pb", "roe", "debt_ratio", "revenue_growth"],
        "news_sources": ["reuters", "bloomberg", "wsj", "ft"]
    },
    "notification_preferences": {
        "email_alerts": bool,
        "analysis_complete": bool,
        "price_alerts": bool,
        "weekly_summary": bool,
        "product_updates": bool,
        "alert_threshold": float  # Percentage change
    },
    "ui_preferences": {
        "theme": ["light", "dark", "auto"],
        "chart_type": ["candlestick", "line", "area"],
        "default_view": ["overview", "technical", "fundamental"],
        "data_refresh": ["manual", "5min", "15min", "30min"]
    }
}
```

### 5.2 Preference-Based Analysis Customization

```python
# app/utils/analysis_customizer.py
def customize_analysis_based_on_preferences(ticker, user_preferences):
    """Customize analysis based on user preferences"""
    
    prefs = user_preferences.get('analysis_preferences', {})
    
    analysis_config = {
        'depth': prefs.get('default_depth', 'standard'),
        'include_competitors': prefs.get('include_competitors', True),
        'include_sentiment': prefs.get('include_sentiment', True),
        'technical_indicators': prefs.get('technical_indicators', ['rsi', 'macd']),
        'time_period': get_time_period_from_horizon(
            user_preferences.get('investment_preferences', {}).get('time_horizon')
        ),
        'risk_adjusted': user_preferences.get('investment_preferences', {}).get('risk_tolerance', 5) < 5
    }
    
    # Adjust prompts based on experience level
    experience = user_preferences.get('investment_preferences', {}).get('experience_level', 'intermediate')
    if experience == 'beginner':
        analysis_config['explain_terms'] = True
        analysis_config['use_simple_language'] = True
    elif experience == 'professional':
        analysis_config['include_advanced_metrics'] = True
        analysis_config['detailed_technicals'] = True
    
    return analysis_config
```

## 6. Compliance & Audit Features (Priority: Medium)

### 6.1 Comprehensive Audit Logging

```python
# utils/audit_logger.py
import json
import hashlib
from datetime import datetime
from utils.database import db

class AuditLogger:
    def __init__(self):
        self.table = db.audit_table
    
    def log_event(self, event_type, action, user_id=None, target_id=None, 
                  resource=None, details=None, ip_address=None, user_agent=None,
                  success=True, error_code=None):
        """Log an audit event"""
        
        audit_entry = {
            'log_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'action': action,
            'user_id': user_id,
            'target_user_id': target_id,
            'resource': resource,
            'ip_address_hash': self._hash_ip(ip_address) if ip_address else None,
            'user_agent': user_agent,
            'session_id': get_current_session_id(),
            'success': success,
            'error_code': error_code,
            'details': json.dumps(details) if details else None
        }
        
        # Store in DynamoDB
        self.table.put_item(Item=audit_entry)
        
        # Alert on security events
        if event_type == 'security' and not success:
            self._alert_security_team(audit_entry)
    
    def _hash_ip(self, ip_address):
        """Hash IP address for privacy"""
        return hashlib.sha256(ip_address.encode()).hexdigest()
    
    def _alert_security_team(self, event):
        """Send alert for security events"""
        # Send to SNS topic or security monitoring
        pass

# Audit event decorators
def audit_action(event_type, action, resource=None):
    """Decorator to automatically log actions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = get_current_user_id()
            try:
                result = func(*args, **kwargs)
                audit.log_event(
                    event_type=event_type,
                    action=action,
                    user_id=user_id,
                    resource=resource,
                    success=True
                )
                return result
            except Exception as e:
                audit.log_event(
                    event_type=event_type,
                    action=action,
                    user_id=user_id,
                    resource=resource,
                    success=False,
                    error_code=str(e)
                )
                raise
        return wrapper
    return decorator

# Global audit logger instance
audit = AuditLogger()
```

### 6.2 GDPR Compliance

```python
# handlers/gdpr.py
def export_user_data_handler(event, context):
    """Export all user data (GDPR right to access)"""
    
    user_id = event['requestContext']['authorizer']['user_id']
    
    # Collect all user data
    user_data = {
        'profile': db.get_user_by_id(user_id),
        'preferences': db.get_user_preferences(user_id),
        'usage_history': db.get_usage_history(user_id),
        'analysis_history': db.get_analysis_history(user_id),
        'audit_logs': db.get_user_audit_logs(user_id)
    }
    
    # Remove sensitive fields
    user_data['profile'].pop('password_hash', None)
    
    # Generate export file
    export_id = generate_data_export(user_data)
    
    # Send email with download link
    send_data_export_email(user_data['profile']['email'], export_id)
    
    # Log export
    audit.log_event('gdpr', 'data_export', user_id=user_id)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'message': 'Data export initiated. Check your email.'
        })
    }

def delete_user_data_handler(event, context):
    """Delete all user data (GDPR right to erasure)"""
    
    user_id = event['requestContext']['authorizer']['user_id']
    
    # Verify deletion request
    body = json.loads(event['body'])
    if body.get('confirm') != 'DELETE':
        return error_response('Please confirm deletion')
    
    # Delete from all tables
    db.delete_user(user_id)
    db.delete_user_preferences(user_id)
    db.delete_usage_history(user_id)
    db.delete_analysis_history(user_id)
    
    # Log deletion
    audit.log_event('gdpr', 'data_deletion', user_id=user_id)
    
    # Send confirmation email
    send_deletion_confirmation(email)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'message': 'Account and all data permanently deleted'
        })
    }
```

## Implementation Timeline (Updated)

### Week 1: Core Security & Google OAuth
- [ ] Day 1-2: Google OAuth integration (backend + frontend)
- [ ] Day 3: Rate limiting implementation
- [ ] Day 4: Account lockout system
- [ ] Day 5: Testing and integration

### Week 2: Email & Admin Features  
- [ ] Day 1-2: Complete email verification flow
- [ ] Day 3: Password reset implementation
- [ ] Day 4-5: Admin dashboard (users + waitlist)

### Week 3: Compliance & Polish
- [ ] Day 1-2: Audit logging system
- [ ] Day 3: GDPR compliance endpoints
- [ ] Day 4: Enhanced preferences UI
- [ ] Day 5: Final testing and documentation

## Testing Strategy

### Unit Tests
```python
# tests/test_auth.py
def test_google_oauth_valid_token():
    """Test Google OAuth with valid token"""
    # Mock Google token verification
    with patch('google.oauth2.id_token.verify_oauth2_token') as mock_verify:
        mock_verify.return_value = {
            'email': 'test@gmail.com',
            'sub': '12345',
            'name': 'Test User'
        }
        
        response = google_auth_handler({
            'body': json.dumps({'id_token': 'valid_token'})
        }, {})
        
        assert response['statusCode'] == 200
        data = json.loads(response['body'])
        assert data['success'] == True
        assert 'access_token' in data['data']

def test_rate_limiting():
    """Test rate limiting functionality"""
    # Make 60 requests
    for i in range(60):
        response = make_request()
        assert response['statusCode'] == 200
    
    # 61st request should fail
    response = make_request()
    assert response['statusCode'] == 429
```

### Integration Tests
```python
# tests/test_user_flow.py
def test_complete_user_journey():
    """Test complete user signup to analysis flow"""
    
    # 1. Sign up
    signup_response = api.signup(email, password)
    assert signup_response['success']
    
    # 2. Verify email
    verify_response = api.verify_email(token)
    assert verify_response['success']
    
    # 3. Set preferences
    pref_response = api.save_preferences(preferences)
    assert pref_response['success']
    
    # 4. Run analysis
    analysis_response = api.run_analysis('AAPL')
    assert analysis_response['success']
    
    # 5. Check usage
    usage_response = api.get_usage()
    assert usage_response['data']['analyses_count'] == 1
```

## Deployment Checklist

### Environment Variables
```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret

# Security
JWT_SECRET=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key

# Redis (for rate limiting)
REDIS_URL=redis://your-redis-instance

# Email
FROM_EMAIL=noreply@investforge.io
SUPPORT_EMAIL=support@investforge.io
```

### AWS Resources
- [ ] Update Lambda functions with new handlers
- [ ] Add Redis ElastiCache for rate limiting
- [ ] Update API Gateway with new endpoints
- [ ] Configure Google OAuth in Console
- [ ] Update environment variables

### Security Review
- [ ] Penetration testing for OAuth flow
- [ ] Rate limiting verification
- [ ] GDPR compliance audit
- [ ] Security logging review

## Conclusion

This updated plan focuses on the remaining 20% of work needed to complete InvestForge's user management system. The core infrastructure is solid, and these enhancements will provide enterprise-grade security, compliance, and user experience features.