#!/usr/bin/env python3
"""
Script to clear all chat sessions for a fresh start
"""
import sqlite3
import os

# Database path
db_path = "/home/info/fntx-ai-v1/fntx_auth.db"

if os.path.exists(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check existing chat sessions
        cursor.execute("SELECT COUNT(*) FROM chat_sessions")
        count = cursor.fetchone()[0]
        print(f"Found {count} chat sessions")
        
        if count > 0:
            # Show existing sessions
            cursor.execute("SELECT id, user_id, title, preview FROM chat_sessions ORDER BY created_at DESC")
            sessions = cursor.fetchall()
            print("\nExisting chat sessions:")
            for session in sessions:
                print(f"  ID: {session[0]}, User: {session[1]}, Title: {session[2]}")
            
            # Clear all chat sessions
            cursor.execute("DELETE FROM chat_sessions")
            conn.commit()
            print(f"\n✅ Cleared all {count} chat sessions")
        else:
            print("No chat sessions found")
else:
    print(f"Database not found at {db_path}")