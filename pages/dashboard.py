import streamlit as st

from auth import verify_session


# Dashboard page for authenticated users
def dashboard_page(cookies):
    username, roles = verify_session(cookies)
    if username:
        role_display = (
            ", ".join([r.capitalize() for r in roles]) if roles else "Unknown"
        )
        st.title("Dashboard")
        st.write(f"Welcome to the Dashboard, {username}!")
        st.write(f"Role(s): {role_display}")
        st.write(
            "This page is accessible to all authenticated users (both admins and users)."
        )
    else:
        st.error("Please login to access this page.")
        st.stop()
