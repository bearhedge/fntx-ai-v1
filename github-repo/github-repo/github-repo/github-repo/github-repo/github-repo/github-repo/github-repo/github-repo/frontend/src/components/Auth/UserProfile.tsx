import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { LoginModal } from './LoginModal';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { LogIn, LogOut } from 'lucide-react';

interface UserProfileProps {
  className?: string;
}

export const UserProfile: React.FC<UserProfileProps> = ({ className = '' }) => {
  const { user, isAuthenticated, logout, isLoading } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center p-4 ${className}`}>
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <>
        <div className={`${className}`}>
          <Button
            onClick={() => setShowLoginModal(true)}
            variant="outline"
            className="w-full flex items-center space-x-2 bg-white hover:bg-gray-50 border-gray-300"
          >
            <LogIn className="w-4 h-4" />
            <span className="text-sm">Sign in with Google</span>
          </Button>
        </div>
        
        <LoginModal 
          isOpen={showLoginModal} 
          onClose={() => setShowLoginModal(false)} 
        />
      </>
    );
  }

  return (
    <div className={`flex items-center justify-between space-x-3 ${className}`}>
      <div className="flex items-center space-x-3 flex-1 min-w-0">
        <Avatar className="w-8 h-8">
          <AvatarImage src={user?.picture} alt={user?.name} />
          <AvatarFallback className="bg-gray-200">
            {user?.name?.charAt(0) || 'U'}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {user?.name}
          </p>
          <p className="text-xs text-gray-600 truncate">
            {user?.email}
          </p>
        </div>
      </div>
      <Button
        onClick={logout}
        variant="ghost"
        size="sm"
        className="text-gray-500 hover:text-red-600 p-2"
        title="Sign out"
      >
        <LogOut className="w-4 h-4" />
      </Button>
    </div>
  );
};