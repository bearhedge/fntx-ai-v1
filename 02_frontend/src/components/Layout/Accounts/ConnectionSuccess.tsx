
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle } from 'lucide-react';

interface ConnectionSuccessProps {
  accountData: {
    accountNumber?: string;
    availableBalance?: number;
    optionsLevel?: number;
  };
  onStartTrading: () => void;
}

export const ConnectionSuccess: React.FC<ConnectionSuccessProps> = ({ 
  accountData, 
  onStartTrading 
}) => {
  return (
    <div className="space-y-8">
      <Card className="border border-zinc-200">
        <CardHeader className="text-center py-8">
          <CardTitle className="text-xl font-light text-zinc-900">
            CONNECT INTERACTIVE BROKERS
          </CardTitle>
        </CardHeader>
      </Card>

      <Card className="border border-zinc-200">
        <CardContent className="py-12 space-y-6">
          <div className="flex items-center justify-center space-x-3 mb-6">
            <CheckCircle className="w-6 h-6 text-green-600" />
            <p className="text-green-700 font-medium">
              Account Connected Successfully
            </p>
          </div>
          
          <div className="space-y-3 text-zinc-700 font-light">
            <div className="flex justify-between">
              <span>Account:</span>
              <span className="font-medium">{accountData.accountNumber}</span>
            </div>
            
            <div className="flex justify-between">
              <span>Available for Trading:</span>
              <span className="font-medium">
                ${accountData.availableBalance?.toLocaleString('en-US', { 
                  minimumFractionDigits: 2, 
                  maximumFractionDigits: 2 
                })}
              </span>
            </div>
            
            <div className="flex justify-between">
              <span>Options Approval Level:</span>
              <span className="font-medium">Level {accountData.optionsLevel}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border border-zinc-200">
        <CardContent className="py-6">
          <div className="flex justify-end">
            <Button 
              onClick={onStartTrading}
              className="bg-zinc-900 hover:bg-zinc-800 text-white font-light px-8"
            >
              Start Trading
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
