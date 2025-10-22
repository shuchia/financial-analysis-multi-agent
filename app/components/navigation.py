"""
InvestForge Navigation Component
Mobile-responsive navigation with hamburger menu
"""

import streamlit as st


def render_navigation():
    """Render responsive navigation bar with link-style navigation"""

    # Navigation HTML with hamburger menu
    nav_html = """
    <div class="investforge-nav">
        <div class="investforge-nav-brand">
            <span class="material-symbols-outlined">trending_up</span>
            InvestForge
        </div>

        <div class="investforge-nav-links">
            <a class="investforge-nav-link {portfolio_active}" id="nav-portfolio">
                <span class="material-symbols-outlined">pie_chart</span>
                Portfolio
            </a>
            <a class="investforge-nav-link {analysis_active}" id="nav-analysis">
                <span class="material-symbols-outlined">analytics</span>
                Analysis
            </a>
            <a class="investforge-nav-link {settings_active}" id="nav-settings">
                <span class="material-symbols-outlined">settings</span>
                Settings
            </a>
        </div>

        <div class="investforge-nav-actions">
            <button class="investforge-hamburger" id="hamburger-menu">
                <span></span>
                <span></span>
                <span></span>
            </button>
        </div>
    </div>

    <!-- Mobile Navigation Overlay -->
    <div class="investforge-nav-mobile-overlay" id="mobile-overlay">
        <div class="investforge-nav-mobile-menu">
            <div class="investforge-nav-mobile-header">
                <div class="investforge-nav-brand">
                    <span class="material-symbols-outlined">trending_up</span>
                    InvestForge
                </div>
                <button class="investforge-nav-mobile-close" id="close-menu">
                    ×
                </button>
            </div>
            <a class="investforge-nav-link {portfolio_active}" id="nav-portfolio-mobile">
                <span class="material-symbols-outlined">pie_chart</span>
                Portfolio
            </a>
            <a class="investforge-nav-link {analysis_active}" id="nav-analysis-mobile">
                <span class="material-symbols-outlined">analytics</span>
                Analysis
            </a>
            <a class="investforge-nav-link {settings_active}" id="nav-settings-mobile">
                <span class="material-symbols-outlined">settings</span>
                Settings
            </a>
        </div>
    </div>

    <script>
        // Hamburger menu toggle
        const hamburger = document.getElementById('hamburger-menu');
        const overlay = document.getElementById('mobile-overlay');
        const closeBtn = document.getElementById('close-menu');

        if (hamburger) {{
            hamburger.addEventListener('click', function() {{
                hamburger.classList.toggle('active');
                overlay.classList.toggle('active');
            }});
        }}

        if (closeBtn) {{
            closeBtn.addEventListener('click', function() {{
                hamburger.classList.remove('active');
                overlay.classList.remove('active');
            }});
        }}

        if (overlay) {{
            overlay.addEventListener('click', function(e) {{
                if (e.target === overlay) {{
                    hamburger.classList.remove('active');
                    overlay.classList.remove('active');
                }}
            }});
        }}

        // Navigation link handling
        function handleNavClick(page) {{
            const stateKey = 'nav_clicked';
            const stateValue = page;

            // Use Streamlit's component communication
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                key: stateKey,
                value: stateValue
            }}, '*');
        }}

        document.querySelectorAll('[id^="nav-"]').forEach(link => {{
            link.addEventListener('click', function(e) {{
                e.preventDefault();
                const page = this.id.replace('nav-', '').replace('-mobile', '');
                handleNavClick(page);
            }});
        }});
    </script>
    """

    # Determine active page
    current_page = st.session_state.get('current_page', 'portfolio')

    # Format nav HTML with active states
    nav_html = nav_html.format(
        portfolio_active='active' if current_page == 'portfolio' else '',
        analysis_active='active' if current_page == 'analysis' else '',
        settings_active='active' if current_page == 'settings' else ''
    )

    st.markdown(nav_html, unsafe_allow_html=True)


def get_current_page():
    """Get current page from session state or query params"""
    return st.session_state.get('current_page', 'portfolio')


def set_current_page(page):
    """Set current page in session state"""
    st.session_state.current_page = page
