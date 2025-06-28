# Setting Up Google OAuth for FNTX AI on Localhost

## Quick Setup Guide

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the "Google Identity" API

### Step 2: Create OAuth 2.0 Credentials

1. Navigate to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. If prompted, configure the OAuth consent screen first:
   - User Type: External
   - App name: FNTX AI Development
   - User support email: Your email
   - Developer contact: Your email
   - Add scopes: email, profile, openid

4. For the OAuth client ID:
   - Application type: **Web application**
   - Name: FNTX AI Localhost
   - Authorized JavaScript origins:
     ```
     http://localhost:8080
     http://localhost:8081
     http://localhost:3000
     ```
   - NO redirect URIs needed for Google Identity Services

5. Click **Create** and copy your Client ID

### Step 3: Add Client ID to Your Project

1. Create/update `.env` file in the frontend directory:
   ```
   VITE_GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
   ```

2. Restart your frontend development server

### Step 4: Test the Integration

1. Navigate to http://localhost:8081/signin
2. Click "Sign in with Google"
3. Select your Google account
4. You should be logged into FNTX AI

## Troubleshooting

### "invalid_client" Error
- Make sure you added the correct localhost URLs to Authorized JavaScript origins
- Verify your Client ID is correctly copied
- Check that the .env file is in the frontend directory

### Button Not Appearing
- Check browser console for errors
- Ensure Google Identity Services script is loading
- Verify no ad blockers are interfering

### Development vs Production
- For production, add your domain to Authorized JavaScript origins
- Use environment variables to switch between dev/prod Client IDs
- Consider implementing proper token verification on the backend

## Security Notes
- Never commit your Google Client ID to version control
- The Client ID is safe to expose in frontend code (it's designed for that)
- Always verify tokens on the backend in production