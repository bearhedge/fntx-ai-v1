# Google OAuth Setup Guide

This guide will help you set up Google OAuth authentication for the FNTX AI application.

## Prerequisites
- A Google account
- Access to Google Cloud Console

## Steps to Get Google OAuth Client ID

### 1. Go to Google Cloud Console
Visit [https://console.cloud.google.com/](https://console.cloud.google.com/)

### 2. Create a New Project (or select existing)
- Click on the project dropdown at the top
- Click "New Project"
- Enter a project name (e.g., "FNTX AI")
- Click "Create"

### 3. Enable Google Sign-In API
- In the left sidebar, go to "APIs & Services" > "Library"
- Search for "Google Identity Toolkit API" or "Google+ API"
- Click on it and press "Enable"

### 4. Configure OAuth Consent Screen
- Go to "APIs & Services" > "OAuth consent screen"
- Choose "External" user type
- Fill in the required fields:
  - App name: FNTX AI
  - User support email: your email
  - Developer contact: your email
- Add your domain to "Authorized domains" if you have one
- Save and continue through all steps

### 5. Create OAuth 2.0 Client ID
- Go to "APIs & Services" > "Credentials"
- Click "Create Credentials" > "OAuth client ID"
- Application type: "Web application"
- Name: "FNTX AI Web Client"
- Add Authorized JavaScript origins:
  - `http://localhost:8080` (for local development)
  - `http://35.194.231.94:8080` (your production URL)
  - Add any other domains you'll use
- Add Authorized redirect URIs (same as origins)
- Click "Create"

### 6. Copy Your Client ID
- A popup will show your Client ID and Client Secret
- Copy the Client ID (looks like: `123456789-abcdefg.apps.googleusercontent.com`)

### 7. Configure the Application
Edit `/home/info/fntx-ai-v1/frontend/.env`:
```
VITE_API_URL=http://localhost:8003
VITE_GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE
```

Replace `YOUR_CLIENT_ID_HERE` with your actual Client ID.

### 8. Rebuild and Restart
```bash
cd /home/info/fntx-ai-v1/frontend
npm run build
# Restart the server
```

## Testing
1. Visit your application
2. Click "Sign in with Google"
3. Select your Google account
4. You should be logged in!

## Troubleshooting
- If you see "Sign in with Google (Demo)", the Client ID is not configured
- Check browser console for errors
- Ensure your domain is added to authorized origins
- Make sure the Google Sign-In API is enabled

## Security Notes
- Never commit your Client ID to public repositories
- The Client ID is safe to expose in frontend code
- Keep your Client Secret private (not used in frontend)