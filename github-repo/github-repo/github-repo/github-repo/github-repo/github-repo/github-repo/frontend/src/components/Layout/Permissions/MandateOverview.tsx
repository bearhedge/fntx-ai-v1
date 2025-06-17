
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Shield } from 'lucide-react';

export const MandateOverview: React.FC = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-center text-lg font-light text-zinc-700">
          Your account is configured with the following mandate:
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-6 text-center">
          <div className="flex items-center justify-center mb-4">
            <Shield className="w-8 h-8 text-zinc-600" />
          </div>
          <h3 className="text-xl text-zinc-900 mb-2 font-light">DAILY SPY OPTION SELLING</h3>
          <p className="text-zinc-600 text-sm font-light">Strategy locked and enforced through a smart contract</p>
        </div>
        
        <div className="flex justify-center space-x-4">
          
          
          
        </div>
      </CardContent>
    </Card>
  );
};
