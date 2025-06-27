import sqlite3
from datetime import datetime, timedelta

import bcrypt


# Register a new user in the database
def register_user(username, password, role="user"):
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# Verify user credentials and return True if valid
def verify_user(username, password):
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and bcrypt.checkpw(password.encode(), result[0]):
        return True
    return False


# Create a new session for the user and store it in cookies
def create_session(username, cookies):
    import uuid

    session_id = str(uuid.uuid4())
    expiry = datetime.now() + timedelta(days=0.5)
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute(
        "INSERT INTO sessions (session_id, username, expiry) VALUES (?, ?, ?)",
        (session_id, username, expiry),
    )
    conn.commit()
    conn.close()
    cookies["session_id"] = session_id
    cookies.save()
    return session_id


# Verify the current session using cookies and clean up expired sessions
def verify_session(cookies):
    # Clean up expired sessions
    conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE expiry < ?", (datetime.now(),))
    conn.commit()
    session_id = cookies.get("session_id")
    if not session_id:
        conn.close()
        return None, []
    # Get the username for the current session_id
    c.execute("SELECT username FROM sessions WHERE session_id = ?", (session_id,))
    user_result = c.fetchone()
    if not user_result:
        conn.close()
        return None, []
    username = user_result[0]
    # Get all sessions for this user
    c.execute("SELECT expiry FROM sessions WHERE username = ?", (username,))
    sessions = c.fetchall()
    for session in sessions:
        if datetime.now() < session[0]:
            # Fetch all roles for this user
            c.execute("SELECT role FROM user_roles WHERE username = ?", (username,))
            roles = [row[0] for row in c.fetchall()]
            conn.close()
            return username, roles
    conn.close()
    return None, []


# Clear the current session from the database and cookies
def clear_session(cookies):
    session_id = cookies.get("session_id")
    if session_id:
        conn = sqlite3.connect("users.db", detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        cookies.pop("session_id", None)
        cookies.save()
