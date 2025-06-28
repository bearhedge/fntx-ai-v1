# Google OAuth Setup Guide for FNTX AI

## Current Implementation
The application currently uses a mock Google OAuth implementation for development that allows you to test the Google login flow without setting up actual Google OAuth credentials.

When you click "Sign in with Google", it will:
1. Create a mock user with email: demo@gmail.com
2. Generate a JWT token
3. Log you into the application

## Setting Up Real Google OAuth

To enable real Google OAuth authentication:

### 1. Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the Google+ API

### 2. Create OAuth 2.0 Credentials
1. Go to APIs & Services > Credentials
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Web application"
4. Add authorized JavaScript origins:
   - http://localhost:8080
   - http://localhost:8081
   - http://localhost:3000
   - Your production domain
5. Add authorized redirect URIs (if needed)
6. Save and copy your Client ID

### 3. Update the Application
1. Create a `.env` file in the frontend directory if it doesn't exist
2. Add your Google Client ID:
   ```
   VITE_GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
   ```

### 4. Update GoogleLoginButton.tsx
Replace the mock implementation with the real Google Identity Services implementation:

```typescript
useEffect(() => {
  const script = document.createElement('script');
  script.src = 'https://accounts.google.com/gsi/client';
  script.async = true;
  script.defer = true;
  document.head.appendChild(script);

  script.onload = () => {
    if (window.google) {
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        callback: handleCredentialResponse,
        auto_select: false,
        cancel_on_tap_outside: true,
      });

      if (buttonRef.current) {
        window.google.accounts.id.renderButton(
          buttonRef.current,
          {
            theme: 'filled_black',
            size: 'large',
            text: 'signin_with',
            shape: 'rectangular',
            logo_alignment: 'left',
          }
        );
      }
    }
  };

  return () => {
    document.head.removeChild(script);
  };
}, []);
```

### 5. Update Backend
The backend `/api/auth/google` endpoint is already set up to handle real Google OAuth tokens. It will:
1. Verify the Google token
2. Extract user information
3. Create or update the user in the database
4. Return a JWT token

## Testing
1. Click "Sign in with Google" on the login page
2. Select your Google account
3. You should be logged into the application

## Security Notes
- Never commit your Google Client ID to version control
- Use environment variables for all sensitive configuration
- In production, ensure HTTPS is enabled
- Validate tokens on the backend before trusting user data