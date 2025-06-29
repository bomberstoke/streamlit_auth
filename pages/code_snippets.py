import sqlite3
import streamlit as st
from auth import verify_session
import time


def code_snippets_page(cookies):
    username, roles = verify_session(cookies)
    if not username:
        st.error("Please login to access this page.")
        st.stop()

    st.title("Code Snippets")
    st.write("Manage and organize your code snippets for quick reference.")

    # Always clear the add snippet modal state at the start of the page
    if "_add_snippet_modal_opened" not in st.session_state:
        st.session_state["show_add_snippet_modal"] = False
    st.session_state.pop("_add_snippet_modal_opened", None)

    # Add New Snippet Modal
    show_modal = st.session_state.get("show_add_snippet_modal", False)
    if st.button("➕ Add New Snippet", key="open_add_snippet_modal"):
        st.session_state["show_add_snippet_modal"] = True
        show_modal = True
    if show_modal:
        add_new_snippet_modal(cookies)

    # List all snippets
    snippets = get_snippets()
    if not snippets:
        st.info("No code snippets found. Add your first snippet above!")
        # Always clear modal state at the end of the function
        st.session_state["show_add_snippet_modal"] = False
        return

    for snippet in snippets:
        expanded = st.expander(f"📝 {snippet['title']}")
        with expanded:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Description:** {snippet['description'] or 'No description'}")
                st.markdown(f"**Created by:** {snippet['created_by']} on {snippet['created_at'].strftime('%Y-%m-%d %H:%M')}")
            with col2:
                if snippet['updated_at'] != snippet['created_at']:
                    st.caption(f"Updated: {snippet['updated_at'].strftime('%Y-%m-%d %H:%M')}")
            st.code(snippet['code'], language="python")
            # Edit button and modal
            if st.button("✏️ Edit", key=f"edit_{snippet['id']}"):
                st.session_state[f"edit_snippet_modal_{snippet['id']}"] = True
            if st.session_state.get(f"edit_snippet_modal_{snippet['id']}"):
                edit_snippet_dialog(snippet, cookies)

    # Always clear modal state at the end of the function
    st.session_state["show_add_snippet_modal"] = False
    # Also clear all edit_snippet_modal_{id} flags
    for snippet in snippets:
        st.session_state.pop(f"edit_snippet_modal_{snippet['id']}", None)


def edit_snippet_dialog(snippet, cookies):
    @st.dialog(f"Edit Snippet: {snippet['title']}")
    def modal():
        title = st.text_input("Title *", value=snippet['title'], key=f"edit_title_{snippet['id']}")
        description = st.text_area("Description", value=snippet['description'] or "", key=f"edit_description_{snippet['id']}")
        code = st.text_area("Code *", value=snippet['code'], height=300, key=f"edit_code_{snippet['id']}")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            update = st.button("Update Snippet", key=f"update_{snippet['id']}")
        with col2:
            delete = st.button("Delete Snippet", key=f"delete_{snippet['id']}")
        with col3:
            cancel = st.button("Cancel", key=f"cancel_{snippet['id']}")
        if update:
            if title and code:
                success = update_snippet(snippet['id'], title, description, code, "Python", None)
                if success:
                    st.toast("Snippet updated successfully!", icon="✅")
                    st.session_state.pop(f"edit_snippet_modal_{snippet['id']}", None)
                    st.rerun()
                else:
                    st.toast("Failed to update snippet. Please try again.", icon="❌")
            else:
                st.toast("Please fill in all required fields.", icon="⚠️")
        if delete:
            if st.session_state.get(f"confirm_delete_{snippet['id']}") != True:
                st.session_state[f"confirm_delete_{snippet['id']}"] = True
                st.toast("Click 'Delete Snippet' again to confirm deletion.", icon="⚠️")
            else:
                success = delete_snippet(snippet['id'])
                if success:
                    st.toast("Snippet deleted successfully!", icon="✅")
                    st.session_state.pop(f"edit_snippet_modal_{snippet['id']}", None)
                    st.session_state.pop(f"confirm_delete_{snippet['id']}", None)
                    st.rerun()
                else:
                    st.toast("Failed to delete snippet. Please try again.", icon="❌")
        if cancel:
            st.session_state.pop(f"edit_snippet_modal_{snippet['id']}", None)
            st.session_state.pop(f"confirm_delete_{snippet['id']}", None)
            st.rerun()
    modal()


def get_snippets(search_query=""):
    """Get snippets from database with optional filtering"""
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    
    query = """
        SELECT id, title, description, code, created_by, created_at, updated_at 
        FROM code_snippets 
        WHERE 1=1
    """
    params = []
    
    if search_query:
        query += " AND (title LIKE ? OR description LIKE ?)"
        search_param = f"%{search_query}%"
        params.extend([search_param, search_param])
    
    query += " ORDER BY updated_at DESC"
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    snippets = []
    for row in rows:
        snippets.append({
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'code': row[3],
            'created_by': row[4],
            'created_at': row[5],
            'updated_at': row[6]
        })
    
    return snippets


def save_snippet(title, description, code, language, tags, created_by):
    """Save a new snippet to the database"""
    try:
        conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        c.execute("""
            INSERT INTO code_snippets (title, description, code, language, tags, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, description, code, language, tags, created_by))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False


def update_snippet(snippet_id, title, description, code, language, tags):
    """Update an existing snippet"""
    try:
        conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        c.execute("""
            UPDATE code_snippets 
            SET title = ?, description = ?, code = ?, language = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (title, description, code, language, tags, snippet_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False


def delete_snippet(snippet_id):
    """Delete a snippet from the database"""
    try:
        conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        c.execute("DELETE FROM code_snippets WHERE id = ?", (snippet_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False


def add_new_snippet_modal(cookies):
    @st.dialog("Add New Code Snippet")
    def modal():
        title_key = "add_snippet_title"
        desc_key = "add_snippet_description"
        code_key = "add_snippet_code"
        title = st.text_input("Title *", placeholder="Enter snippet title", key=title_key)
        description = st.text_area("Description", placeholder="Optional description of what this snippet does", key=desc_key)
        code = st.text_area("Code *", height=300, placeholder="Paste your code here...", key=code_key)
        col1, col_spacer, col3 = st.columns([1, 4, 1])
        with col1:
            submit = st.button("Save", key="save_new_snippet")
        with col3:
            clear = st.button("Clear", key="clear_new_snippet")
        if submit:
            if title and code:
                username, _ = verify_session(cookies)
                success = save_snippet(title, description, code, "Python", None, username)
                if success:
                    st.toast("Snippet saved successfully!", icon="✅")
                    for k in [title_key, desc_key, code_key]:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.session_state["show_add_snippet_modal"] = False
                    st.rerun()
                else:
                    st.toast("Failed to save snippet. Please try again.", icon="❌")
            else:
                st.toast("Please fill in all required fields (Title, Code).", icon="⚠️")
        if clear:
            for k in [title_key, desc_key, code_key]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
    modal() 