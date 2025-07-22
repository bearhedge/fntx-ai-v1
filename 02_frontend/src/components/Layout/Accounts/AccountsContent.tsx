
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConnectionPrompt } from './ConnectionPrompt';
import { AuthenticationStep } from './AuthenticationStep';
import { PermissionsStep } from './PermissionsStep';
import { ConnectionSuccess } from './ConnectionSuccess';
import { ConnectedState } from './ConnectedState';

type ConnectionState = 'prompt' | 'auth' | 'permissions' | 'success' | 'connected';

export const AccountsContent: React.FC = () => {
  const [connectionState, setConnectionState] = useState<ConnectionState>('prompt');
  const [accountData, setAccountData] = useState<{
    accountNumber?: string;
    availableBalance?: number;
    optionsLevel?: number;
  }>({});

  const handleConnect = () => {
    setConnectionState('auth');
  };

  const handleAuth = (username: string, password: string) => {
    // Simulate authentication
    setConnectionState('permissions');
  };

  const handlePermissions = (permissions: any) => {
    // Simulate account connection
    setAccountData({
      accountNumber: 'U1234567',
      availableBalance: 25000.00,
      optionsLevel: 3
    });
    setConnectionState('success');
  };

  const handleStartTrading = () => {
    setConnectionState('connected');
  };

  const handleDisconnect = () => {
    setConnectionState('prompt');
    setAccountData({});
  };

  const handleBack = () => {
    switch (connectionState) {
      case 'auth':
        setConnectionState('prompt');
        break;
      case 'permissions':
        setConnectionState('auth');
        break;
      case 'success':
        setConnectionState('permissions');
        break;
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-2xl mx-auto pt-16 px-6">
        {connectionState === 'prompt' && (
          <ConnectionPrompt onConnect={handleConnect} />
        )}
        
        {connectionState === 'auth' && (
          <AuthenticationStep 
            onAuth={handleAuth} 
            onBack={handleBack}
          />
        )}
        
        {connectionState === 'permissions' && (
          <PermissionsStep 
            onContinue={handlePermissions} 
            onBack={handleBack}
          />
        )}
        
        {connectionState === 'success' && (
          <ConnectionSuccess 
            accountData={accountData}
            onStartTrading={handleStartTrading} 
          />
        )}
        
        {connectionState === 'connected' && (
          <ConnectedState 
            accountData={accountData}
            onDisconnect={handleDisconnect}
          />
        )}
      </div>
    </div>
  );
};
