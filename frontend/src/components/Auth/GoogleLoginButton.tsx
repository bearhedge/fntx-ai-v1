import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

declare global {
  interface Window {
    google: any;
  }
}

interface GoogleLoginButtonProps {
  className?: string;
}

export const GoogleLoginButton: React.FC<GoogleLoginButtonProps> = ({ className = '' }) => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const buttonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const initializeGoogleSignIn = () => {
      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
      
      if (!clientId || clientId === 'YOUR_GOOGLE_CLIENT_ID_HERE') {
        console.log('Google Client ID not configured, using demo mode');
        return;
      }

      if (window.google && buttonRef.current) {
        try {
          window.google.accounts.id.initialize({
            client_id: clientId,
            callback: handleCredentialResponse,
            auto_select: false,
            cancel_on_tap_outside: true,
          });

          window.google.accounts.id.renderButton(
            buttonRef.current,
            { 
              theme: 'outline',
              size: 'large',
              width: 280,
              text: 'signin_with',
              shape: 'rectangular',
              logo_alignment: 'left'
            }
          );
        } catch (err) {
          console.error('Failed to initialize Google Sign-In:', err);
        }
      }
    };

    const handleCredentialResponse = async (response: any) => {
      setIsLoading(true);
      setError('');
      
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8002';
        
        // Send the credential to our backend
        const res = await fetch(`${apiUrl}/api/auth/google`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ credential: response.credential }),
        });

        const data = await res.json();
        
        if (!res.ok) {
          throw new Error(data.detail || 'Authentication failed');
        }

        // Store the token and navigate
        if (data.token) {
          await login(data.token);
          // Navigate to user's personal page
          if (data.user?.email) {
            const username = data.user.email.split('@')[0].toLowerCase();
            navigate(`/${username}`);
          } else {
            navigate('/');
          }
        } else {
          throw new Error('No token received');
        }
      } catch (err) {
        console.error('Google login error:', err);
        setError(err instanceof Error ? err.message : 'Google sign-in failed');
      } finally {
        setIsLoading(false);
      }
    };

    // Wait for Google script to load
    const checkGoogleLoaded = setInterval(() => {
      if (window.google) {
        clearInterval(checkGoogleLoaded);
        initializeGoogleSignIn();
      }
    }, 100);

    return () => clearInterval(checkGoogleLoaded);
  }, [login, navigate]);

  const handleDemoLogin = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8002';
      
      // Use demo token
      const response = await fetch(`${apiUrl}/api/auth/google`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ credential: 'DEMO_GOOGLE_USER' }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }

      if (data.token) {
        await login(data.token);
        navigate('/');
      } else {
        throw new Error('No token received');
      }
    } catch (err) {
      console.error('Demo login error:', err);
      setError(err instanceof Error ? err.message : 'Demo sign-in failed');
    } finally {
      setIsLoading(false);
    }
  };

  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const isDemoMode = !clientId || clientId === 'YOUR_GOOGLE_CLIENT_ID_HERE';

  return (
    <div className={`flex flex-col items-center space-y-3 ${className}`}>
      {isDemoMode ? (
        <button
          onClick={handleDemoLogin}
          disabled={isLoading}
          className="flex items-center justify-center gap-3 w-full max-w-[280px] px-4 py-3 bg-white text-gray-700 rounded border border-gray-300 hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-700"></div>
          ) : (
            <>
              <svg className="w-5 h-5" viewBox="0 0 48 48">
                <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/>
                <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"/>
                <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"/>
                <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"/>
              </svg>
              <span className="text-sm font-medium">Sign in with Google (Demo)</span>
            </>
          )}
        </button>
      ) : (
        <div ref={buttonRef} className="google-signin-button"></div>
      )}
      
      {error && (
        <p className="text-xs text-red-500 text-center">{error}</p>
      )}
    </div>
  );
};