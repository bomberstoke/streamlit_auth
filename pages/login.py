import streamlit as st
import time

from auth import create_session, verify_user


# Login page for users
def login_page(cookies):
    st.title("Login")
    
    # Login form
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        # Validate credentials and create session
        if submit:
            username_lower = username.lower()
            role = verify_user(username_lower, password)
            if role:
                create_session(username_lower, cookies)
                st.toast("Login successful!", icon="✅")
                # Add a small delay to ensure cookies are saved
                time.sleep(0.5)
                st.rerun()
            else:
                st.toast("Invalid credentials", icon="❌")
