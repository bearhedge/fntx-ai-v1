#!/usr/bin/env python3
"""
Database initialization script for FNTX.ai
Creates and initializes the authentication database and ensures chat database exists.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def init_databases():
    """Initialize all required databases"""
    print("Initializing FNTX.ai databases...")
    
    try:
        # Initialize authentication database
        from backend.database.auth_db import get_auth_db
        auth_db = get_auth_db()
        print(f"✓ Authentication database initialized: {auth_db.db_path}")
        
        # Initialize chat database  
        from backend.database.chat_db import get_chat_db
        chat_db = get_chat_db()
        print(f"✓ Chat database initialized: {chat_db.db_path}")
        
        # Verify databases are working
        user_count = auth_db.count_users()
        print(f"✓ Authentication database verified ({user_count} users)")
        
        print("\n✅ All databases initialized successfully!")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    init_databases()