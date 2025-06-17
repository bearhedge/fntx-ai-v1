import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
export const MandateDetails: React.FC = () => {
  return <Card>
      <CardHeader>
        <CardTitle className="text-lg font-light text-zinc-700">DETAILS</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">
              STRATEGY PARAMETERS
            </h4>
            
            <div className="space-y-2 text-xs text-zinc-700">
              <div><span className="font-medium">Instrument:</span> SPY Puts</div>
              <div><span className="font-medium">Strike:</span> 5% OTM</div>
              <div><span className="font-medium">Expiration:</span> 1-3 DTE</div>
              <div><span className="font-medium">Position size:</span> 5% of available capital per trade</div>
            </div>
          </div>
          
          <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">
              EXECUTION RULES
            </h4>
            
            <div className="space-y-2 text-xs text-zinc-700">
              <div><span className="font-medium">Execution time:</span> 9:45-10:15 AM EST</div>
              <div><span className="font-medium">Days:</span> Mon-Fri (except holidays)</div>
              <div><span className="font-medium">Auto-execution:</span> ON</div>
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">
              RISK CONTROLS
            </h4>
            
            <div className="space-y-2 text-xs text-zinc-700">
              <div><span className="font-medium">Max daily exposure:</span> 15% of account</div>
              <div><span className="font-medium">Stop-loss:</span> 3x premium</div>
              <div><span className="font-medium">Take-profit:</span> 80% of premium</div>
            </div>
          </div>
          
          <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">
              MANDATE DURATION
            </h4>
            
            <div className="space-y-2 text-xs text-zinc-700">
              <div><span className="font-medium">Start date:</span> June 1, 2025</div>
              <div><span className="font-medium">End date:</span> December 31, 2025</div>
              <div><span className="font-medium">Renewal:</span> Manual</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>;
};