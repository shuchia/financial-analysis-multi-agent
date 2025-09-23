"""
Waitlist handlers for managing email signups.
"""

import json
from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, ValidationError

from utils.response import (
    success_response, error_response, validation_error_response,
    server_error_response
)
from utils.database import db


class WaitlistSignup(BaseModel):
    """Waitlist signup model."""
    email: EmailStr
    source: str = 'website'
    referral_code: str = None
    interested_features: list = []


def join_waitlist(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Add email to waitlist."""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate input
        try:
            signup_data = WaitlistSignup(**body)
        except ValidationError as e:
            return validation_error_response(e.errors())
        
        # Check if email already exists in waitlist
        existing_entry = db.get_waitlist_entry(signup_data.email)
        if existing_entry:
            return error_response(
                message="Email already on waitlist",
                status_code=409,
                error_code="ALREADY_ON_WAITLIST"
            )
        
        # Create waitlist entry
        waitlist_entry = {
            'email': signup_data.email,
            'source': signup_data.source,
            'referral_code': signup_data.referral_code,
            'interested_features': signup_data.interested_features,
            'joined_at': datetime.utcnow().isoformat(),
            'status': 'pending'
        }
        
        # Save to database
        success = db.add_to_waitlist(waitlist_entry)
        if not success:
            return server_error_response("Failed to add to waitlist")
        
        # Track waitlist signup event
        from handlers.analytics import track_event
        track_event({
            'event_type': 'waitlist_signup',
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': None,
            'event_data': {
                'email': signup_data.email,
                'source': signup_data.source,
                'referral_code': signup_data.referral_code
            },
            'source': 'api'
        })
        
        # Send welcome email (optional)
        send_waitlist_welcome_email(signup_data.email)
        
        return success_response(
            data={
                'email': signup_data.email,
                'position': get_waitlist_position(signup_data.email)
            },
            message="Successfully added to waitlist",
            status_code=201
        )
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Join waitlist error: {str(e)}")
        return server_error_response("Internal server error")


def get_waitlist_position(email: str) -> int:
    """Get position in waitlist (simplified implementation)."""
    # In a real implementation, you'd query the database to count
    # entries created before this email's entry
    return 1000  # Placeholder


def send_waitlist_welcome_email(email: str):
    """Send welcome email to waitlist signups."""
    try:
        from handlers.emails import send_email
        
        subject = "You're on the InvestForge waitlist! 🎉"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #FF6B35;">Welcome to the InvestForge Waitlist! 🚀</h1>
                </div>
                
                <p>Hi there,</p>
                
                <p>Thanks for your interest in InvestForge! You're now on our exclusive waitlist for early access to our AI-powered investment analysis platform.</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #004E89; margin-top: 0;">What to expect:</h3>
                    <ul>
                        <li>🔔 Early access notifications</li>
                        <li>📊 Exclusive beta features</li>
                        <li>💰 Special launch pricing</li>
                        <li>📈 Investment insights and tips</li>
                    </ul>
                </div>
                
                <p>We're working hard to make InvestForge the best AI investment assistant available. You'll be among the first to know when we launch!</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://investforge.io" style="background-color: #FF6B35; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Learn More About InvestForge
                    </a>
                </div>
                
                <p>Follow us on social media for updates and investment insights:</p>
                <ul>
                    <li><a href="https://twitter.com/investforge">Twitter</a></li>
                    <li><a href="https://linkedin.com/company/investforge">LinkedIn</a></li>
                </ul>
                
                <p>Thanks for joining us on this journey!</p>
                
                <p>Best regards,<br>The InvestForge Team</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #666; text-align: center;">
                    InvestForge - AI-Powered Investment Analysis<br>
                    <a href="https://investforge.io">investforge.io</a>
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Welcome to the InvestForge Waitlist!
        
        Hi there,
        
        Thanks for your interest in InvestForge! You're now on our exclusive waitlist for early access to our AI-powered investment analysis platform.
        
        What to expect:
        - Early access notifications
        - Exclusive beta features  
        - Special launch pricing
        - Investment insights and tips
        
        We're working hard to make InvestForge the best AI investment assistant available. You'll be among the first to know when we launch!
        
        Learn more: https://investforge.io
        
        Thanks for joining us on this journey!
        
        Best regards,
        The InvestForge Team
        """
        
        send_email(
            to_email=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
        
    except Exception as e:
        print(f"Send waitlist welcome email error: {str(e)}")


def get_waitlist_stats(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get waitlist statistics (admin only)."""
    try:
        # This would typically require admin authentication
        # For demo purposes, returning mock data
        
        stats = {
            'total_signups': 0,  # Would query actual count
            'recent_signups': 0,  # Last 7 days
            'sources': {},  # Breakdown by source
            'referrals': 0  # Number with referral codes
        }
        
        return success_response(
            data=stats,
            message="Waitlist statistics retrieved successfully"
        )
        
    except Exception as e:
        print(f"Get waitlist stats error: {str(e)}")
        return server_error_response("Internal server error")