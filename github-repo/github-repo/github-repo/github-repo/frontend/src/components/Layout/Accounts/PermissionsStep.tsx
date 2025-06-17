
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

interface PermissionsStepProps {
  onContinue: (permissions: any) => void;
  onBack: () => void;
}

export const PermissionsStep: React.FC<PermissionsStepProps> = ({ onContinue, onBack }) => {
  const [permissions, setPermissions] = useState({
    readAccount: true,
    submitOrders: true,
    automatedTrading: false
  });

  const handlePermissionChange = (key: keyof typeof permissions, value: boolean) => {
    setPermissions(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = () => {
    onContinue(permissions);
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
        <CardContent className="py-12 space-y-6">
          <p className="text-zinc-700 font-light mb-6">
            Set Trading Permissions
          </p>
          
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <Checkbox
                id="readAccount"
                checked={permissions.readAccount}
                onCheckedChange={(checked) => handlePermissionChange('readAccount', checked as boolean)}
              />
              <Label htmlFor="readAccount" className="text-zinc-700 font-light">
                Allow reading account information
              </Label>
            </div>

            <div className="flex items-center space-x-3">
              <Checkbox
                id="submitOrders"
                checked={permissions.submitOrders}
                onCheckedChange={(checked) => handlePermissionChange('submitOrders', checked as boolean)}
              />
              <Label htmlFor="submitOrders" className="text-zinc-700 font-light">
                Allow submitting orders
              </Label>
            </div>

            <div className="flex items-center space-x-3">
              <Checkbox
                id="automatedTrading"
                checked={permissions.automatedTrading}
                onCheckedChange={(checked) => handlePermissionChange('automatedTrading', checked as boolean)}
              />
              <Label htmlFor="automatedTrading" className="text-zinc-700 font-light">
                Allow automated trading
              </Label>
            </div>
          </div>

          <div className="pt-4">
            <p className="text-zinc-700 font-light">
              <span className="font-medium">Trading Strategy:</span> SPY Daily Options
            </p>
          </div>
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
              Back
            </Button>
            <Button 
              onClick={handleSubmit}
              className="bg-zinc-900 hover:bg-zinc-800 text-white font-light"
            >
              Connect Account
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
