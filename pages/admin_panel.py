import os
import sqlite3
import time

import bcrypt
import streamlit as st
import streamlit_sortables as sortables

from auth import verify_session


# Dialog function for editing a page
@st.dialog("Edit Page")
def edit_page_dialog(current_name, current_role, current_icon, current_enabled):
    icon_options = [
        "📄",
        "🏠",
        "👤",
        "🔐",
        "⚙️",
        "📊",
        "📅",
        "📝",
        "📦",
        "💡",
        "⭐",
        "🔔",
        "📁",
        "🛒",
        "🗂️",
        "🧑‍💼",
    ]
    all_roles = get_roles()
    with st.form("edit_page_form"):
        new_name = st.text_input("Page Name", value=current_name, key="edit_page_name")
        new_icon = st.selectbox(
            "Icon (emoji)",
            icon_options,
            index=(
                icon_options.index(current_icon) if current_icon in icon_options else 0
            ),
            key="edit_page_icon",
        )
        if all_roles:
            # Check if current_role exists in available roles, if not use first available role
            current_role_index = 0
            if current_role in all_roles:
                current_role_index = all_roles.index(current_role)
            new_required_role = st.selectbox(
                "Required Role",
                all_roles,
                index=current_role_index,
                key="edit_page_role",
            )
        else:
            st.toast(
                "No roles available. Please add a role first in the Manage Roles tab.",
                icon="⚠️",
            )
            new_required_role = None
        new_enabled = st.checkbox(
            "Enabled", value=bool(current_enabled), key="edit_page_enabled"
        )
        col_save, col_spacer, col_cancel = st.columns([1, 3, 1])
        with col_save:
            submit_edit = st.form_submit_button("Save", disabled=not all_roles)
        with col_spacer:
            st.write("")
        with col_cancel:
            cancel_edit = st.form_submit_button("Cancel")
        if submit_edit:
            # Update the page in the DB
            conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            c.execute(
                "UPDATE pages SET page_name = ?, required_role = ?, icon = ?, enabled = ? WHERE page_name = ?",
                (new_name, new_required_role, new_icon, int(new_enabled), current_name),
            )
            conn.commit()
            conn.close()
            # If the name changed, also rename the file
            if new_name and current_name and new_name != current_name:
                old_file = f"pages/{str(current_name).lower().replace(' ', '_')}.py"
                new_file = f"pages/{str(new_name).lower().replace(' ', '_')}.py"
                if os.path.exists(old_file):
                    os.rename(old_file, new_file)
                    # Also rename the function inside the file
                    with open(new_file, "r") as f:
                        content = f.read()
                    old_func = f"def {str(current_name).lower().replace(' ', '_')}_page(cookies):"
                    new_func = (
                        f"def {str(new_name).lower().replace(' ', '_')}_page(cookies):"
                    )
                    if old_func in content:
                        content = content.replace(old_func, new_func, 1)
                        with open(new_file, "w") as f:
                            f.write(content)
                # Update file_path in DB
                conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
                c = conn.cursor()
                c.execute(
                    "UPDATE pages SET file_path = ? WHERE page_name = ?",
                    (new_file, new_name),
                )
                conn.commit()
                conn.close()
            st.toast(f"Page '{new_name}' updated.", icon="✅")
            del st.session_state["edit_page"]
            if "edit_page_active" in st.session_state:
                del st.session_state["edit_page_active"]
            st.rerun()
        elif cancel_edit:
            del st.session_state["edit_page"]
            if "edit_page_active" in st.session_state:
                del st.session_state["edit_page_active"]
            st.rerun()


# Dialog function for confirming page deletion
@st.dialog("Confirm Delete Page")
def confirm_delete_page_dialog(page_name):
    st.warning(
        f"Are you sure you want to delete the page '{page_name}'? This action cannot be undone."
    )
    col_a, col_b, col_c = st.columns([1, 3, 1])
    with col_a:
        if st.button("Delete", key="confirm_delete_yes"):
            # Remove from DB and delete file
            conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            c.execute("SELECT file_path FROM pages WHERE page_name = ?", (page_name,))
            row = c.fetchone()
            c.execute("DELETE FROM pages WHERE page_name = ?", (page_name,))
            conn.commit()
            conn.close()
            if row and row[0] and os.path.exists(row[0]):
                os.remove(row[0])
            st.toast(f"Page '{page_name}' deleted.", icon="✅")
            del st.session_state["confirm_delete_page"]
            time.sleep(2)
            st.rerun()
    with col_b:
        st.write("")
    with col_c:
        if st.button("Cancel", key="confirm_delete_cancel"):
            del st.session_state["confirm_delete_page"]
            if "edit_page" in st.session_state:
                del st.session_state["edit_page"]
            st.rerun()


# Admin panel page for managing users and sessions
def admin_panel_page(cookies):
    # Add custom CSS for max-width and padding
    st.markdown(
        """
    <style>
    section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {
        max-width: 90%;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
    <style>
        .block-container {
           padding-top: 0rem;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Clear dialog state if the dialog was closed with the X
    if "edit_page" in st.session_state and not st.session_state.get("edit_page_active"):
        del st.session_state["edit_page"]
    if "confirm_delete_page" in st.session_state and not st.session_state.get(
        "confirm_delete_page_active"
    ):
        del st.session_state["confirm_delete_page"]
    username, roles = verify_session(cookies)
    if username:
        if "admin" in roles:
            st.title("Admin Panel")
            st.write(f"Welcome to the Admin Panel, {username}!")
            st.write("This page is only accessible to users with the 'admin' role.")

            # Fetch all users from the database
            conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            c.execute("SELECT username FROM users")
            users = [(row[0],) for row in c.fetchall()]
            conn.close()

            # Create tabs for each admin section
            tabs = st.tabs([
                "Users",
                "User Sessions",
                "Manage Roles"
            ])

            # Users tab
            with tabs[0]:
                st.subheader("Users")
                # Search functionality for users (moved into this tab)
                search_query = st.text_input(
                    "Search users by username", "", key="user_search"
                )
                filtered_users = users
                if search_query:
                    filtered_users = [
                        user
                        for user in users
                        if search_query.lower() in user[0].lower()
                    ]
                header1, header2, header4 = st.columns([1, 3, 2])
                with header1:
                    st.markdown("**Username**")
                with header2:
                    st.markdown("**Roles**")
                with header4:
                    st.markdown("**Reset Password**")

                all_roles = []
                # Fetch all roles from the database
                conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
                c = conn.cursor()
                c.execute("SELECT role FROM roles")
                all_roles = [row[0] for row in c.fetchall()]
                conn.close()
                for user in filtered_users:
                    username = user[0]
                    col1, col2, col4 = st.columns([1, 3, 2])
                    with col1:
                        st.write(username)
                    with col2:
                        if username == "admin":
                            st.write(", ".join(get_user_roles(username)))
                        else:
                            user_roles = get_user_roles(username)
                            # Ensure 'user' is always included and cannot be removed
                            roles_for_multiselect = [
                                r for r in all_roles if r != "user"
                            ]
                            if "user" not in user_roles:
                                user_roles.append("user")
                            new_roles = st.multiselect(
                                "",
                                roles_for_multiselect,
                                default=[r for r in user_roles if r != "user"],
                                key=f"roles_{username}",
                                label_visibility="collapsed",
                            )
                            # Always add 'user' to the selected roles
                            new_roles.append("user")
                            if set(new_roles) != set(user_roles):
                                update_user_roles(username, new_roles)
                                st.toast(f"Roles for {username} updated.", icon="✅")
                                time.sleep(2)
                                st.rerun()
                    with col4:
                        if username == "admin":
                            st.write("")
                        else:
                            clear_pw_key = f"clear_pw_{username}"
                            pw_key = f"pw_updated_{username}"
                            pw_input_key = f"new_password_{username}"
                            if st.session_state.get(clear_pw_key):
                                st.session_state[pw_input_key] = ""
                                st.session_state[clear_pw_key] = False
                            new_password = st.text_input(
                                "",
                                type="password",
                                key=pw_input_key,
                                label_visibility="collapsed",
                                placeholder="Enter new password",
                            )
                            if new_password and not st.session_state.get(pw_key):
                                hashed = bcrypt.hashpw(
                                    new_password.encode(), bcrypt.gensalt()
                                )
                                conn = sqlite3.connect(
                                    "users.db", detect_types=sqlite3.PARSE_DECLTYPES
                                )
                                c = conn.cursor()
                                c.execute(
                                    "UPDATE users SET password = ? WHERE username = ?",
                                    (hashed, username),
                                )
                                conn.commit()
                                conn.close()
                                st.session_state[pw_key] = True
                                st.toast(f"Password for {username} updated.", icon="✅")
                                st.session_state[clear_pw_key] = True
                                time.sleep(2)
                                st.rerun()
                            elif not new_password and st.session_state.get(pw_key):
                                st.session_state[pw_key] = False

            # User Sessions tab
            with tabs[1]:
                st.subheader("User Sessions")
                current_session_id = cookies.get("session_id")
                conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
                c = conn.cursor()
                c.execute("SELECT username, session_id, expiry FROM sessions")
                all_sessions = c.fetchall()
                conn.close()

                import datetime
                from datetime import datetime as dt

                from dateutil import parser

                col1, col2, col3 = st.columns([3, 3, 2])
                with col1:
                    st.markdown("**Username**")
                with col2:
                    st.markdown("**Expiry**")
                with col3:
                    st.markdown("**Action**")

                for session in all_sessions:
                    username, session_id, expiry = session
                    is_current = session_id == current_session_id
                    col1, col2, col3 = st.columns([3, 3, 2])
                    with col1:
                        label = f"{username}"
                        if is_current:
                            label += " (Current Session)"
                        st.write(label)
                    with col2:
                        expiry_str = str(expiry)
                        try:
                            from dateutil import parser

                            expiry_dt = parser.parse(expiry_str)
                            expiry_display = expiry_dt.strftime("%d-%m-%Y %H:%M:%S")
                        except Exception:
                            expiry_display = expiry_str
                        st.write(expiry_display)
                    with col3:
                        if not is_current:
                            if st.button(f"Delete", key=f"del_sess_{session_id}"):
                                conn = sqlite3.connect(
                                    "users.db", detect_types=sqlite3.PARSE_DECLTYPES
                                )
                                c = conn.cursor()
                                c.execute(
                                    "DELETE FROM sessions WHERE session_id = ?",
                                    (session_id,),
                                )
                                conn.commit()
                                conn.close()
                                st.toast(f"Session {session_id} deleted.", icon="✅")
                                time.sleep(2)
                                st.rerun()
                        else:
                            st.write("")

            # Manage Roles tab
            with tabs[2]:
                st.subheader("Manage Roles")
                with st.form("add_role_form"):
                    new_role = st.text_input("Add new role", key="add_role_input")
                    add_role_submit = st.form_submit_button("Add Role")
                    if add_role_submit:
                        if not new_role or not new_role.strip():
                            st.toast("Please enter a role name.", icon="⚠️")
                        elif new_role not in roles:
                            try:
                                conn = sqlite3.connect(
                                    "users.db", detect_types=sqlite3.PARSE_DECLTYPES
                                )
                                c = conn.cursor()
                                c.execute(
                                    "INSERT INTO roles (role) VALUES (?)", (new_role,)
                                )
                                conn.commit()
                                conn.close()
                                st.toast(f"Role '{new_role}' added.", icon="✅")
                                time.sleep(2)
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.toast(f"Role '{new_role}' already exists.", icon="⚠️")
                        else:
                            st.toast(f"Role '{new_role}' already exists.", icon="⚠️")
                st.write("**Existing Roles:**")
                all_roles_db = get_roles()
                for r in all_roles_db:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(r)
                    with col2:
                        if r not in ("admin", "user", "pages"):
                            # Check if role is assigned to any page
                            conn = sqlite3.connect(
                                "users.db", detect_types=sqlite3.PARSE_DECLTYPES
                            )
                            c = conn.cursor()
                            c.execute(
                                "SELECT COUNT(*) FROM pages WHERE required_role = ?",
                                (r,),
                            )
                            is_assigned = c.fetchone()[0] > 0
                            conn.close()
                            if is_assigned:
                                st.button(
                                    f"Delete",
                                    key=f"del_role_{r}",
                                    disabled=True,
                                    help="Cannot delete: role is assigned to a page.",
                                )
                            else:
                                if st.button(f"Delete", key=f"del_role_{r}"):
                                    conn = sqlite3.connect(
                                        "users.db", detect_types=sqlite3.PARSE_DECLTYPES
                                    )
                                    c = conn.cursor()

                                    # Remove the role from all users first
                                    c.execute(
                                        "DELETE FROM user_roles WHERE role = ?", (r,)
                                    )

                                    # Delete the role from roles table
                                    c.execute("DELETE FROM roles WHERE role = ?", (r,))

                                    # Clean up orphaned roles in pages - set them to 'user' role
                                    c.execute(
                                        "UPDATE pages SET required_role = 'user' WHERE required_role = ?",
                                        (r,),
                                    )

                                    conn.commit()
                                    conn.close()
                                    st.toast(
                                        f"Role '{r}' deleted and removed from all users.",
                                        icon="✅",
                                    )
                                    time.sleep(2)
                                    st.rerun()
                        else:
                            st.write("")

        else:
            st.toast("Access denied: Admin role required.", icon="❌")
            st.stop()
    else:
        st.toast("Please login to access this page.", icon="❌")
        st.stop()

    # Always reset dialog active flags at the end of the function
    st.session_state["edit_page_active"] = False
    st.session_state["confirm_delete_page_active"] = False


# Helper to fetch roles from the database
def get_roles():
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("SELECT role FROM roles")
    roles = [row[0] for row in c.fetchall()]
    conn.close()
    return roles


# Helper to fetch roles for a user
def get_user_roles(username):
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("SELECT role FROM user_roles WHERE username = ?", (username,))
    user_roles = [row[0] for row in c.fetchall()]
    conn.close()
    return user_roles


# Helper to update roles for a user
def update_user_roles(username, new_roles):
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("DELETE FROM user_roles WHERE username = ?", (username,))
    c.executemany(
        "INSERT INTO user_roles (username, role) VALUES (?, ?)",
        [(username, r) for r in new_roles],
    )
    conn.commit()
    conn.close()
