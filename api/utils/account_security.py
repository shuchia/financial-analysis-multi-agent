"""
Account security utilities for handling failed login attempts,
account lockouts, and suspicious activity detection.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, Tuple
import redis
import os
from datetime import datetime, timedelta
import hashlib

from utils.email import send_security_alert_email

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class AccountSecurity:
    """
    Handles account security features like failed login tracking,
    account lockouts, and suspicious activity detection.
    """
    
    # Configuration
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes
    SUSPICIOUS_ACTIVITY_THRESHOLD = 10  # Attempts from different IPs
    SUSPICIOUS_WINDOW = 3600  # 1 hour
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize with Redis client."""
        self.redis_client = redis_client or self._get_redis_client()
        self.enabled = self.redis_client is not None
    
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client from environment."""
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            logger.warning("REDIS_URL not configured, account security features disabled")
            return None
        
        try:
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            return None
    
    def check_account_lockout(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Check if account is locked due to failed attempts.
        
        Returns:
            Tuple of (is_locked, lock_reason)
        """
        if not self.enabled:
            return False, None
        
        try:
            lockout_key = f"lockout:{email}"
            lock_data = self.redis_client.get(lockout_key)
            
            if lock_data:
                lock_info = json.loads(lock_data)
                remaining_time = int(self.redis_client.ttl(lockout_key))
                
                reason = (
                    f"Account temporarily locked due to {lock_info.get('attempts', 'multiple')} "
                    f"failed login attempts. Please try again in {remaining_time // 60} minutes."
                )
                
                return True, reason
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking account lockout: {str(e)}")
            return False, None
    
    def record_failed_attempt(
        self,
        email: str,
        ip_address: str,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Record a failed login attempt.
        
        Returns:
            Tuple of (account_locked, message)
        """
        if not self.enabled:
            return False, "Security features not available"
        
        try:
            attempts_key = f"attempts:{email}"
            ip_key = f"attempts:ips:{email}"
            
            # Increment attempt counter
            attempts = self.redis_client.incr(attempts_key)
            self.redis_client.expire(attempts_key, self.LOCKOUT_DURATION)
            
            # Track IPs for suspicious activity detection
            self.redis_client.sadd(ip_key, self._hash_ip(ip_address))
            self.redis_client.expire(ip_key, self.SUSPICIOUS_WINDOW)
            
            # Log attempt details
            attempt_log = {
                'timestamp': datetime.utcnow().isoformat(),
                'ip_address': ip_address,
                'user_agent': user_agent,
                'attempt_number': attempts
            }
            
            attempt_detail_key = f"attempt:detail:{email}:{attempts}"
            self.redis_client.setex(
                attempt_detail_key,
                self.LOCKOUT_DURATION,
                json.dumps(attempt_log)
            )
            
            # Check for suspicious activity (multiple IPs)
            unique_ips = self.redis_client.scard(ip_key)
            if unique_ips >= self.SUSPICIOUS_ACTIVITY_THRESHOLD:
                self._handle_suspicious_activity(email, unique_ips)
            
            # Check if account should be locked
            if attempts >= self.MAX_LOGIN_ATTEMPTS:
                # Lock the account
                lock_data = {
                    'locked_at': datetime.utcnow().isoformat(),
                    'attempts': attempts,
                    'reason': 'max_attempts_exceeded'
                }
                
                lockout_key = f"lockout:{email}"
                self.redis_client.setex(
                    lockout_key,
                    self.LOCKOUT_DURATION,
                    json.dumps(lock_data)
                )
                
                # Send security alert
                self._send_lockout_alert(email, attempts, ip_address)
                
                # Clear attempts counter
                self.redis_client.delete(attempts_key)
                
                return True, f"Account locked after {attempts} failed attempts. Please try again in 15 minutes."
            
            remaining_attempts = self.MAX_LOGIN_ATTEMPTS - attempts
            return False, f"Invalid credentials. {remaining_attempts} attempts remaining."
            
        except Exception as e:
            logger.error(f"Error recording failed attempt: {str(e)}")
            return False, "Failed to record attempt"
    
    def clear_failed_attempts(self, email: str) -> bool:
        """Clear failed attempts on successful login."""
        if not self.enabled:
            return False
        
        try:
            # Clear all related keys
            keys_to_delete = [
                f"attempts:{email}",
                f"attempts:ips:{email}",
                f"lockout:{email}"
            ]
            
            # Also clear attempt details
            for i in range(1, self.MAX_LOGIN_ATTEMPTS + 1):
                keys_to_delete.append(f"attempt:detail:{email}:{i}")
            
            self.redis_client.delete(*keys_to_delete)
            return True
            
        except Exception as e:
            logger.error(f"Error clearing failed attempts: {str(e)}")
            return False
    
    def get_failed_attempts_count(self, email: str) -> int:
        """Get current failed attempts count."""
        if not self.enabled:
            return 0
        
        try:
            attempts_key = f"attempts:{email}"
            return int(self.redis_client.get(attempts_key) or 0)
        except Exception as e:
            logger.error(f"Error getting failed attempts: {str(e)}")
            return 0
    
    def manually_lock_account(self, email: str, reason: str, duration: int = 3600) -> bool:
        """
        Manually lock an account (admin action).
        
        Args:
            email: User email
            reason: Lock reason
            duration: Lock duration in seconds
        """
        if not self.enabled:
            return False
        
        try:
            lock_data = {
                'locked_at': datetime.utcnow().isoformat(),
                'reason': reason,
                'manual': True,
                'locked_by': 'admin'
            }
            
            lockout_key = f"lockout:{email}"
            self.redis_client.setex(
                lockout_key,
                duration,
                json.dumps(lock_data)
            )
            
            logger.info(f"Manually locked account: {email} for {duration} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Error manually locking account: {str(e)}")
            return False
    
    def unlock_account(self, email: str) -> bool:
        """Manually unlock an account."""
        if not self.enabled:
            return False
        
        try:
            lockout_key = f"lockout:{email}"
            result = self.redis_client.delete(lockout_key)
            
            if result:
                logger.info(f"Manually unlocked account: {email}")
                # Also clear any failed attempts
                self.clear_failed_attempts(email)
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error unlocking account: {str(e)}")
            return False
    
    def _hash_ip(self, ip_address: str) -> str:
        """Hash IP address for privacy."""
        return hashlib.sha256(ip_address.encode()).hexdigest()[:16]
    
    def _handle_suspicious_activity(self, email: str, unique_ips: int):
        """Handle suspicious activity detection."""
        logger.warning(f"Suspicious activity detected for {email}: {unique_ips} different IPs")
        
        # Track suspicious activity
        suspicious_key = f"suspicious:{email}"
        self.redis_client.setex(suspicious_key, 86400, json.dumps({
            'detected_at': datetime.utcnow().isoformat(),
            'unique_ips': unique_ips
        }))
        
        # Send alert (implement based on your notification system)
        # self._send_suspicious_activity_alert(email, unique_ips)
    
    def _send_lockout_alert(self, email: str, attempts: int, ip_address: str):
        """Send account lockout alert email."""
        try:
            send_security_alert_email(
                email,
                subject="Account Locked - Security Alert",
                alert_type="account_lockout",
                details={
                    'attempts': attempts,
                    'ip_address': ip_address,
                    'locked_until': (datetime.utcnow() + timedelta(seconds=self.LOCKOUT_DURATION)).isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to send lockout alert: {str(e)}")


# Global security instance
account_security = AccountSecurity()


def check_password_complexity(password: str) -> Tuple[bool, Optional[str]]:
    """
    Check password complexity requirements.
    
    Requirements:
    - At least 8 characters
    - Contains uppercase and lowercase letters
    - Contains at least one number
    - Contains at least one special character
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"
    
    # Check for common patterns
    common_patterns = [
        'password', '12345678', 'qwerty', 'abc123', 'letmein',
        'welcome', 'monkey', 'dragon', 'football', 'iloveyou'
    ]
    
    password_lower = password.lower()
    for pattern in common_patterns:
        if pattern in password_lower:
            return False, "Password is too common or contains common patterns"
    
    return True, None


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return os.urandom(length).hex()


def is_password_compromised(password: str) -> bool:
    """
    Check if password has been compromised using Have I Been Pwned API.
    Uses k-anonymity to protect the password.
    """
    try:
        import requests
        
        # Calculate SHA-1 hash of password
        sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]
        
        # Query HIBP API
        response = requests.get(
            f"https://api.pwnedpasswords.com/range/{prefix}",
            timeout=5
        )
        
        if response.status_code != 200:
            # If API fails, don't block user
            return False
        
        # Check if suffix exists in response
        for line in response.text.splitlines():
            if line.startswith(suffix):
                # Password found in breach
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking password breach status: {str(e)}")
        # Don't block user if check fails
        return False