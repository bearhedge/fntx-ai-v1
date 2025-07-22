
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface AuthenticationStepProps {
  onAuth: (username: string, password: string) => void;
  onBack: () => void;
}

export const AuthenticationStep: React.FC<AuthenticationStepProps> = ({ onAuth, onBack }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (username && password) {
      onAuth(username, password);
    }
  };

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
        <CardContent className="py-12">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-4">
              <p className="text-zinc-700 font-light mb-6">
                Enter your IBKR credentials
              </p>
              
              <div className="space-y-2">
                <Label htmlFor="username" className="text-zinc-700 font-light">
                  Username
                </Label>
                <Input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="border-zinc-300 focus:border-zinc-500"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-zinc-700 font-light">
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="border-zinc-300 focus:border-zinc-500"
                  required
                />
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="border border-zinc-200">
        <CardContent className="py-6">
          <div className="flex justify-between">
            <Button 
              variant="outline" 
              onClick={onBack}
              className="border-zinc-300 text-zinc-700 hover:bg-zinc-50 font-light"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSubmit}
              className="bg-zinc-900 hover:bg-zinc-800 text-white font-light"
              disabled={!username || !password}
            >
              Continue
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
