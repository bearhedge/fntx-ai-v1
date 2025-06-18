"""
Authentication database module for FNTX.ai
Handles user storage and retrieval using SQLite
"""
import sqlite3
from pathlib import Path
from typing import Optional, List
import json
from datetime import datetime
import logging
from contextlib import contextmanager

from backend.models.user import User

logger = logging.getLogger(__name__)

class AuthDatabase:
    """Manages user authentication data in SQLite"""
    
    def __init__(self, db_path: str = "fntx_auth.db"):
        """
        Initialize authentication database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables if they don't exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    password_hash TEXT,
                    picture TEXT,
                    given_name TEXT,
                    family_name TEXT,
                    google_id TEXT UNIQUE,
                    created_at TEXT NOT NULL,
                    last_login TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Create index on email for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email 
                ON users(email)
            """)
            
            # Create index on google_id for OAuth lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_google_id 
                ON users(google_id)
            """)
            
            # Create chat_sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    preview TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 0,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Create index on user_id for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id 
                ON chat_sessions(user_id)
            """)
            
            # Create index on updated_at for sorting
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at 
                ON chat_sessions(updated_at)
            """)
            
            conn.commit()
            logger.info(f"Initialized auth database at {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        finally:
            if conn:
                conn.close()
    
    def create_user(self, user: User) -> User:
        """
        Create a new user in the database
        
        Args:
            user: User object to create
            
        Returns:
            Created user object
            
        Raises:
            ValueError: If user already exists
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO users (
                        id, email, name, password_hash, picture, given_name, 
                        family_name, google_id, created_at, last_login, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user.id,
                    user.email,
                    user.name,
                    user.password_hash,
                    user.picture,
                    user.given_name,
                    user.family_name,
                    user.google_id,
                    user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat(),
                    user.last_login.isoformat() if user.last_login else datetime.utcnow().isoformat(),
                    json.dumps({})  # Empty metadata for now
                ))
                conn.commit()
                logger.info(f"Created user: {user.email}")
                return user
                
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    raise ValueError(f"User already exists: {user.email}")
                raise
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            user_id: User ID to lookup
            
        Returns:
            User object if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_user(row)
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email
        
        Args:
            email: Email address to lookup
            
        Returns:
            User object if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_user(row)
            return None
    
    def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """
        Get user by Google ID
        
        Args:
            google_id: Google OAuth ID to lookup
            
        Returns:
            User object if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE google_id = ?", (google_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_user(row)
            return None
    
    def update_user(self, user: User) -> User:
        """
        Update existing user
        
        Args:
            user: User object with updated data
            
        Returns:
            Updated user object
            
        Raises:
            ValueError: If user doesn't exist
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users SET
                    email = ?,
                    name = ?,
                    picture = ?,
                    given_name = ?,
                    family_name = ?,
                    google_id = ?,
                    last_login = ?
                WHERE id = ?
            """, (
                user.email,
                user.name,
                user.picture,
                user.given_name,
                user.family_name,
                user.google_id,
                user.last_login.isoformat() if user.last_login else datetime.utcnow().isoformat(),
                user.id
            ))
            
            if cursor.rowcount == 0:
                raise ValueError(f"User not found: {user.id}")
            
            conn.commit()
            logger.info(f"Updated user: {user.email}")
            return user
    
    def update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp
        
        Args:
            user_id: User ID to update
            
        Returns:
            True if updated, False if user not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users SET last_login = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), user_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete user from database
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Deleted user: {user_id}")
                return True
            return False
    
    def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """
        List users with pagination
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of User objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            return [self._row_to_user(row) for row in cursor.fetchall()]
    
    def count_users(self) -> int:
        """
        Get total number of users
        
        Returns:
            Total user count
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]
    
    def _row_to_user(self, row: sqlite3.Row) -> User:
        """
        Convert database row to User object
        
        Args:
            row: SQLite row object
            
        Returns:
            User object
        """
        return User(
            id=row['id'],
            email=row['email'],
            name=row['name'],
            password_hash=row['password_hash'],
            picture=row['picture'],
            given_name=row['given_name'],
            family_name=row['family_name'],
            google_id=row['google_id'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
        )
    
    def close(self):
        """Close database connection (for cleanup)"""
        # SQLite connections are closed in context manager
        pass
    
    # Chat session management methods
    def create_chat_session(self, user_id: str, title: str, preview: str = "") -> dict:
        """
        Create a new chat session for a user
        
        Args:
            user_id: User ID
            title: Chat session title
            preview: Preview text (optional)
            
        Returns:
            Created chat session as dict
        """
        import uuid
        from datetime import datetime
        
        chat_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Set all other chats to inactive
            cursor.execute("""
                UPDATE chat_sessions 
                SET is_active = 0 
                WHERE user_id = ?
            """, (user_id,))
            
            # Create new active chat
            cursor.execute("""
                INSERT INTO chat_sessions (
                    id, user_id, title, preview, created_at, 
                    updated_at, is_active, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                chat_id, user_id, title, preview, now, now, 
                json.dumps({})
            ))
            
            conn.commit()
            
            return {
                'id': chat_id,
                'user_id': user_id,
                'title': title,
                'preview': preview,
                'created_at': now,
                'updated_at': now,
                'is_active': True
            }
    
    def get_user_chat_sessions(self, user_id: str, limit: int = 50) -> List[dict]:
        """
        Get chat sessions for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of sessions to return
            
        Returns:
            List of chat session dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM chat_sessions 
                WHERE user_id = ? 
                ORDER BY updated_at DESC 
                LIMIT ?
            """, (user_id, limit))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'title': row['title'],
                    'preview': row['preview'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'is_active': bool(row['is_active'])
                })
            
            return sessions
    
    def update_chat_session(self, chat_id: str, title: str = None, preview: str = None) -> bool:
        """
        Update a chat session
        
        Args:
            chat_id: Chat session ID
            title: New title (optional)
            preview: New preview (optional)
            
        Returns:
            True if updated, False if not found
        """
        from datetime import datetime
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query dynamically
            updates = []
            params = []
            
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            
            if preview is not None:
                updates.append("preview = ?")
                params.append(preview)
            
            updates.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            
            params.append(chat_id)
            
            cursor.execute(f"""
                UPDATE chat_sessions 
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            
            conn.commit()
            return cursor.rowcount > 0
    
    def set_active_chat_session(self, user_id: str, chat_id: str) -> bool:
        """
        Set a chat session as active for a user
        
        Args:
            user_id: User ID
            chat_id: Chat session ID to activate
            
        Returns:
            True if successful, False otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Deactivate all user's chats
            cursor.execute("""
                UPDATE chat_sessions 
                SET is_active = 0 
                WHERE user_id = ?
            """, (user_id,))
            
            # Activate the specified chat
            cursor.execute("""
                UPDATE chat_sessions 
                SET is_active = 1 
                WHERE id = ? AND user_id = ?
            """, (chat_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_chat_session(self, chat_id: str, user_id: str) -> bool:
        """
        Delete a chat session
        
        Args:
            chat_id: Chat session ID
            user_id: User ID (for security)
            
        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM chat_sessions 
                WHERE id = ? AND user_id = ?
            """, (chat_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0

# Singleton instance
_auth_db_instance = None

def get_auth_db() -> AuthDatabase:
    """Get singleton instance of AuthDatabase"""
    global _auth_db_instance
    if _auth_db_instance is None:
        _auth_db_instance = AuthDatabase()
    return _auth_db_instance