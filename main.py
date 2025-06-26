import streamlit as st
from db import init_db
from streamlit_cookies_manager import EncryptedCookieManager
from auth import verify_session, clear_session
from pages.register import register_page
import pages.login as login_mod
import sqlite3
import importlib.util
import sys
import os

# Helper to get required role for a page
def get_required_role(page_name):
    conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('SELECT required_role FROM pages WHERE page_name = ?', (page_name,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# Helper to get all enabled pages from the database
def get_enabled_pages():
    conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('SELECT page_name, icon, file_path FROM page_roles WHERE enabled = 1')
    pages = c.fetchall()
    conn.close()
    return pages

# Helper to get all enabled pages with roles from the database
def get_enabled_pages_with_roles():
    conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('SELECT page_name, icon, file_path, required_role FROM pages WHERE enabled = 1')
    pages = c.fetchall()
    conn.close()
    return pages

# Helper to dynamically import a page function from a file
def import_page_function(file_path, page_name):
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    func_name = f"{page_name.lower().replace(' ', '_')}_page"
    return getattr(module, func_name, None)

# Main entry point for the Streamlit app

def main():
    # Initialize the database (create tables if not exist)
    init_db()

    # Set up encrypted cookies manager for session handling
    cookies = EncryptedCookieManager(
        prefix="myapp/cookies/",
        password="your-secure-password-here"
    )
    if not cookies.ready():
        st.stop()

    def login_page():
        login_mod.login_page(cookies)

    # Check if user is logged in and get their role(s)
    username, roles = verify_session(cookies)

    # Dynamically load enabled pages the user has access to
    enabled_pages = get_enabled_pages_with_roles()
    page_objs = []
    admin_panel_obj = None
    for page_name, icon, file_path, required_role in enabled_pages:
        # Skip login/register, handled separately
        if page_name in ("Login", "Register"):
            continue
        # Only show if user has the required role, or is admin
        if required_role and (roles is None or (required_role not in roles and "admin" not in roles)):
            continue
        # Import the page function
        page_func = import_page_function(file_path, page_name)
        if page_func is None:
            continue
        # Wrap with access control and unique function name
        def make_page_func(page_func, page_name):
            def wrapped_page(page_func=page_func, page_name=page_name):
                required_role = get_required_role(page_name)
                _, user_roles = verify_session(cookies)
                if required_role and (required_role not in user_roles and "admin" not in user_roles):
                    st.error(f"Access denied: {required_role.capitalize()} role required.")
                    st.stop()
                page_func(cookies)
            wrapped_page.__name__ = f"{page_name.lower().replace(' ', '_')}"
            return wrapped_page
        page_obj = st.Page(make_page_func(page_func, page_name), title=page_name, icon=icon)
        if page_name == "Admin Panel":
            admin_panel_obj = page_obj
        else:
            page_objs.append(page_obj)
    if admin_panel_obj:
        page_objs.append(admin_panel_obj)

    # Define navigation pages based on authentication status
    if username:
        role_display = (", ".join([r.capitalize() for r in roles]) if roles else "Unknown")
        st.sidebar.write(f"Welcome, {username} ({role_display})!")
        if st.sidebar.button("Logout"):
            clear_session(cookies)
            st.rerun()
        # Authenticated user pages
        pages = page_objs
    else:
        # Unauthenticated user pages
        pages = [
            st.Page(login_page, title="Login", icon="🔒"),
            st.Page(register_page, title="Register", icon="📝")
        ]

    # Set up and run navigation
    navigation = st.navigation(pages)
    navigation.run()

if __name__ == "__main__":
    main()