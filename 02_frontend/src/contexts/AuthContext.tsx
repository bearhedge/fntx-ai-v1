import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import Cookies from 'js-cookie';

export interface User {
  id: string;
  email: string;
  name: string;
  picture: string;
  given_name: string;
  family_name: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credential: string) => Promise<void>;
  logout: () => void;
  signOut?: () => void; // Alias for logout
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  // Initialize authentication state from cookies
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = Cookies.get('fntx_token');
        
        if (token) {
          // Verify token with backend
          const apiUrl = import.meta.env.VITE_API_URL || '/api';
          const response = await fetch(`${apiUrl}/auth/verify`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token }),
          });

          if (response.ok) {
            const data = await response.json();
            if (data.valid && data.user) {
              setUser(data.user);
              return;
            }
          }
          
          // Token invalid, clear cookies
          Cookies.remove('fntx_user');
          Cookies.remove('fntx_token');
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
        // Clear invalid cookies
        Cookies.remove('fntx_user');
        Cookies.remove('fntx_token');
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (credential: string) => {
    try {
      setIsLoading(true);
      
      // Check if this is a JWT token (from email/password auth) or Google credential
      let token: string;
      let userData: User;
      
      if (credential.includes('.')) {
        // This looks like a JWT token from email/password auth
        token = credential;
        
        // Verify the token with backend to get user data
        const apiUrl = import.meta.env.VITE_API_URL || '/api';
        const verifyResponse = await fetch(`${apiUrl}/auth/verify`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token }),
        });

        if (!verifyResponse.ok) {
          throw new Error('Invalid token');
        }

        const verifyData = await verifyResponse.json();
        if (!verifyData.valid || !verifyData.user) {
          throw new Error('Token verification failed');
        }
        
        userData = verifyData.user;
      } else {
        // This is a Google OAuth credential
        const apiUrl = import.meta.env.VITE_API_URL || '/api';
        const response = await fetch(`${apiUrl}/auth/google`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ credential }),
        });

        if (!response.ok) {
          throw new Error('Google authentication failed');
        }

        const data = await response.json();
        token = data.token;
        userData = data.user;
      }

      // Store JWT token and user data in cookies (7 days expiry)
      const isHTTPS = window.location.protocol === 'https:';
      Cookies.set('fntx_token', token, { expires: 7, secure: isHTTPS, sameSite: 'lax' });
      Cookies.set('fntx_user', JSON.stringify(userData), { expires: 7, secure: isHTTPS, sameSite: 'lax' });
      
      setUser(userData);

    } catch (error) {
      console.error('Login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setUser(null);
    Cookies.remove('fntx_user');
    Cookies.remove('fntx_token');
    
    // Notify backend
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '/api';
      await fetch(`${apiUrl}/auth/logout`, { method: 'POST' });
    } catch (error) {
      console.warn('Backend logout notification failed:', error);
    }
    
    // Force redirect to landing page
    window.location.replace('/');
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    signOut: logout, // Alias for compatibility
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};