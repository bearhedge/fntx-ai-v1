
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ConnectionPromptProps {
  onConnect: () => void;
}

export const ConnectionPrompt: React.FC<ConnectionPromptProps> = ({ onConnect }) => {
  return (
    <div className="space-y-8">
      <Card className="border border-zinc-200">
        <CardHeader className="text-center py-8">
          <CardTitle className="text-xl font-light text-zinc-900">
            CONNECT YOUR TRADING ACCOUNT
          </CardTitle>
        </CardHeader>
      </Card>

      <Card className="border border-zinc-200">
        <CardContent className="py-12 text-center space-y-8">
          <p className="text-zinc-700 font-light">
            To start trading with FNTX AI, connect your Interactive Brokers account.
          </p>
          
          <Button 
            onClick={onConnect}
            className="bg-zinc-900 hover:bg-zinc-800 text-white px-8 py-3 font-light"
          >
            Connect Interactive Brokers
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};
