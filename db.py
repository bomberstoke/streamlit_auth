import sqlite3
from datetime import datetime

import bcrypt


# Adapter: Convert datetime object to ISO format string for SQLite storage
def adapt_datetime(dt):
    return dt.isoformat()


# Converter: Convert ISO format string from SQLite back to datetime object
def convert_datetime(s):
    return datetime.fromisoformat(s.decode("utf-8"))


# Register adapters and converters for datetime objects
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)


# Initialize the database and create tables if they do not exist
def init_db():
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    
    # Create users table
    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )"""
    )
    
    # Create sessions table
    c.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            username TEXT,
            expiry TIMESTAMP
        )"""
    )
    
    # Create roles table
    c.execute(
        """CREATE TABLE IF NOT EXISTS roles (
            role TEXT UNIQUE
        )"""
    )
    
    # Create user_roles table for many-to-many relationship
    c.execute(
        """CREATE TABLE IF NOT EXISTS user_roles (
            username TEXT,
            role TEXT,
            PRIMARY KEY (username, role),
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (role) REFERENCES roles(role)
        )"""
    )
    
    # Create pages table for dynamic page management
    c.execute(
        """CREATE TABLE IF NOT EXISTS pages (
            page_name TEXT UNIQUE,
            required_role TEXT,
            icon TEXT,
            enabled INTEGER,
            file_path TEXT,
            menu_order INTEGER DEFAULT 0
        )"""
    )
    
    # Create code_snippets table
    c.execute("""
        CREATE TABLE IF NOT EXISTS code_snippets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            code TEXT NOT NULL,
            language TEXT NOT NULL,
            tags TEXT,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert default roles if they don't exist
    c.execute("SELECT COUNT(*) FROM roles")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO roles (role) VALUES (?)", [("admin",), ("user",)])
    
    # Insert default pages if they don't exist
    default_pages = [
        ("Dashboard", "user", "📊", 1, "pages/dashboard.py", 1),
        ("User Profile", "user", "👤", 1, "pages/user_profile.py", 2),
        ("Edit Page", "admin", "✏️", 1, "pages/edit_page_file.py", 3),
        ("Code Snippets", "admin", "💻", 1, "pages/code_snippets.py", 4),
        ("Admin Panel", "admin", "⚙️", 1, "pages/admin_panel.py", 5),
    ]
    
    for page_name, required_role, icon, enabled, file_path, menu_order in default_pages:
        c.execute("SELECT COUNT(*) FROM pages WHERE page_name = ?", (page_name,))
        if c.fetchone()[0] == 0:
            c.execute(
                "INSERT INTO pages (page_name, required_role, icon, enabled, file_path, menu_order) VALUES (?, ?, ?, ?, ?, ?)",
                (page_name, required_role, icon, enabled, file_path, menu_order)
            )
    
    # Create admin user with password '1234' if it doesn't exist
    c.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
    if c.fetchone()[0] == 0:
        hashed = bcrypt.hashpw("1234".encode(), bcrypt.gensalt())
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", hashed))
        
        # Assign admin role to admin user if not already assigned
        c.execute("SELECT COUNT(*) FROM user_roles WHERE username = ? AND role = ?", ("admin", "admin"))
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO user_roles (username, role) VALUES (?, ?)", ("admin", "admin"))
    
    conn.commit()
    conn.close()
