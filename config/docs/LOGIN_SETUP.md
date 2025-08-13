# FNTX Trading Terminal - Login System Setup

## Overview
The FNTX Trading Terminal now includes a complete authentication system with a cyberpunk-themed matrix rain login screen.

## Features Implemented

### 1. Database Schema
- User authentication tables created in PostgreSQL
- Secure password hashing with bcrypt
- JWT token management for sessions
- User profiles and authentication tracking

### 2. Backend API
- `/api/auth/register` - Create new account
- `/api/auth/login` - Authenticate user
- `/api/auth/logout` - End session
- `/api/auth/refresh` - Refresh JWT token
- `/api/auth/profile` - Get user profile

### 3. Terminal UI
- **Matrix Login Screen** - Cyberpunk-themed login with falling matrix rain
- **Registration Screen** - Create new accounts with password strength indicator
- **Dashboard Screen** - Main trading interface after login
- **Session Management** - Automatic token refresh and persistent sessions

## Quick Start

### 1. Apply Database Migration
```bash
cd /home/info/fntx-ai-v1
psql -U postgres -d options_data -f backend/data/database/migrations/026_create_users_schema.sql
```

### 2. Install Dependencies
```bash
cd /home/info/fntx-ai-v1
pip install -e config/project/
```

### 3. Start the Backend API
```bash
cd /home/info/fntx-ai-v1/backend/api
python main.py
```

### 4. Run the Terminal UI
```bash
cd /home/info/fntx-ai-v1
python -m tui.main
```

## Usage

### Creating an Account
1. On the login screen, click "CREATE ACCOUNT"
2. Fill in:
   - Username (alphanumeric + underscore)
   - Email address
   - Full name (optional)
   - Password (must be strong)
3. Click "CREATE" to register

### Logging In
1. Enter your username or email
2. Enter your password
3. Press Enter or click "ENTER"

### Navigation
- `Tab` / `Shift+Tab` - Navigate between fields
- `Enter` - Submit form
- `Escape` - Go back/quit

## Security Features
- Passwords hashed with bcrypt
- JWT tokens for session management
- Automatic session persistence
- Token refresh for long sessions
- Authentication attempt logging
- IP-based security monitoring

## File Structure
```
/backend/
  /api/
    auth_api.py              # Authentication endpoints
  /core/auth/
    jwt_utils.py            # JWT token management
    password_utils.py       # Password hashing
  /data/database/migrations/
    026_create_users_schema.sql  # User tables

/tui/
  /screens/
    matrix_login_final.py   # Login screen
    matrix_register.py      # Registration screen
    dashboard.py           # Main dashboard
  /services/
    auth_service.py        # Authentication service
    api_client.py         # HTTP API client
  /components/
    glow_input.py         # Custom input widgets
  main.py                 # Application entry point
```

## Troubleshooting

### Database Connection Issues
Ensure PostgreSQL is running and the connection parameters in your .env file are correct:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=options_data
DB_USER=postgres
DB_PASSWORD=your_password
```

### API Connection Issues
Make sure the backend API is running on port 8080. Check the API_BASE_URL environment variable:
```
API_BASE_URL=http://localhost:8080
```

### Session Issues
Sessions are stored in `~/.fntx/session.json`. Delete this file to force a new login.

## Next Steps
- Integrate with existing trading functionality
- Add real-time portfolio data to dashboard
- Implement trading screens
- Add position management UI
- Create settings and preferences screens