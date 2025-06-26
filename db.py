import sqlite3
from datetime import datetime
import bcrypt

# Adapter: Convert datetime object to ISO format string for SQLite storage
def adapt_datetime(dt):
    return dt.isoformat()

# Converter: Convert ISO format string from SQLite back to datetime object
def convert_datetime(s):
    return datetime.fromisoformat(s.decode('utf-8'))

# Register adapters and converters for datetime objects
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter('TIMESTAMP', convert_datetime)

# Initialize the database and create tables if they do not exist
def init_db():
    conn = sqlite3.connect('users.db', detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    # Create users table (keep role column for backward compatibility, but not used)
    c.execute(
        '''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )'''
    )
    # Create sessions table
    c.execute(
        '''CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            username TEXT,
            expiry TIMESTAMP
        )'''
    )
    # Create roles table
    c.execute(
        '''CREATE TABLE IF NOT EXISTS roles (
            role TEXT UNIQUE
        )'''
    )
    # Create user_roles table for many-to-many relationship
    c.execute(
        '''CREATE TABLE IF NOT EXISTS user_roles (
            username TEXT,
            role TEXT,
            PRIMARY KEY (username, role),
            FOREIGN KEY (username) REFERENCES users(username),
            FOREIGN KEY (role) REFERENCES roles(role)
        )'''
    )
    # Create pages table for dynamic page management
    c.execute(
        '''CREATE TABLE IF NOT EXISTS pages (
            page_name TEXT UNIQUE,
            required_role TEXT,
            icon TEXT,
            enabled INTEGER,
            file_path TEXT
        )'''
    )
    # Initialize default roles if empty
    c.execute('SELECT COUNT(*) FROM roles')
    if c.fetchone()[0] == 0:
        c.executemany('INSERT INTO roles (role) VALUES (?)', [("admin",), ("user",)])
    # Initialize default pages if empty
    c.execute('SELECT COUNT(*) FROM pages')
    if c.fetchone()[0] == 0:
        c.executemany('INSERT INTO pages (page_name, required_role, icon, enabled, file_path) VALUES (?, ?, ?, ?, ?)', [
            ("Dashboard", "user", "🏠", 1, "pages/dashboard.py"),
            ("User Profile", "user", "👤", 1, "pages/user_profile.py"),
            ("Admin Panel", "admin", "🔐", 1, "pages/admin_panel.py")
        ])
    conn.commit()

    # Auto-create admin user with password '1234' if not exists
    c.execute('SELECT COUNT(*) FROM users WHERE username = ?', ("admin",))
    if c.fetchone()[0] == 0:
        hashed = bcrypt.hashpw("1234".encode(), bcrypt.gensalt())
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', ("admin", hashed))
        # Assign admin role
        c.execute('INSERT OR IGNORE INTO user_roles (username, role) VALUES (?, ?)', ("admin", "admin"))
        conn.commit()
    conn.close() 