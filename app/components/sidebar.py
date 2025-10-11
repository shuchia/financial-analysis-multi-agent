"""
Sidebar component with navigation and user info.
"""

import streamlit as st
from typing import Optional
from auth.session_manager import SessionManager
from utils.constants import PLANS, UI_CONFIG


def render_sidebar() -> str:
    """Render the application sidebar and return selected page."""
    
    session_manager = SessionManager()
    user = session_manager.get_current_user()
    
    if not user:
        return "login"
    
    with st.sidebar:
        # Header with logo
        try:
            logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
            with logo_col2:
                st.image("app/static/images/investforge-logo.png", width=80)
        except:
            st.markdown("⚒️", unsafe_allow_html=True)
            
        st.markdown("""
        <div style='text-align: center; padding: 0.5rem 0;'>
            <h3 class='gradient-text' style='margin: 0; font-size: 1.2rem;'>InvestForge</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # User info
        user_email = user.get('email', 'Unknown')
        user_plan = user.get('plan', 'free')
        
        st.markdown(f"**👤 User:** {user_email}")
        st.markdown(f"**💎 Plan:** {PLANS[user_plan]['name']}")
        
        # Plan-specific info
        if user_plan == 'free':
            usage = user.get('usage', {})
            analyses_used = usage.get('analyses_count', 0)
            analyses_limit = PLANS['free']['analyses_limit']
            
            progress = min(analyses_used / analyses_limit, 1.0)
            st.progress(progress)
            
            remaining = max(0, analyses_limit - analyses_used)
            st.markdown(f"**📊 Analyses:** {remaining}/{analyses_limit} left")
            
            if remaining <= 2:
                st.warning("⚠️ Running low on analyses!")
                if st.button("🚀 Upgrade Now", use_container_width=True, type="primary"):
                    st.session_state.show_upgrade_modal = True
                    st.rerun()
        
        elif user_plan in ['growth', 'pro']:
            st.success("✨ Unlimited access!")
        
        st.markdown("---")
        
        # Navigation
        pages = {
            "📊 Analysis": "analysis",
            "💼 Portfolio": "portfolio", 
            "📈 Backtesting": "backtesting",
            "🎯 Risk Assessment": "risk",
            "📚 Learn": "education",
            "⚙️ Settings": "settings"
        }
        
        selected_page = st.selectbox(
            "Navigation",
            list(pages.keys()),
            index=0,
            key="navigation"
        )
        
        # Feature availability hints
        if user_plan == 'free':
            st.markdown("---")
            st.markdown("### 🔒 Upgrade for:")
            st.markdown("""
            - ✨ Unlimited analyses
            - 📈 Backtesting
            - 💼 Portfolio optimization
            - 🎯 Risk simulations
            - 📞 Priority support
            """)
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            session_manager.logout()
            st.rerun()
        
        # Demo mode indicator
        if user.get('demo_mode', False):
            st.markdown("---")
            st.info("🎮 **Demo Mode**\nExplore with sample data!")
    
    return pages[selected_page]


def render_usage_widget(user_plan: str, usage: dict):
    """Render usage tracking widget for free users."""
    if user_plan != 'free':
        return
    
    st.markdown("### 📊 Usage This Month")
    
    limits = PLANS['free']
    
    # Analyses
    analyses_used = usage.get('analyses_count', 0)
    analyses_limit = limits['analyses_limit']
    analyses_progress = min(analyses_used / analyses_limit, 1.0)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress(analyses_progress)
    with col2:
        st.markdown(f"{analyses_used}/{analyses_limit}")
    
    st.caption("Stock Analyses")
    
    # Backtests
    backtests_used = usage.get('backtests_count', 0)
    backtests_limit = limits['backtests_limit']
    backtests_progress = min(backtests_used / backtests_limit, 1.0)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress(backtests_progress)
    with col2:
        st.markdown(f"{backtests_used}/{backtests_limit}")
    
    st.caption("Strategy Backtests")


def render_upgrade_prompt():
    """Render upgrade prompt for free users."""
    st.markdown("""
    ### 🚀 Ready to Level Up?
    
    **Growth Plan - $4.99/month**
    - ✅ Unlimited stock analyses
    - ✅ Portfolio optimization
    - ✅ Strategy backtesting
    - ✅ Risk simulations
    - ✅ Priority support
    
    **Less than a coffee a week!**
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Upgrade Now", type="primary", use_container_width=True):
            st.session_state.show_upgrade_modal = True
            st.rerun()
    
    with col2:
        if st.button("Maybe Later", use_container_width=True):
            st.session_state.show_upgrade_prompt = False