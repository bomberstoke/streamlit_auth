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
            st.toast("No roles available. Please add a role first in the Manage Roles tab.", icon="⚠️")
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
                    new_func = f"def {str(new_name).lower().replace(' ', '_')}_page(cookies):"
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
    
    # Clear dialog state if the dialog was closed with the X
    if "edit_page" in st.session_state and not st.session_state.get("edit_page_active"):
        del st.session_state["edit_page"]
    if "confirm_delete_page" in st.session_state and not st.session_state.get("confirm_delete_page_active"):
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
            tabs = st.tabs(
                ["Users", "User Sessions", "Manage Roles", "New Page", "View Pages", "Menu Order"]
            )

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
                            roles_for_multiselect = [r for r in all_roles if r != 'user']
                            if 'user' not in user_roles:
                                user_roles.append('user')
                            new_roles = st.multiselect(
                                "",
                                roles_for_multiselect,
                                default=[r for r in user_roles if r != 'user'],
                                key=f"roles_{username}",
                                label_visibility="collapsed",
                            )
                            # Always add 'user' to the selected roles
                            new_roles.append('user')
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
                    if add_role_submit and new_role:
                        if new_role not in roles:
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
                        if r not in ("admin", "user"):
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
                                    c.execute("DELETE FROM user_roles WHERE role = ?", (r,))
                                    
                                    # Delete the role from roles table
                                    c.execute("DELETE FROM roles WHERE role = ?", (r,))
                                    
                                    # Clean up orphaned roles in pages - set them to 'user' role
                                    c.execute("UPDATE pages SET required_role = 'user' WHERE required_role = ?", (r,))
                                    
                                    conn.commit()
                                    conn.close()
                                    st.toast(f"Role '{r}' deleted and removed from all users.", icon="✅")
                                    time.sleep(2)
                                    st.rerun()
                        else:
                            st.write("")

            # New Page tab
            with tabs[3]:
                all_roles = get_roles()
                with st.form("add_page_form"):
                    new_page_name = st.text_input("Page Name", key="add_page_name")
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
                    new_icon = st.selectbox(
                        "Icon (emoji)", icon_options, index=0, key="add_page_icon"
                    )
                    if all_roles:
                        new_required_role = st.selectbox(
                            "Required Role", all_roles, key="add_page_role"
                        )
                    else:
                        st.toast("No roles available. Please add a role first in the Manage Roles tab.", icon="⚠️")
                        new_required_role = None
                    new_role_input = st.text_input(
                        "Or add a new role", key="add_page_new_role"
                    )
                    new_enabled = st.checkbox(
                        "Enabled", value=True, key="add_page_enabled"
                    )
                    add_page_submit = st.form_submit_button(
                        "Add Page", disabled=not all_roles
                    )
                    if add_page_submit and new_page_name:
                        # Determine the role to use
                        role_to_use = new_required_role
                        if new_role_input:
                            # Add new role if it doesn't exist
                            if new_role_input not in all_roles:
                                try:
                                    conn = sqlite3.connect(
                                        "users.db", detect_types=sqlite3.PARSE_DECLTYPES
                                    )
                                    c = conn.cursor()
                                    c.execute(
                                        "INSERT INTO roles (role) VALUES (?)",
                                        (new_role_input,),
                                    )
                                    conn.commit()
                                    conn.close()
                                    st.toast(f"Role '{new_role_input}' added.", icon="✅")
                                    role_to_use = new_role_input
                                    all_roles.append(new_role_input)
                                except sqlite3.IntegrityError:
                                    st.toast(f"Role '{new_role_input}' already exists.", icon="⚠️")
                                    role_to_use = new_role_input
                            else:
                                st.toast(f"Role '{new_role_input}' already exists. Using it as required role.", icon="ℹ️")
                                role_to_use = new_role_input
                        # Generate file path
                        file_path = (
                            f"pages/{new_page_name.lower().replace(' ', '_')}.py"
                        )
                        # Get the next available menu order
                        conn = sqlite3.connect(
                            "users.db", detect_types=sqlite3.PARSE_DECLTYPES
                        )
                        c = conn.cursor()
                        c.execute("SELECT MAX(menu_order) FROM pages")
                        max_order = c.fetchone()[0]
                        next_order = (max_order or 0) + 1
                        # Check for duplicate page name
                        c.execute(
                            "SELECT COUNT(*) FROM pages WHERE page_name = ?",
                            (new_page_name,),
                        )
                        if c.fetchone()[0] > 0:
                            st.toast(f"A page with the name '{new_page_name}' already exists.", icon="⚠️")
                            conn.close()
                        else:
                            # Create the file with a basic template if it doesn't exist
                            if not os.path.exists(file_path):
                                with open(file_path, "w") as f:
                                    f.write(
                                        f'''import streamlit as st

def {new_page_name.lower().replace(' ', '_')}_page(cookies):
    # Add custom CSS for max-width and padding
    st.markdown("""
    <style>
    section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {{
        max-width: 90%;
    }}
    </style>
    """, unsafe_allow_html=True)
    st.markdown("""
    <style>
        .block-container {{
           padding-top: 0rem;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    st.title("{new_page_name}")
    st.write("This is the {new_page_name} page.")
'''
                                    )
                            # Insert into pages
                            try:
                                c.execute(
                                    "INSERT INTO pages (page_name, required_role, icon, enabled, file_path, menu_order) VALUES (?, ?, ?, ?, ?, ?)",
                                    (
                                        new_page_name,
                                        role_to_use,
                                        new_icon,
                                        int(new_enabled),
                                        file_path,
                                        next_order,
                                    ),
                                )
                                conn.commit()
                                
                                # Move Admin Panel to the end of the menu
                                c.execute("SELECT MAX(menu_order) FROM pages")
                                max_order = c.fetchone()[0]
                                # Set Admin Panel to the highest order + 1 to ensure it's at the end
                                admin_panel_order = max_order + 1
                                c.execute("UPDATE pages SET menu_order = ? WHERE page_name = 'Admin Panel'", (admin_panel_order,))
                                
                                # Reorder all pages sequentially (excluding Admin Panel)
                                c.execute("SELECT page_name FROM pages WHERE page_name != 'Admin Panel' ORDER BY menu_order")
                                pages_to_reorder = c.fetchall()
                                for i, (page_name,) in enumerate(pages_to_reorder, start=1):
                                    c.execute("UPDATE pages SET menu_order = ? WHERE page_name = ?", (i, page_name))
                                
                                # Set Admin Panel to the end
                                c.execute("SELECT COUNT(*) FROM pages WHERE page_name != 'Admin Panel'")
                                total_pages = c.fetchone()[0]
                                c.execute("UPDATE pages SET menu_order = ? WHERE page_name = 'Admin Panel'", (total_pages + 1,))
                                
                                conn.commit()
                                
                                st.toast(f"Page '{new_page_name}' created.", icon="✅")
                                conn.close()
                                time.sleep(2)
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.toast(f"A page with the name '{new_page_name}' already exists.", icon="⚠️")
                                conn.close()

            # View Pages tab
            with tabs[4]:
                all_roles = []
                conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
                c = conn.cursor()
                c.execute(
                    "SELECT page_name, required_role, icon, enabled, file_path, menu_order FROM pages ORDER BY menu_order, page_name"
                )
                all_pages = c.fetchall()
                conn.close()
                # Add column headings
                header1, header2, header3, header4, header5, header6, header7, header8 = (
                    st.columns([3, 3, 2, 2, 2, 4, 2, 3])
                )
                with header1:
                    st.markdown("**Page Name**")
                with header2:
                    st.markdown("**Role**")
                with header3:
                    st.markdown("**Icon**")
                with header4:
                    st.markdown("**Status**")
                with header5:
                    st.markdown("**Order**")
                with header6:
                    st.markdown("**File Path**")
                with header7:
                    st.markdown("**Edit**")
                with header8:
                    st.markdown("**Delete**")
                for page_name, required_role, icon, enabled, file_path, menu_order in all_pages:
                    if page_name in (
                        "Dashboard",
                        "User Profile",
                        "Admin Panel",
                        "Edit Page",
                        "Code Snippets",
                    ):
                        continue  # Skip core pages
                    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(
                        [3, 3, 2, 2, 2, 4, 2, 3]
                    )
                    with col1:
                        st.write(page_name)
                    with col2:
                        st.write(required_role)
                    with col3:
                        st.write(icon)
                    with col4:
                        status_icon = "✅" if enabled else "❌"
                        st.write(status_icon)
                    with col5:
                        st.write(menu_order or "N/A")
                    with col6:
                        # Remove "pages/" prefix from file path for cleaner display
                        clean_file_path = file_path.replace("pages/", "") if file_path else file_path
                        st.write(clean_file_path)
                    with col7:
                        if st.button(f"Edit", key=f"edit_page_{page_name}"):
                            if "confirm_delete_page" in st.session_state:
                                del st.session_state["confirm_delete_page"]
                            st.session_state["edit_page"] = page_name
                            st.session_state["edit_page_active"] = True
                    with col8:
                        delete_key = f"del_page_{page_name}"
                        if st.button(f"Delete", key=delete_key):
                            st.session_state["confirm_delete_page"] = page_name

                # Confirmation dialog for deleting a page
                confirm_delete_page = st.session_state.get("confirm_delete_page")
                if confirm_delete_page:
                    # Set active flag when dialog is open
                    st.session_state["confirm_delete_page_active"] = True
                    confirm_delete_page_dialog(confirm_delete_page)
                else:
                    # Call the dialog if edit_page is set
                    edit_page = st.session_state.get("edit_page")
                    if edit_page:
                        # Set active flag when dialog is open
                        st.session_state["edit_page_active"] = True
                        # Fetch current values
                        conn = sqlite3.connect(
                            "users.db", detect_types=sqlite3.PARSE_DECLTYPES
                        )
                        c = conn.cursor()
                        c.execute(
                            "SELECT page_name, required_role, icon, enabled FROM pages WHERE page_name = ?",
                            (edit_page,),
                        )
                        row = c.fetchone()
                        conn.close()
                        if row:
                            (
                                current_name,
                                current_role,
                                current_icon,
                                current_enabled,
                            ) = row
                            edit_page_dialog(
                                current_name,
                                current_role,
                                current_icon,
                                current_enabled,
                            )

            # Menu Order tab
            with tabs[5]:
                st.subheader("Menu Order")
                st.write("Drag and drop to reorder pages in the menu.")
                
                # Fetch all pages ordered by current menu_order
                conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
                c = conn.cursor()
                c.execute(
                    "SELECT page_name, required_role, icon, enabled, menu_order FROM pages ORDER BY menu_order, page_name"
                )
                all_pages = c.fetchall()
                conn.close()
                
                # Prepare items for sortables
                sortable_items = [
                    f"{icon} {page_name} ({required_role}) {'✅' if enabled else '❌'}"
                    for page_name, required_role, icon, enabled, _ in all_pages
                ]
                page_names = [page_name for page_name, _, _, _, _ in all_pages]
                
                # Create a unique key based on the current state to force refresh when status changes
                status_hash = hash(tuple((name, enabled) for name, _, _, enabled, _ in all_pages))
                sortable_key = f"menu_order_sortable_{status_hash}"
                
                # Show sortable list
                new_ordered_items = sortables.sort_items(
                    sortable_items,
                    direction="vertical",
                    key=sortable_key,
                )
                
                # Check if the order has changed
                if new_ordered_items != sortable_items:
                    # Map new_ordered_items to page_names by their new order
                    new_page_order = []
                    for item in new_ordered_items:
                        # Find the original index by matching the page name and role, ignoring status
                        for i, original_item in enumerate(sortable_items):
                            # Extract page name and role from both items (ignore status)
                            if "(" in item and ")" in item:
                                item_parts = item.split("(")[0].strip()
                                item_role = item.split("(")[1].split(")")[0].strip()
                            else:
                                continue
                                
                            if "(" in original_item and ")" in original_item:
                                original_parts = original_item.split("(")[0].strip()
                                original_role = original_item.split("(")[1].split(")")[0].strip()
                            else:
                                continue
                            
                            # Match by page name and role (ignore status)
                            if item_parts == original_parts and item_role == original_role:
                                new_page_order.append(page_names[i])
                                break
                        else:
                            # Fallback: try to find by page name only
                            for i, page_name in enumerate(page_names):
                                if page_name in item:
                                    new_page_order.append(page_name)
                                    break
                    
                    # Update the database with new order
                    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
                    c = conn.cursor()
                    for idx, page_name in enumerate(new_page_order, start=1):
                        c.execute(
                            "UPDATE pages SET menu_order = ? WHERE page_name = ?",
                            (idx, page_name)
                        )
                    conn.commit()
                    conn.close()
                    st.toast("Menu order updated!", icon="✅")
                    time.sleep(1)
                    st.rerun()

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
