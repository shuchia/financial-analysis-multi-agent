"""
Email utilities for sending authentication-related emails.
Uses AWS SES for email delivery.
"""

import os
import logging
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class EmailService:
    """Email service using AWS SES."""
    
    def __init__(self):
        """Initialize SES client."""
        self.ses_client = boto3.client('ses', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
        self.sender_email = os.environ.get('SENDER_EMAIL', 'noreply@investforge.io')
        self.app_name = os.environ.get('APP_NAME', 'InvestForge')
        self.app_url = os.environ.get('APP_URL', 'https://investforge.io')
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """Send email using SES."""
        try:
            message = {
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                }
            }
            
            if text_body:
                message['Body']['Text'] = {'Data': text_body, 'Charset': 'UTF-8'}
            
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={'ToAddresses': [to_email]},
                Message=message
            )
            
            logger.info(f"Email sent successfully to {to_email}, MessageId: {response['MessageId']}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {str(e)}")
            return False
    
    def get_email_template(self, template_name: str, **kwargs) -> tuple[str, str]:
        """Get email template with substitutions."""
        templates = {
            'password_reset': self._get_password_reset_template,
            'email_verification': self._get_email_verification_template,
            'security_alert': self._get_security_alert_template,
            'welcome': self._get_welcome_template
        }
        
        if template_name not in templates:
            raise ValueError(f"Unknown email template: {template_name}")
        
        return templates[template_name](**kwargs)
    
    def _get_password_reset_template(self, reset_token: str, user_name: str = 'User') -> tuple[str, str]:
        """Get password reset email template."""
        reset_url = f"{self.app_url}/reset-password?token={reset_token}"
        
        subject = f"Reset Your {self.app_name} Password"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                <h1 style="color: #2c3e50; margin-bottom: 10px;">{self.app_name}</h1>
                <h2 style="color: #34495e; margin-top: 0;">Password Reset Request</h2>
            </div>
            
            <div style="background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <p>Hello {user_name},</p>
                
                <p>We received a request to reset your password for your {self.app_name} account. If you made this request, please click the button below to reset your password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Reset Password</a>
                </div>
                
                <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
                <p style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; word-break: break-all; font-family: monospace; font-size: 12px;">{reset_url}</p>
                
                <p><strong>This link will expire in 1 hour for security reasons.</strong></p>
                
                <p>If you didn't request a password reset, please ignore this email or contact our support team if you have concerns about your account security.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This email was sent from {self.app_name}. If you have any questions, please contact our support team.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        {self.app_name} - Password Reset Request
        
        Hello {user_name},
        
        We received a request to reset your password for your {self.app_name} account. 
        
        To reset your password, please visit the following link:
        {reset_url}
        
        This link will expire in 1 hour for security reasons.
        
        If you didn't request a password reset, please ignore this email.
        
        Best regards,
        The {self.app_name} Team
        """
        
        return subject, html_body, text_body
    
    def _get_email_verification_template(self, verification_token: str, user_name: str = 'User') -> tuple[str, str]:
        """Get email verification template."""
        verification_url = f"{self.app_url}/verify-email?token={verification_token}"
        
        subject = f"Verify Your {self.app_name} Email Address"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Verification</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                <h1 style="color: #2c3e50; margin-bottom: 10px;">{self.app_name}</h1>
                <h2 style="color: #34495e; margin-top: 0;">Welcome! Please Verify Your Email</h2>
            </div>
            
            <div style="background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <p>Hello {user_name},</p>
                
                <p>Thank you for signing up for {self.app_name}! To complete your registration and start using our platform, please verify your email address by clicking the button below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" style="background-color: #27ae60; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Verify Email Address</a>
                </div>
                
                <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
                <p style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; word-break: break-all; font-family: monospace; font-size: 12px;">{verification_url}</p>
                
                <p>Once your email is verified, you'll have full access to all {self.app_name} features.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This email was sent from {self.app_name}. If you didn't create an account with us, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        {self.app_name} - Email Verification
        
        Hello {user_name},
        
        Thank you for signing up for {self.app_name}! 
        
        To complete your registration, please verify your email address by visiting:
        {verification_url}
        
        Once verified, you'll have full access to all {self.app_name} features.
        
        Best regards,
        The {self.app_name} Team
        """
        
        return subject, html_body, text_body
    
    def _get_security_alert_template(
        self,
        alert_type: str,
        details: Dict[str, Any],
        user_name: str = 'User'
    ) -> tuple[str, str]:
        """Get security alert email template."""
        alert_messages = {
            'account_lockout': {
                'subject': f"Security Alert: {self.app_name} Account Temporarily Locked",
                'title': 'Account Temporarily Locked',
                'message': f"Your account has been temporarily locked due to {details.get('attempts', 'multiple')} failed login attempts.",
                'action': f"The lockout will be automatically lifted at {details.get('locked_until', 'shortly')}. If this wasn't you, please contact our support team immediately."
            },
            'suspicious_activity': {
                'subject': f"Security Alert: Suspicious Activity on {self.app_name} Account",
                'title': 'Suspicious Activity Detected',
                'message': f"We detected unusual login activity on your account from {details.get('unique_ips', 'multiple')} different IP addresses.",
                'action': 'If this wasn\'t you, please change your password immediately and contact our support team.'
            }
        }
        
        alert = alert_messages.get(alert_type, {
            'subject': f"Security Alert: {self.app_name} Account",
            'title': 'Security Alert',
            'message': 'Unusual activity was detected on your account.',
            'action': 'Please review your account activity and contact support if needed.'
        })
        
        subject = alert['subject']
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Security Alert</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                <h1 style="color: #856404; margin-bottom: 10px;">⚠️ {self.app_name}</h1>
                <h2 style="color: #856404; margin-top: 0;">{alert['title']}</h2>
            </div>
            
            <div style="background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <p>Hello {user_name},</p>
                
                <p>{alert['message']}</p>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>What to do next:</strong><br>
                    {alert['action']}
                </div>
                
                <p><strong>If you have any concerns about your account security, please contact our support team immediately.</strong></p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{self.app_url}/support" style="background-color: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Contact Support</a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    This is an automated security alert from {self.app_name}. 
                    Time: {details.get('timestamp', 'Unknown')}<br>
                    IP Address: {details.get('ip_address', 'Unknown')}
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        {self.app_name} - Security Alert
        
        Hello {user_name},
        
        {alert['title']}
        
        {alert['message']}
        
        What to do next:
        {alert['action']}
        
        If you have any concerns, please contact our support team at {self.app_url}/support
        
        Time: {details.get('timestamp', 'Unknown')}
        IP Address: {details.get('ip_address', 'Unknown')}
        
        The {self.app_name} Security Team
        """
        
        return subject, html_body, text_body
    
    def _get_welcome_template(self, user_name: str = 'User') -> tuple[str, str]:
        """Get welcome email template."""
        subject = f"Welcome to {self.app_name}!"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                <h1 style="color: #2c3e50; margin-bottom: 10px;">🎉 Welcome to {self.app_name}!</h1>
                <h2 style="color: #34495e; margin-top: 0;">Your Financial Analysis Journey Starts Here</h2>
            </div>
            
            <div style="background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <p>Hello {user_name},</p>
                
                <p>Welcome to {self.app_name}! We're excited to have you on board and help you make smarter investment decisions with AI-powered financial analysis.</p>
                
                <h3 style="color: #2c3e50;">What you can do with {self.app_name}:</h3>
                <ul style="padding-left: 20px;">
                    <li>📊 <strong>AI-Powered Analysis:</strong> Get comprehensive stock analysis with our advanced AI models</li>
                    <li>🔍 <strong>Competitor Analysis:</strong> Compare stocks against their competitors</li>
                    <li>📈 <strong>Technical Analysis:</strong> Detailed charts and technical indicators</li>
                    <li>📰 <strong>Sentiment Analysis:</strong> Real-time market sentiment insights</li>
                    <li>⚠️ <strong>Risk Assessment:</strong> Understand the risks before you invest</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{self.app_url}/app" style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Start Analyzing →</a>
                </div>
                
                <h3 style="color: #2c3e50;">Need Help Getting Started?</h3>
                <p>Check out our <a href="{self.app_url}/docs" style="color: #3498db;">documentation</a> or <a href="{self.app_url}/support" style="color: #3498db;">contact our support team</a> if you have any questions.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    Happy investing!<br>
                    The {self.app_name} Team
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Welcome to {self.app_name}!
        
        Hello {user_name},
        
        Welcome to {self.app_name}! We're excited to help you make smarter investment decisions.
        
        What you can do:
        - AI-Powered stock analysis
        - Competitor comparisons
        - Technical analysis with charts
        - Real-time sentiment analysis
        - Risk assessment tools
        
        Get started: {self.app_url}/app
        Documentation: {self.app_url}/docs
        Support: {self.app_url}/support
        
        Happy investing!
        The {self.app_name} Team
        """
        
        return subject, html_body, text_body


# Global email service instance
email_service = EmailService()


def send_password_reset_email(email: str, reset_token: str, user_name: str = 'User') -> bool:
    """Send password reset email."""
    try:
        subject, html_body, text_body = email_service.get_email_template(
            'password_reset',
            reset_token=reset_token,
            user_name=user_name
        )
        return email_service.send_email(email, subject, html_body, text_body)
    except Exception as e:
        logger.error(f"Error sending password reset email: {str(e)}")
        return False


def send_verification_email(email: str, verification_token: str, user_name: str = 'User') -> bool:
    """Send email verification email."""
    try:
        subject, html_body, text_body = email_service.get_email_template(
            'email_verification',
            verification_token=verification_token,
            user_name=user_name
        )
        return email_service.send_email(email, subject, html_body, text_body)
    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        return False


def send_security_alert_email(
    email: str,
    subject: str,
    alert_type: str,
    details: Dict[str, Any],
    user_name: str = 'User'
) -> bool:
    """Send security alert email."""
    try:
        subject, html_body, text_body = email_service.get_email_template(
            'security_alert',
            alert_type=alert_type,
            details=details,
            user_name=user_name
        )
        return email_service.send_email(email, subject, html_body, text_body)
    except Exception as e:
        logger.error(f"Error sending security alert email: {str(e)}")
        return False


def send_welcome_email(email: str, user_name: str = 'User') -> bool:
    """Send welcome email to new users."""
    try:
        subject, html_body, text_body = email_service.get_email_template(
            'welcome',
            user_name=user_name
        )
        return email_service.send_email(email, subject, html_body, text_body)
    except Exception as e:
        logger.error(f"Error sending welcome email: {str(e)}")
        return False