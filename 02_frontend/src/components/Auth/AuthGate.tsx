import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { LandingPage } from './LandingPage';
import { LoginModal } from './LoginModal';

interface AuthGateProps {
  children: React.ReactNode;
}

export const AuthGate: React.FC<AuthGateProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  // Show landing page when not authenticated
  if (!isAuthenticated) {
    return (
      <>
        <LandingPage
          onSignIn={() => setShowLoginModal(true)}
          onSignUp={() => setShowLoginModal(true)} // Same modal for both actions
        />
        <LoginModal 
          isOpen={showLoginModal} 
          onClose={() => setShowLoginModal(false)} 
        />
      </>
    );
  }

  // Show main app when authenticated
  return <>{children}</>;
};