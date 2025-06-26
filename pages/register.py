import streamlit as st
from auth import register_user
import sqlite3

# Helper to fetch roles from the database
def get_roles():
    conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('SELECT role FROM roles')
    roles = [row[0] for row in c.fetchall()]
    conn.close()
    return roles

# Helper to assign a role to a user in user_roles table
def assign_role(username, role):
    conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO user_roles (username, role) VALUES (?, ?)', (username, role))
    conn.commit()
    conn.close()

# Registration page for new users
def register_page():
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
                st.error("Passwords do not match")
            elif register_user(username, password, "user"):
                assign_role(username, "user")
                st.success("Registration successful!")
            else:
                st.error("Username already exists") 