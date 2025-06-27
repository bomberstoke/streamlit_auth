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
    # Create users table (keep role column for backward compatibility, but not used)
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
    # Initialize default roles if empty
    c.execute("SELECT COUNT(*) FROM roles")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO roles (role) VALUES (?)", [("admin",), ("user",)])
    # Initialize default pages if empty
    c.execute("SELECT COUNT(*) FROM pages")
    if c.fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO pages (page_name, required_role, icon, enabled, file_path, menu_order) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("Dashboard", "user", "🏠", 1, "pages/dashboard.py", 1),
                ("User Profile", "user", "👤", 1, "pages/user_profile.py", 2),
                ("Admin Panel", "admin", "🔐", 1, "pages/admin_panel.py", 3),
                ("Edit Page File", "admin", "📝", 1, "pages/edit_page_file.py", 4),
            ],
        )
    conn.commit()

    # Migration: Add menu_order column if it doesn't exist
    try:
        c.execute("SELECT menu_order FROM pages LIMIT 1")
    except sqlite3.OperationalError:
        # Add menu_order column
        c.execute("ALTER TABLE pages ADD COLUMN menu_order INTEGER DEFAULT 0")
        # Set default order for existing pages
        c.execute("UPDATE pages SET menu_order = 1 WHERE page_name = 'Dashboard'")
        c.execute("UPDATE pages SET menu_order = 2 WHERE page_name = 'User Profile'")
        c.execute("UPDATE pages SET menu_order = 3 WHERE page_name = 'Admin Panel'")
        c.execute("UPDATE pages SET menu_order = 4 WHERE page_name = 'Edit Page File'")
        # Set order for other pages based on their current position
        c.execute("SELECT page_name FROM pages WHERE menu_order = 0 ORDER BY page_name")
        other_pages = c.fetchall()
        for i, (page_name,) in enumerate(other_pages, start=5):
            c.execute("UPDATE pages SET menu_order = ? WHERE page_name = ?", (i, page_name))
        conn.commit()

    # Auto-create admin user with password '1234' if not exists
    c.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
    if c.fetchone()[0] == 0:
        hashed = bcrypt.hashpw("1234".encode(), bcrypt.gensalt())
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)", ("admin", hashed)
        )
        # Assign admin role
        c.execute(
            "INSERT OR IGNORE INTO user_roles (username, role) VALUES (?, ?)",
            ("admin", "admin"),
        )
        conn.commit()
    conn.close()
