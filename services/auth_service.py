from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection

def register_user(username, email, password, role='customer'):
    """Registers a new user with hashed password."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        pw_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, pw_hash, role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {'success': True, 'user_id': user_id}
    except Exception as e:
        return {'success': False, 'error': str(e)}
    finally:
        conn.close()

def authenticate_user(username, password):
    """Authenticates user credentials and returns user dict or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def get_user_by_id(user_id):
    """Retrieves user by primary key."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, email, role, created_at FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None
