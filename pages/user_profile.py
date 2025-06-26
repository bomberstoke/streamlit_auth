import streamlit as st
from auth import verify_session

# User profile page for authenticated users
def user_profile_page(cookies):
    username, roles = verify_session(cookies)
    if username:
        st.title("User Profile")
        st.write(f"Profile for {username}")
        role_display = (", ".join([r.capitalize() for r in roles]) if roles else "Unknown")
        st.write(f"Role(s): {role_display}")
        st.write("This page is accessible to all authenticated users (both admins and users).")

        st.subheader("Change Password")
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            submit = st.form_submit_button("Change Password")

            if submit:
                import sqlite3
                import bcrypt
                # Fetch current hashed password from DB
                conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                c = conn.cursor()
                c.execute("SELECT password FROM users WHERE username = ?", (username,))
                result = c.fetchone()
                if not result or not bcrypt.checkpw(current_password.encode(), result[0]):
                    st.error("Current password is incorrect.")
                elif new_password != confirm_password:
                    st.error("New passwords do not match.")
                elif len(new_password) < 4:
                    st.error("New password must be at least 4 characters.")
                else:
                    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
                    c.execute("UPDATE users SET password = ? WHERE username = ?", (hashed, username))
                    conn.commit()
                    st.success("Password changed successfully.")
                conn.close()
    else:
        st.error("Please login to access this page.")
        st.stop() 