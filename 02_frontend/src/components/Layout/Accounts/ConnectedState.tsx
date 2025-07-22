
import React from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ConnectedStateProps {
  accountData: {
    accountNumber?: string;
    availableBalance?: number;
    optionsLevel?: number;
  };
  onDisconnect: () => void;
}

export const ConnectedState: React.FC<ConnectedStateProps> = ({ 
  accountData, 
  onDisconnect 
}) => {
  return (
    <Card className="border border-zinc-200">
      <CardContent className="py-8">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-light text-zinc-900">IBKR ACCOUNT</h3>
            <span className="text-sm text-green-600 font-medium">CONNECTED</span>
          </div>
          
          <div className="space-y-3 text-zinc-700 font-light">
            <div className="flex justify-between">
              <span>Account:</span>
              <span className="font-medium">{accountData.accountNumber}</span>
            </div>
            
            <div className="flex justify-between">
              <span>Available Balance:</span>
              <span className="font-medium">
                ${accountData.availableBalance?.toLocaleString('en-US', { 
                  minimumFractionDigits: 2, 
                  maximumFractionDigits: 2 
                })}
              </span>
            </div>
            
            <div className="flex justify-between">
              <span>Last Synced:</span>
              <span className="font-medium">Just now</span>
            </div>
          </div>

          <div className="flex justify-between pt-4">
            <Button 
              variant="outline"
              className="border-zinc-300 text-zinc-700 hover:bg-zinc-50 font-light"
            >
              View Details
            </Button>
            <Button 
              variant="outline"
              onClick={onDisconnect}
              className="border-zinc-300 text-zinc-700 hover:bg-zinc-50 font-light"
            >
              Disconnect
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
