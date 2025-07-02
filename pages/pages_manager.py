import os
import sqlite3
import time
import streamlit as st
import streamlit_sortables as sortables
from auth import verify_session

def pages_manager_page(cookies):
    username, roles = verify_session(cookies)
    if not username or ("pages" not in roles and "admin" not in roles):
        st.toast("Access denied: Pages or Admin role required.", icon="❌")
        st.stop()
    st.title("Pages Manager")
    st.write("Create, view, and organize dynamic pages.")
    
    # Always clear the add page modal state at the start of the page
    if "_add_page_modal_opened" not in st.session_state:
        st.session_state["show_add_page_modal"] = False
    st.session_state.pop("_add_page_modal_opened", None)
    
    # Add New Page Button
    if st.button("➕ Add New Page", key="open_add_page_modal"):
        st.session_state["show_add_page_modal"] = True
        st.session_state["_add_page_modal_opened"] = True
    
    # Modal dialog for adding a new page
    if st.session_state.get("show_add_page_modal"):
        add_new_page_modal(cookies)
    
    # --- View Pages Section ---
    st.header("View Pages")
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
            "Pages Manager",
        ):
            continue  # Skip core pages and Pages Manager itself
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
                    st.session_state.pop("confirm_delete_page", None)
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

    # --- Menu Order Section ---
    st.header("Menu Order")
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
    status_hash = hash(tuple((name, enabled, icon, required_role) for name, required_role, icon, enabled, _ in all_pages))
    sortable_key = f"menu_order_sortable_{status_hash}"
    # Show sortable list centered in the container
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        new_ordered_items = sortables.sort_items(
            sortable_items,
            direction="vertical",
            key=sortable_key,
        )
    # (col_left and col_right are left empty for centering effect)
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
                (idx, page_name),
            )
        conn.commit()
        conn.close()
        st.toast("Menu order updated!", icon="✅")
        time.sleep(1)
        st.rerun()

    # Always reset dialog active flags at the end of the function
    st.session_state["edit_page_active"] = False
    st.session_state["confirm_delete_page_active"] = False
    st.session_state["show_add_page_modal"] = False
    if "edit_page" in st.session_state:
        del st.session_state["edit_page"]
    if "edit_page_active" in st.session_state:
        del st.session_state["edit_page_active"]
    st.session_state.pop("confirm_delete_page", None)
    st.session_state.pop("confirm_delete_page_active", None)

# Helper to fetch roles from the database

def get_roles():
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("SELECT role FROM roles")
    roles = [row[0] for row in c.fetchall()]
    conn.close()
    return roles

# Dialog function for confirming page deletion (moved from admin_panel.py)
@st.dialog("Confirm Delete Page")
def confirm_delete_page_dialog(page_name):
    st.warning(
        f"Are you sure you want to delete the page '{page_name}'? This action cannot be undone."
    )
    col_a, col_b, col_c = st.columns([1, 3, 1])
    with col_a:
        if st.button("Delete"):
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
            st.session_state.pop("confirm_delete_page", None)
            time.sleep(2)
            st.rerun()
    with col_b:
        st.write("")
    with col_c:
        if st.button("Cancel"):
            st.session_state.pop("confirm_delete_page", None)
            if "edit_page" in st.session_state:
                del st.session_state["edit_page"]
            st.rerun()

# Modal dialog for adding a new page
@st.dialog("Add New Page")
def add_new_page_modal(cookies):
    all_roles = get_roles()
    # Fetch icon options from the database, ordered by icon_order
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("SELECT icon FROM icons ORDER BY icon_order, icon")
    icon_options = [row[0] for row in c.fetchall()]
    conn.close()
    with st.form("add_page_form"):
        new_page_name = st.text_input("Page Name", key="add_page_name")
        new_icon = st.selectbox(
            "Icon (emoji)", icon_options, index=0 if icon_options else None, key="add_page_icon"
        )
        if all_roles:
            new_required_role = st.selectbox(
                "Required Role", all_roles, key="add_page_role"
            )
        else:
            st.toast(
                "No roles available. Please add a role first in the Manage Roles tab.",
                icon="⚠️",
            )
            new_required_role = None
        new_role_input = st.text_input(
            "Or add a new role", key="add_page_new_role"
        )
        new_enabled = st.checkbox(
            "Enabled", value=True, key="add_page_enabled"
        )
        col_add, col_spacer, col_cancel = st.columns([1, 3, 1])
        with col_add:
            add_page_submit = st.form_submit_button("Add")
        with col_cancel:
            cancel_clicked = st.form_submit_button("Cancel")
        if add_page_submit:
            if not new_page_name or not new_page_name.strip():
                st.toast("Please enter a page name.", icon="⚠️")
            elif not all_roles:
                st.toast(
                    "No roles available. Please add a role first in the Manage Roles tab.",
                    icon="⚠️",
                )
            else:
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
                            st.toast(
                                f"Role '{new_role_input}' added.", icon="✅"
                            )
                            role_to_use = new_role_input
                            all_roles.append(new_role_input)
                        except sqlite3.IntegrityError:
                            st.toast(
                                f"Role '{new_role_input}' already exists.",
                                icon="⚠️",
                            )
                            role_to_use = new_role_input
                    else:
                        st.toast(
                            f"Role '{new_role_input}' already exists. Using it as required role.",
                            icon="ℹ️",
                        )
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
                    st.toast(
                        f"A page with the name '{new_page_name}' already exists.",
                        icon="⚠️",
                    )
                    conn.close()
                else:
                    # Create the file with a basic template if it doesn't exist
                    if not os.path.exists(file_path):
                        with open(file_path, "w") as f:
                            f.write(
                                f'''import streamlit as st
from auth import verify_session

def {new_page_name.lower().replace(' ', '_')}_page(cookies):
    username, _ = verify_session(cookies)
    st.title("{new_page_name}")
    st.write("This is the {new_page_name} page.")
    st.write(f"Current user: {{username}}")
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
                        
                        # After adding the new page, enforce menu order:
                        # 1. Get all pages except Pages Manager, Admin Panel, Code Snippets, and Edit Page
                        c.execute("SELECT page_name FROM pages WHERE page_name NOT IN ('Admin Panel', 'Pages Manager', 'Code Snippets', 'Edit Page') ORDER BY menu_order, page_name")
                        normal_pages = [row[0] for row in c.fetchall()]
                        # 2. Set their menu_order from 1 to N
                        for idx, page_name in enumerate(normal_pages, start=1):
                            c.execute("UPDATE pages SET menu_order = ? WHERE page_name = ?", (idx, page_name))
                        # 3. Set Edit Page to fourth from last, Code Snippets to third from last, Pages Manager to second to last, Admin Panel to last
                        c.execute("SELECT COUNT(*) FROM pages")
                        total_pages = c.fetchone()[0]
                        c.execute("UPDATE pages SET menu_order = ? WHERE page_name = 'Edit Page'", (total_pages - 3,))
                        c.execute("UPDATE pages SET menu_order = ? WHERE page_name = 'Code Snippets'", (total_pages - 2,))
                        c.execute("UPDATE pages SET menu_order = ? WHERE page_name = 'Pages Manager'", (total_pages - 1,))
                        c.execute("UPDATE pages SET menu_order = ? WHERE page_name = 'Admin Panel'", (total_pages,))
                        conn.commit()
                        
                        st.toast(f"Page '{new_page_name}' created.", icon="✅")
                        conn.close()
                        time.sleep(2)
                        st.session_state["show_add_page_modal"] = False
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.toast(
                            f"A page with the name '{new_page_name}' already exists.",
                            icon="⚠️",
                        )
                        conn.close()
        if cancel_clicked:
            st.session_state["show_add_page_modal"] = False
            st.rerun()

@st.dialog("Edit Page")
def edit_page_dialog(current_name, current_role, current_icon, current_enabled):
    # Fetch icon options from the database, ordered by icon_order
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("SELECT icon FROM icons ORDER BY icon_order, icon")
    icon_options = [row[0] for row in c.fetchall()]
    conn.close()
    all_roles = get_roles()
    with st.form("edit_page_form"):
        new_name = st.text_input("Page Name", value=current_name, key="edit_page_name")
        new_icon = st.selectbox(
            "Icon (emoji)",
            icon_options,
            index=(icon_options.index(current_icon) if current_icon in icon_options else 0) if icon_options else None,
            key="edit_page_icon",
        )
        if all_roles:
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
            conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            c.execute(
                "UPDATE pages SET page_name = ?, required_role = ?, icon = ?, enabled = ? WHERE page_name = ?",
                (new_name, new_required_role, new_icon, int(new_enabled), current_name),
            )
            conn.commit()
            conn.close()
            if new_name and current_name and new_name != current_name:
                old_file = f"pages/{str(current_name).lower().replace(' ', '_')}.py"
                new_file = f"pages/{str(new_name).lower().replace(' ', '_')}.py"
                if os.path.exists(old_file):
                    os.rename(old_file, new_file)
                    with open(new_file, "r") as f:
                        content = f.read()
                    old_func = f"def {str(current_name).lower().replace(' ', '_')}_page(cookies):"
                    new_func = f"def {str(new_name).lower().replace(' ', '_')}_page(cookies):"
                    if old_func in content:
                        content = content.replace(old_func, new_func, 1)
                        with open(new_file, "w") as f:
                            f.write(content)
                conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
                c = conn.cursor()
                c.execute(
                    "UPDATE pages SET file_path = ? WHERE page_name = ?",
                    (new_file, new_name),
                )
                conn.commit()
                conn.close()
            st.toast(f"Page '{new_name}' updated.", icon="✅")
            if "edit_page" in st.session_state:
                del st.session_state["edit_page"]
            if "edit_page_active" in st.session_state:
                del st.session_state["edit_page_active"]
            st.rerun()
        elif cancel_edit:
            if "edit_page" in st.session_state:
                del st.session_state["edit_page"]
            if "edit_page_active" in st.session_state:
                del st.session_state["edit_page_active"]
            st.rerun() 