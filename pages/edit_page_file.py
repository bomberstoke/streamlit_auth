import os
import streamlit as st
import sqlite3
from auth import verify_session
import streamlit_ace as st_ace
import time


def edit_page_page(cookies):
    # Clear modal state if the dialog was closed with the X
    if "show_save_confirm_modal" in st.session_state and not st.session_state.get("save_confirm_active"):
        st.session_state.pop("show_save_confirm_modal", None)

    # File selection and ace_key setup
    username, roles = verify_session(cookies)
    if not username or "admin" not in roles:
        st.toast("Access denied: Admin role required.", icon="❌")
        st.stop()

    st.title("Edit Page File")
    st.write("Select a page file to edit its contents. Changes are saved directly to the file.")

    # List .py files in the pages directory, excluding admin_panel.py, edit_page_file.py, login.py, register.py, dashboard.py, user_profile.py, code_snippets.py, and pages_manager.py
    page_files = [
        f for f in os.listdir("pages")
        if f.endswith(".py") and f not in ("admin_panel.py", "edit_page_file.py", "login.py", "register.py", "dashboard.py", "user_profile.py", "code_snippets.py", "pages_manager.py")
    ]
    if not page_files:
        st.toast("No editable page files found.", icon="ℹ️")
        return

    selected_file = st.selectbox("Select a page file", page_files, key="edit_page_file_select")
    file_path = os.path.join("pages", selected_file)
    ace_key = f"edit_page_file_content_ace_{selected_file}"
    saved_key = ace_key + "_saved"
    reload_count_key = ace_key + "_reload_count"

    # Load file content
    with open(file_path, "r", encoding="utf-8") as f:
        file_content = f.read()

    # Always initialize the Ace editor value, saved value, and reload counter in session_state if missing
    if ace_key not in st.session_state:
        st.session_state[ace_key] = file_content
    if saved_key not in st.session_state:
        st.session_state[saved_key] = file_content
    if reload_count_key not in st.session_state:
        st.session_state[reload_count_key] = 0
    if (
        "last_selected_file" not in st.session_state
        or st.session_state["last_selected_file"] != selected_file
    ):
        st.session_state[ace_key] = file_content
        st.session_state[saved_key] = file_content
        st.session_state[reload_count_key] = 0
        st.session_state["last_selected_file"] = selected_file

    # Handle reload_file flag before rendering the editor
    if st.session_state.get("reload_file"):
        st.session_state[ace_key] = st.session_state[saved_key]
        st.session_state[reload_count_key] += 1
        st.toast(f"Changes to {selected_file} discarded.", icon="⚠️")
        st.session_state.pop("reload_file")
        st.session_state["force_editor_reload"] = True

    ace_widget_key = f"{ace_key}_{st.session_state[reload_count_key]}"
    warning_placeholder = st.empty()

    # Render the editor first to get edited_content
    edited_content = st_ace.st_ace(
        value=st.session_state[ace_key],
        language="python",
        theme="monokai",
        key=ace_widget_key,
        height=400,
        font_size=13,
        tab_size=4,
        show_gutter=True,
        show_print_margin=False,
        wrap=True,
        auto_update=True,
    )

    # Detect unsaved changes based on the current editor content
    unsaved_changes = edited_content != st.session_state[saved_key]
    if unsaved_changes:
        warning_placeholder.warning("You have unsaved changes. Please save or discard before leaving this page.")
    else:
        warning_placeholder.empty()

    # After rendering the editor, force rerun if needed to re-instantiate the widget
    if st.session_state.get("force_editor_reload"):
        st.session_state.pop("force_editor_reload")
        st.rerun()

    col_save, col_spacer, col_cancel = st.columns([1, 7, 1])
    with col_save:
        save_clicked = st.button("Save Changes")
    with col_cancel:
        cancel_clicked = st.button("Reload File")
    st.markdown("</div>", unsafe_allow_html=True)

    # Modal confirmation for saving changes
    if save_clicked:
        st.session_state["show_save_confirm_modal"] = True

    if st.session_state.get("show_save_confirm_modal"):
        st.dialog("Confirm Save Changes")(lambda: save_confirm_dialog(selected_file, file_path, edited_content, ace_key, saved_key))()

    # Always reset dialog active flag at the end of the function
    st.session_state["save_confirm_active"] = False

    # Cancel button logic: set reload_file flag and rerun
    if cancel_clicked:
        st.session_state["reload_file"] = True
        st.rerun()


def save_confirm_dialog(selected_file, file_path, edited_content, ace_key, saved_key):
    st.session_state["save_confirm_active"] = True
    st.write(f"Are you sure you want to save changes to **{selected_file}**?")
    col_confirm, col_spacer, col_cancel = st.columns([1, 3, 1])
    with col_confirm:
        if st.button("Save", key="confirm_save_changes"):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(edited_content)
                st.toast(f"Changes saved to {selected_file}.", icon="✅")
                st.session_state[ace_key] = edited_content
                st.session_state[saved_key] = edited_content
                time.sleep(1)
                st.session_state.pop("show_save_confirm_modal", None)
                st.rerun()
            except Exception as e:
                st.toast(f"Failed to save changes: {e}", icon="❌")
                st.session_state.pop("show_save_confirm_modal", None)
                st.rerun()
    with col_cancel:
        if st.button("Cancel", key="cancel_save_changes"):
            st.session_state.pop("show_save_confirm_modal", None)
            st.rerun() 