"""
Email service handlers using AWS SES.
"""

import json
import os
import boto3
from typing import Dict, Any
from datetime import datetime

from utils.response import (
    success_response, error_response, unauthorized_response,
    not_found_response, server_error_response
)
from utils.database import db
from utils.auth import get_user_from_event
from models.user import User


# Initialize SES client
ses_client = boto3.client('ses', region_name=os.getenv('SES_REGION', 'us-east-1'))


def send_welcome_email(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Send welcome email to new users."""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('user_id')
        
        if not user_id:
            return error_response("User ID is required", 400)
        
        # Get user data
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        
        # Send welcome email
        success = send_welcome_email_internal(user)
        
        if success:
            return success_response(
                message="Welcome email sent successfully"
            )
        else:
            return server_error_response("Failed to send welcome email")
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Send welcome email error: {str(e)}")
        return server_error_response("Internal server error")


def send_upgrade_confirmation_email(user_id: str, new_plan: str) -> bool:
    """Send plan upgrade confirmation email."""
    try:
        # Get user data
        user_data = db.get_user(user_id)
        if not user_data:
            return False
        
        user = User(user_data)
        
        # Email content
        subject = f"Welcome to InvestForge {new_plan.title()} Plan!"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #FF6B35;">🚀 Welcome to InvestForge {new_plan.title()}!</h1>
                </div>
                
                <p>Hi {user.first_name or 'there'},</p>
                
                <p>Congratulations! Your subscription to the <strong>{new_plan.title()} plan</strong> has been activated successfully.</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #004E89; margin-top: 0;">What's included in your {new_plan.title()} plan:</h3>
                    <ul>
                        {"<li>Unlimited stock analyses</li>" if new_plan in ['growth', 'pro'] else ""}
                        {"<li>Portfolio optimization tools</li>" if new_plan in ['growth', 'pro'] else ""}
                        {"<li>Strategy backtesting</li>" if new_plan in ['growth', 'pro'] else ""}
                        {"<li>Priority support</li>" if new_plan in ['growth', 'pro'] else ""}
                        {"<li>API access</li>" if new_plan == 'pro' else ""}
                        {"<li>White-label reports</li>" if new_plan == 'pro' else ""}
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://app.investforge.io" style="background-color: #FF6B35; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Start Using Your New Features
                    </a>
                </div>
                
                <p>If you have any questions or need help getting started, don't hesitate to reach out to our support team.</p>
                
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
        Welcome to InvestForge {new_plan.title()}!
        
        Hi {user.first_name or 'there'},
        
        Congratulations! Your subscription to the {new_plan.title()} plan has been activated successfully.
        
        Visit https://app.investforge.io to start using your new features.
        
        If you have any questions, please contact our support team.
        
        Best regards,
        The InvestForge Team
        """
        
        # Send email
        return send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
        
    except Exception as e:
        print(f"Send upgrade confirmation email error: {str(e)}")
        return False


def send_welcome_email_internal(user: User) -> bool:
    """Internal function to send welcome email."""
    try:
        subject = "Welcome to InvestForge - Your AI Investment Assistant!"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #FF6B35;">Welcome to InvestForge! 🎉</h1>
                </div>
                
                <p>Hi {user.first_name or 'there'},</p>
                
                <p>Welcome to InvestForge! We're thrilled to have you join our community of smart investors using AI-powered analysis.</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #004E89; margin-top: 0;">Get started with your {user.plan.title()} plan:</h3>
                    <ul>
                        <li>✅ Run your first stock analysis</li>
                        <li>📊 Explore technical indicators</li>
                        <li>🔍 Get AI-powered insights</li>
                        {"<li>🚀 Try portfolio optimization</li>" if user.plan in ['growth', 'pro'] else ""}
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://app.investforge.io" style="background-color: #FF6B35; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Launch InvestForge App
                    </a>
                </div>
                
                <div style="background-color: #e8f4fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>💡 Pro Tip:</strong> Start by analyzing a stock you're already familiar with to see how our AI insights compare to your own research!</p>
                </div>
                
                <p>Questions? We're here to help! Reply to this email or check out our <a href="https://investforge.io/help">help center</a>.</p>
                
                <p>Happy investing!<br>The InvestForge Team</p>
                
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
        Welcome to InvestForge!
        
        Hi {user.first_name or 'there'},
        
        Welcome to InvestForge! We're thrilled to have you join our community of smart investors using AI-powered analysis.
        
        Get started with your {user.plan.title()} plan:
        - Run your first stock analysis
        - Explore technical indicators  
        - Get AI-powered insights
        
        Launch the app: https://app.investforge.io
        
        Questions? We're here to help!
        
        Happy investing!
        The InvestForge Team
        """
        
        return send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
        
    except Exception as e:
        print(f"Send welcome email internal error: {str(e)}")
        return False


def send_password_reset_email(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Send password reset email."""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        
        if not email:
            return error_response("Email is required", 400)
        
        # Get user by email
        user_data = db.get_user_by_email(email)
        if not user_data:
            # For security, return success even if user doesn't exist
            return success_response(
                message="If an account with that email exists, a password reset link has been sent"
            )
        
        user = User(user_data)
        
        # In production, generate a secure reset token
        # For now, using a simple approach
        reset_token = "demo-reset-token"  # Would be a secure JWT token
        
        subject = "Reset Your InvestForge Password"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #FF6B35;">Reset Your Password</h2>
                
                <p>Hi {user.first_name or 'there'},</p>
                
                <p>We received a request to reset your InvestForge password. Click the button below to create a new password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://app.investforge.io/reset-password?token={reset_token}" style="background-color: #FF6B35; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p>This link will expire in 24 hours for security purposes.</p>
                
                <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
                
                <p>Best regards,<br>The InvestForge Team</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Reset Your Password
        
        Hi {user.first_name or 'there'},
        
        We received a request to reset your InvestForge password.
        
        Click this link to reset your password:
        https://app.investforge.io/reset-password?token={reset_token}
        
        This link will expire in 24 hours.
        
        If you didn't request this, please ignore this email.
        
        Best regards,
        The InvestForge Team
        """
        
        success = send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
        
        if success:
            return success_response(
                message="Password reset email sent successfully"
            )
        else:
            return server_error_response("Failed to send password reset email")
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Send password reset email error: {str(e)}")
        return server_error_response("Internal server error")


def send_email(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Send email using AWS SES."""
    try:
        from_email = "noreply@investforge.io"  # Must be verified in SES
        
        response = ses_client.send_email(
            Source=from_email,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Html': {'Data': html_body, 'Charset': 'UTF-8'},
                    'Text': {'Data': text_body, 'Charset': 'UTF-8'}
                }
            }
        )
        
        print(f"Email sent successfully to {to_email}. MessageId: {response['MessageId']}")
        return True
        
    except Exception as e:
        print(f"SES send email error: {str(e)}")
        return False


def send_notification_email(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Send notification email to user."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        subject = body.get('subject')
        message = body.get('message')
        email_type = body.get('type', 'notification')
        
        if not subject or not message:
            return error_response("Subject and message are required", 400)
        
        # Get user data
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        
        # Simple notification email template
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #FF6B35;">{subject}</h2>
                
                <p>Hi {user.first_name or 'there'},</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    {message}
                </div>
                
                <p>Best regards,<br>The InvestForge Team</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        {subject}
        
        Hi {user.first_name or 'there'},
        
        {message}
        
        Best regards,
        The InvestForge Team
        """
        
        success = send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
        
        if success:
            return success_response(
                message="Notification email sent successfully"
            )
        else:
            return server_error_response("Failed to send notification email")
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Send notification email error: {str(e)}")
        return server_error_response("Internal server error")