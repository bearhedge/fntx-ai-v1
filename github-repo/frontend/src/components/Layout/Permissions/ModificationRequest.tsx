import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { AlertTriangle } from 'lucide-react';

export const ModificationRequest: React.FC = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-light text-zinc-700">MODIFICATION</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5" />
            <div className="text-sm text-amber-800">
              <strong>WARNING:</strong> modifying an active mandate requires multi-signature approval and will be recorded on-chain. 
              Modifications are subject to a 72-hour cooling period before implementation.
            </div>
          </div>
        </div>
        
        <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-6">
          <h4 className="text-sm font-medium text-zinc-900 mb-4">Requested modification:</h4>
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Checkbox id="strategy-params" />
              <label htmlFor="strategy-params" className="text-sm text-zinc-700">Strategy parameters</label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox id="execution-rules" />
              <label htmlFor="execution-rules" className="text-sm text-zinc-700">Execution rules</label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox id="risk-controls" />
              <label htmlFor="risk-controls" className="text-sm text-zinc-700">Risk controls</label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox id="mandate-duration" />
              <label htmlFor="mandate-duration" className="text-sm text-zinc-700">Mandate duration</label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox id="terminate-mandate" />
              <label htmlFor="terminate-mandate" className="text-sm text-zinc-700">Terminate mandate</label>
            </div>
          </div>
          
          <div className="mt-6">
            <label htmlFor="justification" className="block text-sm font-medium text-zinc-900 mb-2">
              Justification for modification:
            </label>
            <Textarea id="justification" placeholder="Please provide detailed justification for the requested modification..." className="min-h-[100px]" />
          </div>
        </div>
        
        <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
          <div className="flex justify-between items-center text-sm text-zinc-700">
            <div>
              <div><span className="font-medium">Required approvals:</span> 2/3</div>
              <div><span className="font-medium">Current approvals:</span> 0/3</div>
            </div>
          </div>
        </div>
        
        <div className="flex justify-between">
          <Button variant="outline" className="text-zinc-700 border-zinc-300">
            Cancel
          </Button>
          <Button className="bg-zinc-900 text-white hover:bg-zinc-800">
            Submit Modification Request
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
