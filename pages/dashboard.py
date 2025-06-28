import streamlit as st

from auth import verify_session


# Dashboard page for authenticated users
def dashboard_page(cookies):
    # Add custom CSS for max-width
    st.markdown("""
    <style>
    section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {
        max-width: 90%;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("""
    <style>
        .block-container {
           padding-top: 0rem;
        }
    </style>
    """, unsafe_allow_html=True)
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
