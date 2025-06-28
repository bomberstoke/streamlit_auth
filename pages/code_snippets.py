import sqlite3
import streamlit as st
from auth import verify_session
import time


def code_snippets_page(cookies):
    # Add custom CSS for max-width
    st.markdown("""
    <style>
    section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {
        max-width: 90%;
    }
    </style>
    """, unsafe_allow_html=True)
    # Add custom CSS to reduce whitespace at top
    st.markdown("""
    <style>
        .block-container {
           padding-top: 0rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    username, roles = verify_session(cookies)
    if not username:
        st.error("Please login to access this page.")
        st.stop()

    st.title("Code Snippets")
    st.write("Manage and organize your code snippets for quick reference.")

    # Create tabs for different operations
    tabs = st.tabs(["View Snippets", "Add New Snippet", "Edit Snippets"])

    # View Snippets tab
    with tabs[0]:
        display_snippets()

    # Add New Snippet tab
    with tabs[1]:
        add_new_snippet(cookies)

    # Edit Snippets tab
    with tabs[2]:
        edit_snippets()


def display_snippets():
    """Display all code snippets in a searchable, filterable list"""
    st.subheader("All Code Snippets")
    
    # Search functionality
    search_query = st.text_input("Search snippets by title, description, or tags", key="snippet_search")
    
    # Get snippets from database
    snippets = get_snippets(search_query)
    
    if not snippets:
        st.info("No code snippets found. Add your first snippet in the 'Add New Snippet' tab!")
        return
    
    # Display snippets
    for snippet in snippets:
        with st.expander(f"📝 {snippet['title']}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Description:** {snippet['description'] or 'No description'}")
                if snippet['tags']:
                    tags = snippet['tags'].split(',')
                    tag_text = " ".join([f"`{tag.strip()}`" for tag in tags])
                    st.markdown(f"**Tags:** {tag_text}")
                st.markdown(f"**Created by:** {snippet['created_by']} on {snippet['created_at'].strftime('%Y-%m-%d %H:%M')}")
            with col2:
                if snippet['updated_at'] != snippet['created_at']:
                    st.caption(f"Updated: {snippet['updated_at'].strftime('%Y-%m-%d %H:%M')}")
            
            # Display code with Python syntax highlighting
            st.code(snippet['code'], language="python")
            
            # Copy button
            if st.button("📋 Copy Code", key=f"copy_{snippet['id']}"):
                st.write("Code copied to clipboard!")
                st.toast("Code copied to clipboard!", icon="📋")


def add_new_snippet(cookies):
    """Add a new code snippet"""
    st.subheader("Add New Code Snippet")
    
    with st.form("add_snippet_form"):
        title = st.text_input("Title *", placeholder="Enter snippet title")
        description = st.text_area("Description", placeholder="Optional description of what this snippet does")
        
        code = st.text_area("Code *", height=300, placeholder="Paste your code here...")
        tags = st.text_input("Tags (comma-separated)", placeholder="e.g., function, utility, web, api")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("Save Snippet")
        with col2:
            clear = st.form_submit_button("Clear Form")
        
        if submit:
            if title and code:
                username, _ = verify_session(cookies)
                success = save_snippet(title, description, code, "Python", tags, username)
                if success:
                    st.toast("Snippet saved successfully!", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.toast("Failed to save snippet. Please try again.", icon="❌")
            else:
                st.toast("Please fill in all required fields (Title, Code).", icon="⚠️")
        
        if clear:
            st.rerun()


def edit_snippets():
    """Edit existing code snippets"""
    st.subheader("Edit Code Snippets")
    
    # Get all snippets for editing
    snippets = get_snippets("")
    
    if not snippets:
        st.info("No snippets available for editing.")
        return
    
    # Create a selectbox for choosing which snippet to edit
    snippet_options = [f"{s['title']}" for s in snippets]
    selected_snippet_text = st.selectbox("Select snippet to edit", snippet_options, key="edit_snippet_select")
    
    if selected_snippet_text:
        # Find the selected snippet
        selected_snippet = None
        for snippet in snippets:
            if f"{snippet['title']}" == selected_snippet_text:
                selected_snippet = snippet
                break
        
        if selected_snippet:
            with st.form("edit_snippet_form"):
                title = st.text_input("Title *", value=selected_snippet['title'], key="edit_title")
                description = st.text_area("Description", value=selected_snippet['description'] or "", key="edit_description")
                
                code = st.text_area("Code *", value=selected_snippet['code'], height=300, key="edit_code")
                tags = st.text_input("Tags (comma-separated)", value=selected_snippet['tags'] or "", key="edit_tags")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    update = st.form_submit_button("Update Snippet")
                with col2:
                    delete = st.form_submit_button("Delete Snippet", type="secondary")
                with col3:
                    cancel = st.form_submit_button("Cancel")
                
                if update:
                    if title and code:
                        success = update_snippet(selected_snippet['id'], title, description, code, "Python", tags)
                        if success:
                            st.toast("Snippet updated successfully!", icon="✅")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.toast("Failed to update snippet. Please try again.", icon="❌")
                    else:
                        st.toast("Please fill in all required fields.", icon="⚠️")
                
                if delete:
                    if st.session_state.get("confirm_delete") != selected_snippet['id']:
                        st.session_state["confirm_delete"] = selected_snippet['id']
                        st.toast("Click 'Delete Snippet' again to confirm deletion.", icon="⚠️")
                    else:
                        success = delete_snippet(selected_snippet['id'])
                        if success:
                            st.toast("Snippet deleted successfully!", icon="✅")
                            st.session_state.pop("confirm_delete", None)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.toast("Failed to delete snippet. Please try again.", icon="❌")
                
                if cancel:
                    st.session_state.pop("confirm_delete", None)
                    st.rerun()


def get_snippets(search_query=""):
    """Get snippets from database with optional filtering"""
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    
    query = """
        SELECT id, title, description, code, tags, created_by, created_at, updated_at 
        FROM code_snippets 
        WHERE 1=1
    """
    params = []
    
    if search_query:
        query += " AND (title LIKE ? OR description LIKE ? OR tags LIKE ?)"
        search_param = f"%{search_query}%"
        params.extend([search_param, search_param, search_param])
    
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
            'tags': row[4],
            'created_by': row[5],
            'created_at': row[6],
            'updated_at': row[7]
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