#!/usr/bin/env python3
"""
Migration script to initialize chat sessions table for existing users
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.auth_db import get_auth_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_chat_sessions():
    """Create initial chat sessions for existing users"""
    auth_db = get_auth_db()
    
    # Re-initialize database to ensure chat_sessions table exists
    auth_db._init_database()
    
    # Get all existing users
    users = auth_db.list_users(limit=1000)
    logger.info(f"Found {len(users)} users to migrate")
    
    # Create a default chat session for each user
    for user in users:
        try:
            # Check if user already has chat sessions
            existing_sessions = auth_db.get_user_chat_sessions(user.id)
            
            if not existing_sessions:
                # Create default session
                session = auth_db.create_chat_session(
                    user_id=user.id,
                    title="Daily Trading Day",
                    preview="Welcome to FNTX.ai! Start chatting to explore AI-powered trading."
                )
                logger.info(f"Created chat session for user {user.email}: {session['id']}")
            else:
                logger.info(f"User {user.email} already has {len(existing_sessions)} chat sessions")
                
        except Exception as e:
            logger.error(f"Failed to create session for user {user.email}: {e}")
    
    logger.info("Migration completed")

if __name__ == "__main__":
    migrate_chat_sessions()