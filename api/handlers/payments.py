"""
Payment processing handlers using Stripe.
"""

import json
import os
import stripe
from typing import Dict, Any
from datetime import datetime

from utils.response import (
    success_response, error_response, unauthorized_response,
    not_found_response, server_error_response
)
from utils.database import db
from utils.auth import get_user_from_event
from models.user import User


# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')


def create_checkout_session(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Create Stripe checkout session for plan upgrade."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        plan = body.get('plan')
        success_url = body.get('success_url')
        cancel_url = body.get('cancel_url')
        
        if not plan:
            return error_response("Plan is required", 400)
        
        if not success_url or not cancel_url:
            return error_response("Success and cancel URLs are required", 400)
        
        # Validate plan
        plan_configs = {
            'growth': {
                'price_id': 'price_growth_monthly',  # Replace with actual Stripe price ID
                'amount': 499,  # $4.99 in cents
                'name': 'Growth Plan'
            },
            'pro': {
                'price_id': 'price_pro_monthly',  # Replace with actual Stripe price ID
                'amount': 999,  # $9.99 in cents
                'name': 'Pro Plan'
            }
        }
        
        if plan not in plan_configs:
            return error_response("Invalid plan", 400)
        
        # Get user data
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        
        # Check if user already has this plan or higher
        if plan == 'growth' and user.plan in ['growth', 'pro']:
            return error_response("User already has this plan or higher", 400)
        elif plan == 'pro' and user.plan == 'pro':
            return error_response("User already has this plan", 400)
        
        # Create or get Stripe customer
        customer_id = user.stripe_customer_id
        if not customer_id:
            try:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=f"{user.first_name} {user.last_name}".strip(),
                    metadata={'user_id': user_id}
                )
                customer_id = customer.id
                
                # Update user with Stripe customer ID
                db.update_user(user_id, {
                    'stripe_customer_id': customer_id,
                    'updated_at': datetime.utcnow().isoformat()
                })
                
            except stripe.error.StripeError as e:
                print(f"Stripe customer creation error: {str(e)}")
                return server_error_response("Failed to create customer")
        
        # Create checkout session
        try:
            plan_config = plan_configs[plan]
            
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': plan_config['name'],
                            'description': f'InvestForge {plan_config["name"]} subscription'
                        },
                        'unit_amount': plan_config['amount'],
                        'recurring': {'interval': 'month'}
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata={
                    'user_id': user_id,
                    'plan': plan,
                    'current_plan': user.plan
                }
            )
            
            return success_response(
                data={
                    'checkout_url': session.url,
                    'session_id': session.id
                },
                message="Checkout session created successfully"
            )
            
        except stripe.error.StripeError as e:
            print(f"Stripe checkout error: {str(e)}")
            return server_error_response("Failed to create checkout session")
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", 400)
    except Exception as e:
        print(f"Checkout session error: {str(e)}")
        return server_error_response("Internal server error")


def stripe_webhook(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle Stripe webhook events."""
    try:
        payload = event.get('body', '')
        sig_header = event.get('headers', {}).get('stripe-signature')
        
        if not sig_header:
            return error_response("Missing stripe-signature header", 400)
        
        # Verify webhook signature
        try:
            stripe_event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            return error_response("Invalid payload", 400)
        except stripe.error.SignatureVerificationError:
            return error_response("Invalid signature", 400)
        
        # Handle the event
        if stripe_event['type'] == 'checkout.session.completed':
            handle_checkout_completed(stripe_event['data']['object'])
        elif stripe_event['type'] == 'invoice.payment_succeeded':
            handle_payment_succeeded(stripe_event['data']['object'])
        elif stripe_event['type'] == 'customer.subscription.deleted':
            handle_subscription_canceled(stripe_event['data']['object'])
        elif stripe_event['type'] == 'invoice.payment_failed':
            handle_payment_failed(stripe_event['data']['object'])
        
        return success_response(message="Webhook handled successfully")
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return server_error_response("Webhook processing failed")


def handle_checkout_completed(session: Dict[str, Any]):
    """Handle successful checkout completion."""
    try:
        user_id = session['metadata'].get('user_id')
        new_plan = session['metadata'].get('plan')
        
        if not user_id or not new_plan:
            print("Missing user_id or plan in checkout session metadata")
            return
        
        # Update user plan
        updates = {
            'plan': new_plan,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        success = db.update_user(user_id, updates)
        if success:
            print(f"User {user_id} upgraded to {new_plan} plan")
            
            # Track upgrade event
            from handlers.analytics import track_plan_upgrade_event
            current_plan = session['metadata'].get('current_plan', 'free')
            track_plan_upgrade_event(user_id, current_plan, new_plan)
            
            # Send upgrade confirmation email
            from handlers.emails import send_upgrade_confirmation_email
            send_upgrade_confirmation_email(user_id, new_plan)
        else:
            print(f"Failed to update user {user_id} plan to {new_plan}")
            
    except Exception as e:
        print(f"Checkout completion handling error: {str(e)}")


def handle_payment_succeeded(invoice: Dict[str, Any]):
    """Handle successful recurring payment."""
    try:
        customer_id = invoice['customer']
        
        # Get user by Stripe customer ID
        # Note: You'd need to add a GSI on stripe_customer_id for this query
        # For now, we'll skip this implementation
        print(f"Payment succeeded for customer {customer_id}")
        
    except Exception as e:
        print(f"Payment succeeded handling error: {str(e)}")


def handle_subscription_canceled(subscription: Dict[str, Any]):
    """Handle subscription cancellation."""
    try:
        customer_id = subscription['customer']
        
        # Downgrade user to free plan
        # Note: You'd need to implement customer ID lookup
        print(f"Subscription canceled for customer {customer_id}")
        
    except Exception as e:
        print(f"Subscription cancellation handling error: {str(e)}")


def handle_payment_failed(invoice: Dict[str, Any]):
    """Handle failed payment."""
    try:
        customer_id = invoice['customer']
        
        # Notify user of payment failure
        # Note: You'd need to implement customer ID lookup
        print(f"Payment failed for customer {customer_id}")
        
    except Exception as e:
        print(f"Payment failure handling error: {str(e)}")


def get_billing_info(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Get user's billing information and subscription status."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get user data
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        
        billing_info = {
            'plan': user.plan,
            'stripe_customer_id': user.stripe_customer_id,
            'subscription_active': user.plan != 'free'
        }
        
        # If user has Stripe customer, get subscription details
        if user.stripe_customer_id:
            try:
                subscriptions = stripe.Subscription.list(
                    customer=user.stripe_customer_id,
                    status='active',
                    limit=1
                )
                
                if subscriptions.data:
                    subscription = subscriptions.data[0]
                    billing_info.update({
                        'subscription_id': subscription.id,
                        'current_period_end': subscription.current_period_end,
                        'cancel_at_period_end': subscription.cancel_at_period_end
                    })
                    
            except stripe.error.StripeError as e:
                print(f"Stripe subscription lookup error: {str(e)}")
        
        return success_response(
            data=billing_info,
            message="Billing information retrieved successfully"
        )
        
    except Exception as e:
        print(f"Get billing info error: {str(e)}")
        return server_error_response("Internal server error")


def cancel_subscription(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Cancel user's subscription."""
    try:
        # Extract user from authorizer context
        user_info = get_user_from_event(event)
        if not user_info:
            return unauthorized_response("Authentication required")
        
        user_id = user_info['user_id']
        
        # Get user data
        user_data = db.get_user(user_id)
        if not user_data:
            return not_found_response("User not found")
        
        user = User(user_data)
        
        if not user.stripe_customer_id:
            return error_response("No active subscription found", 400)
        
        try:
            # Get active subscription
            subscriptions = stripe.Subscription.list(
                customer=user.stripe_customer_id,
                status='active',
                limit=1
            )
            
            if not subscriptions.data:
                return error_response("No active subscription found", 400)
            
            subscription = subscriptions.data[0]
            
            # Cancel at period end
            stripe.Subscription.modify(
                subscription.id,
                cancel_at_period_end=True
            )
            
            return success_response(
                message="Subscription will be canceled at the end of the current billing period"
            )
            
        except stripe.error.StripeError as e:
            print(f"Stripe cancellation error: {str(e)}")
            return server_error_response("Failed to cancel subscription")
        
    except Exception as e:
        print(f"Cancel subscription error: {str(e)}")
        return server_error_response("Internal server error")