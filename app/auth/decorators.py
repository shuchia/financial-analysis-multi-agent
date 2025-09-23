"""
Authentication decorators for protecting routes and features.
"""

import functools
import streamlit as st
from typing import Callable, List, Optional
from .session_manager import SessionManager


def require_auth(func: Callable) -> Callable:
    """Decorator to require authentication for a function."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        session_manager = SessionManager()
        
        if not session_manager.is_authenticated():
            st.error("🔒 Please log in to access this feature.")
            st.stop()
        
        return func(*args, **kwargs)
    
    return wrapper


def require_plan(allowed_plans: List[str], upgrade_message: Optional[str] = None) -> Callable:
    """Decorator to require specific subscription plans."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            session_manager = SessionManager()
            
            # First check authentication
            if not session_manager.is_authenticated():
                st.error("🔒 Please log in to access this feature.")
                st.stop()
            
            # Check user plan
            user = session_manager.get_current_user()
            if not user:
                st.error("❌ Unable to verify user plan.")
                st.stop()
            
            current_plan = user.get('plan', 'free')
            
            if current_plan not in allowed_plans:
                default_message = f"🚀 This feature requires a {' or '.join(allowed_plans)} plan."
                st.warning(upgrade_message or default_message)
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("Upgrade Now", type="primary", use_container_width=True):
                        # Redirect to upgrade page or show upgrade modal
                        st.session_state.show_upgrade = True
                        st.rerun()
                
                st.stop()
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def track_usage(feature: str, cost: int = 1) -> Callable:
    """Decorator to track feature usage and enforce limits."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            session_manager = SessionManager()
            
            if not session_manager.is_authenticated():
                st.error("🔒 Please log in to track usage.")
                st.stop()
            
            user = session_manager.get_current_user()
            if not user:
                st.error("❌ Unable to track usage.")
                st.stop()
            
            current_plan = user.get('plan', 'free')
            
            # Check usage limits for free plan
            if current_plan == 'free':
                usage_key = f"{feature}_count"
                current_usage = user.get('usage', {}).get(usage_key, 0)
                
                # Define limits per feature
                limits = {
                    'analyses_count': 5,
                    'backtests_count': 2,
                    'portfolio_optimizations_count': 1
                }
                
                limit = limits.get(usage_key, 0)
                
                if current_usage + cost > limit:
                    st.error(f"📊 You've reached your monthly {feature} limit ({limit}).")
                    st.info("Upgrade to Growth for unlimited access!")
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button("Upgrade to Growth - $4.99/mo", type="primary", use_container_width=True):
                            st.session_state.show_upgrade = True
                            st.rerun()
                    
                    st.stop()
                
                # Update usage count
                if 'usage' not in user:
                    user['usage'] = {}
                user['usage'][usage_key] = current_usage + cost
                
                # Update session
                session_id = session_manager.get_current_session_id()
                session_manager.update_session(session_id, user)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def demo_mode_only(func: Callable) -> Callable:
    """Decorator to allow access only in demo mode."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        session_manager = SessionManager()
        user = session_manager.get_current_user()
        
        if not user or not user.get('demo_mode', False):
            st.error("🎮 This feature is only available in demo mode.")
            st.stop()
        
        return func(*args, **kwargs)
    
    return wrapper