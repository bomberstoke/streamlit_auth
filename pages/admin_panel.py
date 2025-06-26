import streamlit as st
import sqlite3
import time
import bcrypt
from auth import verify_session
import os

# Dialog function for editing a page
@st.dialog("Edit Page")
def edit_page_dialog(current_name, current_role, current_icon, current_enabled):
    icon_options = ["📄", "🏠", "👤", "🔐", "⚙️", "📊", "📅", "📝", "📦", "💡", "⭐", "🔔", "📁", "🛒", "🗂️", "🧑‍💼"]
    all_roles = get_roles()
    with st.form("edit_page_form"):
        new_name = st.text_input("Page Name", value=current_name, key="edit_page_name")
        new_icon = st.selectbox("Icon (emoji)", icon_options, index=icon_options.index(current_icon) if current_icon in icon_options else 0, key="edit_page_icon")
        if all_roles:
            new_required_role = st.selectbox("Required Role", all_roles, index=all_roles.index(current_role) if current_role in all_roles else 0, key="edit_page_role")
        else:
            st.warning("No roles available. Please add a role first in the Manage Roles tab.")
            new_required_role = None
        new_enabled = st.checkbox("Enabled", value=bool(current_enabled), key="edit_page_enabled")
        submit_edit = st.form_submit_button("Save Changes", disabled=not all_roles)
        cancel_edit = st.form_submit_button("Cancel")
        if submit_edit:
            # Update the page in the DB
            conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            c.execute('UPDATE pages SET page_name = ?, required_role = ?, icon = ?, enabled = ? WHERE page_name = ?', (new_name, new_required_role, new_icon, int(new_enabled), current_name))
            conn.commit()
            conn.close()
            # If the name changed, also rename the file
            if new_name and current_name and new_name != current_name:
                old_file = f"pages/{str(current_name).lower().replace(' ', '_')}.py"
                new_file = f"pages/{str(new_name).lower().replace(' ', '_')}.py"
                if os.path.exists(old_file):
                    os.rename(old_file, new_file)
                # Update file_path in DB
                conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                c = conn.cursor()
                c.execute('UPDATE pages SET file_path = ? WHERE page_name = ?', (new_file, new_name))
                conn.commit()
                conn.close()
            st.success(f"Page '{new_name}' updated.")
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
    st.warning(f"Are you sure you want to delete the page '{page_name}'? This action cannot be undone.")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Yes, delete", key="confirm_delete_yes"):
            # Remove from DB and delete file
            conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            c.execute('SELECT file_path FROM pages WHERE page_name = ?', (page_name,))
            row = c.fetchone()
            c.execute('DELETE FROM pages WHERE page_name = ?', (page_name,))
            conn.commit()
            conn.close()
            if row and row[0] and os.path.exists(row[0]):
                os.remove(row[0])
            st.success(f"Page '{page_name}' deleted.")
            del st.session_state["confirm_delete_page"]
            time.sleep(2)
            st.rerun()
    with col_b:
        if st.button("Cancel", key="confirm_delete_cancel"):
            del st.session_state["confirm_delete_page"]
            if "edit_page" in st.session_state:
                del st.session_state["edit_page"]
            st.rerun()

# Admin panel page for managing users and sessions
def admin_panel_page(cookies):
    username, roles = verify_session(cookies)
    if username:
        if 'admin' in roles:
            st.title("Admin Panel")
            st.write(f"Welcome to the Admin Panel, {username}!")
            st.write("This page is only accessible to users with the 'admin' role.")

            # Fetch all users from the database
            conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            c.execute("SELECT username FROM users")
            users = [(row[0],) for row in c.fetchall()]
            conn.close()

            # Create tabs for each admin section
            tabs = st.tabs(["Users", "User Sessions", "Manage Roles", "New Page", "View Pages"])

            # Users tab
            with tabs[0]:
                st.subheader("Users")
                # Search functionality for users (moved into this tab)
                search_query = st.text_input("Search users by username", "", key="user_search")
                filtered_users = users
                if search_query:
                    filtered_users = [user for user in users if search_query.lower() in user[0].lower()]
                header1, header2, header4 = st.columns([1, 3, 2])
                with header1:
                    st.markdown("**Username**")
                with header2:
                    st.markdown("**Roles**")
                with header4:
                    st.markdown("**New Password**")

                all_roles = []
                # Fetch all roles from the database
                conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                c = conn.cursor()
                c.execute('SELECT role FROM roles')
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
                            new_roles = st.multiselect(
                                "",
                                all_roles,
                                default=user_roles,
                                key=f"roles_{username}",
                                label_visibility="collapsed"
                            )
                            if set(new_roles) != set(user_roles):
                                update_user_roles(username, new_roles)
                                st.toast(f"Roles for {username} updated.")
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
                                placeholder="Enter new password"
                            )
                            if new_password and not st.session_state.get(pw_key):
                                hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
                                conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                                c = conn.cursor()
                                c.execute("UPDATE users SET password = ? WHERE username = ?", (hashed, username))
                                conn.commit()
                                conn.close()
                                st.session_state[pw_key] = True
                                st.toast(f"Password for {username} updated.")
                                st.session_state[clear_pw_key] = True
                                time.sleep(2)
                                st.rerun()
                            elif not new_password and st.session_state.get(pw_key):
                                st.session_state[pw_key] = False

            # User Sessions tab
            with tabs[1]:
                st.subheader("User Sessions")
                current_session_id = cookies.get('session_id')
                conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
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
                            expiry_display = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            expiry_display = expiry_str
                        st.write(expiry_display)
                    with col3:
                        if not is_current:
                            if st.button(f"Delete", key=f"del_sess_{session_id}"):
                                conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                                c = conn.cursor()
                                c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                                conn.commit()
                                conn.close()
                                st.toast(f"Session {session_id} deleted.")
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
                    if add_role_submit and new_role:
                        if new_role not in roles:
                            try:
                                conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                                c = conn.cursor()
                                c.execute('INSERT INTO roles (role) VALUES (?)', (new_role,))
                                conn.commit()
                                conn.close()
                                st.success(f"Role '{new_role}' added.")
                                time.sleep(2)
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.warning(f"Role '{new_role}' already exists.")
                        else:
                            st.warning(f"Role '{new_role}' already exists.")
                st.write("**Existing Roles:**")
                all_roles_db = get_roles()
                for r in all_roles_db:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(r)
                    with col2:
                        if r not in ("admin", "user"):
                            # Check if role is assigned to any page
                            conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                            c = conn.cursor()
                            c.execute('SELECT COUNT(*) FROM pages WHERE required_role = ?', (r,))
                            is_assigned = c.fetchone()[0] > 0
                            conn.close()
                            if is_assigned:
                                st.button(f"Delete", key=f"del_role_{r}", disabled=True, help="Cannot delete: role is assigned to a page.")
                            else:
                                if st.button(f"Delete", key=f"del_role_{r}"):
                                    conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                                    c = conn.cursor()
                                    c.execute('DELETE FROM roles WHERE role = ?', (r,))
                                    conn.commit()
                                    conn.close()
                                    st.success(f"Role '{r}' deleted.")
                                    time.sleep(2)
                                    st.rerun()
                        else:
                            st.write("")

            # New Page tab
            with tabs[3]:
                all_roles = get_roles()
                with st.form("add_page_form"):
                    new_page_name = st.text_input("Page Name", key="add_page_name")
                    icon_options = ["📄", "🏠", "👤", "🔐", "⚙️", "📊", "📅", "📝", "📦", "💡", "⭐", "🔔", "📁", "🛒", "🗂️", "🧑‍💼"]
                    new_icon = st.selectbox("Icon (emoji)", icon_options, index=0, key="add_page_icon")
                    if all_roles:
                        new_required_role = st.selectbox("Required Role", all_roles, key="add_page_role")
                    else:
                        st.warning("No roles available. Please add a role first in the Manage Roles tab.")
                        new_required_role = None
                    new_role_input = st.text_input("Or add a new role", key="add_page_new_role")
                    new_enabled = st.checkbox("Enabled", value=True, key="add_page_enabled")
                    add_page_submit = st.form_submit_button("Add Page", disabled=not all_roles)
                    if add_page_submit and new_page_name:
                        # Determine the role to use
                        role_to_use = new_required_role
                        if new_role_input:
                            # Add new role if it doesn't exist
                            if new_role_input not in all_roles:
                                try:
                                    conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                                    c = conn.cursor()
                                    c.execute('INSERT INTO roles (role) VALUES (?)', (new_role_input,))
                                    conn.commit()
                                    conn.close()
                                    st.success(f"Role '{new_role_input}' added.")
                                    role_to_use = new_role_input
                                    all_roles.append(new_role_input)
                                except sqlite3.IntegrityError:
                                    st.warning(f"Role '{new_role_input}' already exists.")
                                    role_to_use = new_role_input
                            else:
                                st.info(f"Role '{new_role_input}' already exists. Using it as required role.")
                                role_to_use = new_role_input
                        # Generate file path
                        file_path = f"pages/{new_page_name.lower().replace(' ', '_')}.py"
                        # Check for duplicate page name
                        conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                        c = conn.cursor()
                        c.execute('SELECT COUNT(*) FROM pages WHERE page_name = ?', (new_page_name,))
                        if c.fetchone()[0] > 0:
                            st.warning(f"A page with the name '{new_page_name}' already exists.")
                            conn.close()
                        else:
                            # Create the file with a basic template if it doesn't exist
                            if not os.path.exists(file_path):
                                with open(file_path, "w") as f:
                                    f.write(f"import streamlit as st\n\ndef {new_page_name.lower().replace(' ', '_')}_page(cookies):\n    st.title(\"{new_page_name}\")\n    st.write(\"This is the {new_page_name} page.\")\n")
                            # Insert into pages
                            try:
                                c.execute('INSERT INTO pages (page_name, required_role, icon, enabled, file_path) VALUES (?, ?, ?, ?, ?)',
                                          (new_page_name, role_to_use, new_icon, int(new_enabled), file_path))
                                conn.commit()
                                st.success(f"Page '{new_page_name}' created.")
                                conn.close()
                                time.sleep(2)
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.warning(f"A page with the name '{new_page_name}' already exists.")
                                conn.close()

            # View Pages tab
            with tabs[4]:
                all_roles = []
                conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                c = conn.cursor()
                c.execute('SELECT page_name, required_role, icon, enabled, file_path FROM pages')
                all_pages = c.fetchall()
                conn.close()
                # Add column headings
                header1, header2, header3, header4, header5, header6, header7 = st.columns([3, 2, 1, 2, 4, 2, 2])
                with header1:
                    st.markdown("**Page Name**")
                with header2:
                    st.markdown("**Role**")
                with header3:
                    st.markdown("**Icon**")
                with header4:
                    st.markdown("**Status**")
                with header5:
                    st.markdown("**File Path**")
                with header6:
                    st.markdown("**Edit**")
                with header7:
                    st.markdown("**Delete**")
                for page_name, required_role, icon, enabled, file_path in all_pages:
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([3, 2, 1, 2, 4, 2, 2])
                    with col1:
                        st.write(page_name)
                    with col2:
                        st.write(required_role)
                    with col3:
                        st.write(icon)
                    with col4:
                        st.write("Enabled" if enabled else "Disabled")
                    with col5:
                        st.write(file_path)
                    with col6:
                        if page_name not in ("Dashboard", "User Profile", "Admin Panel"):
                            if st.button(f"Edit", key=f"edit_page_{page_name}"):
                                if "confirm_delete_page" in st.session_state:
                                    del st.session_state["confirm_delete_page"]
                                st.session_state["edit_page"] = page_name
                                st.session_state["edit_page_active"] = True
                        else:
                            st.write("")
                    with col7:
                        if page_name not in ("Dashboard", "User Profile", "Admin Panel"):
                            delete_key = f"del_page_{page_name}"
                            if st.button(f"Delete", key=delete_key):
                                st.session_state["confirm_delete_page"] = page_name
                        else:
                            st.write("")

                # Confirmation dialog for deleting a page
                confirm_delete_page = st.session_state.get("confirm_delete_page")
                if confirm_delete_page:
                    confirm_delete_page_dialog(confirm_delete_page)
                else:
                    # Call the dialog if edit_page is set
                    edit_page = st.session_state.get("edit_page")
                    if edit_page:
                        # Fetch current values
                        conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
                        c = conn.cursor()
                        c.execute('SELECT page_name, required_role, icon, enabled FROM pages WHERE page_name = ?', (edit_page,))
                        row = c.fetchone()
                        conn.close()
                        if row:
                            current_name, current_role, current_icon, current_enabled = row
                            edit_page_dialog(current_name, current_role, current_icon, current_enabled)
        else:
            st.error("Access denied: Admin role required.")
            st.stop()
    else:
        st.error("Please login to access this page.")
        st.stop()

# Helper to fetch roles from the database
def get_roles():
    conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('SELECT role FROM roles')
    roles = [row[0] for row in c.fetchall()]
    conn.close()
    return roles

# Helper to fetch roles for a user
def get_user_roles(username):
    conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('SELECT role FROM user_roles WHERE username = ?', (username,))
    user_roles = [row[0] for row in c.fetchall()]
    conn.close()
    return user_roles

# Helper to update roles for a user
def update_user_roles(username, new_roles):
    conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute('DELETE FROM user_roles WHERE username = ?', (username,))
    c.executemany('INSERT INTO user_roles (username, role) VALUES (?, ?)', [(username, r) for r in new_roles])
    conn.commit()
    conn.close() 