# Database Setup Guide for FNTX AI

## Issue Resolution Summary

The "unable to open database file" error when hitting `/api/auth/google` has been resolved. The issue was caused by a missing SQLite authentication database file.

## Database Configuration

### 1. Authentication Database (SQLite)
- **File**: `fntx_auth.db` 
- **Location**: Project root (`/home/info/fntx-ai-v1/fntx_auth.db`)
- **Purpose**: Stores user accounts, authentication data, and chat sessions
- **Tables**: 
  - `users` - User authentication and profile data
  - `chat_sessions` - User chat session management

### 2. Chat Database (JSON)
- **File**: `chat_history.json`
- **Location**: `/home/info/fntx-ai-v1/database/chat_history.json`
- **Purpose**: Stores chat message history
- **Format**: JSON with user-keyed message arrays

## Database Files Status

✅ **Authentication Database**: `/home/info/fntx-ai-v1/fntx_auth.db` (Created and configured)
✅ **Chat Database**: `/home/info/fntx-ai-v1/database/chat_history.json` (Exists)

## What Was Fixed

1. **Missing Database File**: The SQLite authentication database didn't exist
2. **Path Configuration**: Updated `auth_db.py` to use absolute paths instead of relative paths
3. **Auto-initialization**: Database tables are created automatically when accessed
4. **Fallback Handling**: Added robust path resolution with fallbacks

## Key Configuration Files

### `/home/info/fntx-ai-v1/backend/database/auth_db.py`
- **Updated**: Added automatic project root detection
- **Fallback**: Handles import errors gracefully
- **Path Resolution**: Uses absolute paths for database files

### `/home/info/fntx-ai-v1/backend/database/chat_db.py`
- **Status**: Already properly configured
- **Path**: Uses project root relative path

## Database Initialization

### Manual Initialization
```bash
# From project root
python3 backend/scripts/init_database.py
```

### Automatic Initialization
Databases are automatically created when accessed by the API server.

## API Endpoint Testing

The Google OAuth endpoint is now working:
```bash
curl -X POST http://localhost:8000/api/auth/google \
  -H "Content-Type: application/json" \
  -d '{"credential": "DEMO_GOOGLE_USER"}'
```

Expected response: JWT token and user data.

## Database Schema

### Users Table
```sql
CREATE TABLE users (
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
);
```

### Chat Sessions Table
```sql
CREATE TABLE chat_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    preview TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 0,
    metadata TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure the process has write access to the project root directory
2. **Path Issues**: Database uses absolute paths, so working directory changes shouldn't affect it
3. **Missing Dependencies**: The auth database has fallback handling for missing imports

### Verification Commands

```bash
# Check database files exist
ls -la /home/info/fntx-ai-v1/fntx_auth.db
ls -la /home/info/fntx-ai-v1/database/chat_history.json

# Test database access
python3 -c "from backend.database.auth_db import get_auth_db; print('Auth DB OK')"
python3 -c "from backend.database.chat_db import get_chat_db; print('Chat DB OK')"

# Test API endpoint
curl -X POST http://localhost:8000/api/auth/google -H "Content-Type: application/json" -d '{"credential": "DEMO_GOOGLE_USER"}'
```

## Next Steps

The database configuration is now complete and working. The authentication system can:
- Create new users via Google OAuth
- Store user sessions
- Handle chat history
- Manage user authentication tokens

All database operations are now functional for the FNTX AI application.