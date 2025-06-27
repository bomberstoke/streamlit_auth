import streamlit as st

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
            role = verify_user(username, password)
            if role:
                create_session(username, cookies)
                st.toast("Login successful!", icon="✅")
                st.rerun()
            else:
                st.toast("Invalid credentials", icon="❌")
