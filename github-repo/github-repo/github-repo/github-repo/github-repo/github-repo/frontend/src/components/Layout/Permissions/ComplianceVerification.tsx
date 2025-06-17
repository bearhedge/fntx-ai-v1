import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
export const ComplianceVerification: React.FC = () => {
  return <Card>
      <CardHeader>
        <CardTitle className="text-lg font-light text-zinc-700">COMPLIANCE</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">
              EXECUTION RECORD
            </h4>
            <div className="space-y-2 text-xs text-zinc-700">
              <div><span className="font-medium">Last execution:</span> June 8, 2025 9:52 AM EST</div>
              <div><span className="font-medium">Next scheduled:</span> June 9, 2025 9:45 AM EST</div>
              <div className="pt-2">
                <Button variant="outline" size="sm" className="w-full text-xs">
                  View Trade Log
                </Button>
              </div>
            </div>
          </div>
          
          <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">
              COMPLIANCE STATUS
            </h4>
            <div className="space-y-2 text-xs text-zinc-700">
              <div><span className="font-medium">Overall compliance:</span> <Badge className="bg-green-100 text-green-800">100%</Badge></div>
              <div><span className="font-medium">Mandate violations:</span> 0</div>
              <div><span className="font-medium">Smart contract:</span> <Badge className="bg-green-100 text-green-800">ACTIVE</Badge></div>
              <div className="pt-2">
                <Button variant="outline" size="sm" className="w-full text-xs">
                  Verify On-Chain
                </Button>
              </div>
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">
              OVERRIDE REQUESTS
            </h4>
            <div className="space-y-2 text-xs text-zinc-700">
              <div><span className="font-medium">Pending:</span> 0</div>
              <div><span className="font-medium">Approved:</span> 0</div>
              <div><span className="font-medium">Rejected:</span> 0</div>
              <div className="text-xs text-zinc-600 mt-2">
                Emergency override requires 2/3 approval from authorized signatories
              </div>
              <div className="pt-2">
                <Button variant="outline" size="sm" className="w-full text-xs">
                  Request Override
                </Button>
              </div>
            </div>
          </div>
          
          <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">
              MANDATE HEALTH
            </h4>
            <div className="space-y-2 text-xs text-zinc-700">
              <div><span className="font-medium">Strategy performance:</span> <span className="text-green-600">+12.4% annualized</span></div>
              <div><span className="font-medium">Risk assessment:</span> <Badge className="bg-green-100 text-green-800">WITHIN PARAMETERS</Badge></div>
              <div><span className="font-medium">Capital utilization:</span> 68% of optimal</div>
              <div className="pt-2">
                <Button variant="outline" size="sm" className="w-full text-xs">
                  View Analytics
                </Button>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>;
};