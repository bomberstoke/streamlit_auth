import sqlite3
import time

import streamlit as st

from auth import register_user, create_session


# Helper to assign a role to a user in user_roles table
def assign_role(username, role):
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO user_roles (username, role) VALUES (?, ?)",
        (username, role),
    )
    conn.commit()
    conn.close()


# Registration page for new users
def register_page(cookies):
    st.title("Register")
    # Registration form
    with st.form("register_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Register")

        # Form validation and registration logic
        if submit:
            if password != confirm_password:
                st.toast("Passwords do not match", icon="⚠️")
            elif register_user(username, password, "user"):
                assign_role(username, "user")
                create_session(username, cookies)
                st.toast("Registration successful! You are now logged in.", icon="✅")
                time.sleep(1)
                st.rerun()
            else:
                st.toast("Username already exists", icon="❌")
