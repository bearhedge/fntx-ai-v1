
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface AutomationSummaryProps {
  data: any;
  onBack: () => void;
  onEdit: (step: number) => void;
}

export const AutomationSummary: React.FC<AutomationSummaryProps> = ({
  data,
  onBack,
  onEdit
}) => {
  const getTimingDisplay = () => {
    if (data.timing?.executionType === 'weekly') {
      const days = data.timing.executionDays?.map((day: string) => 
        day.charAt(0).toUpperCase() + day.slice(1, 3)
      ).join('-') || 'Mon-Fri';
      return `Weekly: ${days}`;
    }
    return 'Daily execution';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-light text-zinc-700">
          AUTOMATION SUMMARY
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <p className="text-sm text-zinc-600 mb-6">
            Your automation has been configured with the following parameters:
          </p>

          <div className="grid grid-cols-2 gap-6 mb-6">
            <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">TIMING</h4>
              <div className="space-y-1 text-xs text-zinc-700">
                <div>{getTimingDisplay()}</div>
                <div>Time: {data.timing?.executionTime || '09:45'} AM EST</div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onEdit(0)}
                className="w-full mt-3 text-xs"
              >
                Edit
              </Button>
            </div>

            <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">CONTRACT</h4>
              <div className="space-y-1 text-xs text-zinc-700">
                <div>Instrument: {data.contract?.instrument || 'SPY Puts'}</div>
                <div>Strike: {data.contract?.deltaTarget || '0.30'} delta</div>
                <div>Expiration: {data.contract?.dteRange || '1-3'} DTE</div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onEdit(1)}
                className="w-full mt-3 text-xs"
              >
                Edit
              </Button>
            </div>

            <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">RISK LEVEL</h4>
              <div className="space-y-1 text-xs text-zinc-700">
                <div>Allocation: {data.riskLevel?.capitalAllocation || '5'}% per trade</div>
                <div>Max exposure: {data.riskLevel?.maxDailyExposure || '15'}%</div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onEdit(2)}
                className="w-full mt-3 text-xs"
              >
                Edit
              </Button>
            </div>

            <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">RISK MANAGEMENT</h4>
              <div className="space-y-1 text-xs text-zinc-700">
                <div>Stop-loss: {data.riskManagement?.stopLossLevel || '3'}x premium</div>
                <div>Take-profit: {data.riskManagement?.takeProfitLevel || '80'}% premium</div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onEdit(3)}
                className="w-full mt-3 text-xs"
              >
                Edit
              </Button>
            </div>
          </div>

          <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4 mb-6">
            <h4 className="text-sm font-medium text-zinc-900 mb-3 text-center">CONTINGENCY ACTIONS</h4>
            <div className="space-y-1 text-xs text-zinc-700">
              <div>Close if ITM</div>
              <div>Pause after 3 losses</div>
              <div>Pause on disruption</div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onEdit(4)}
              className="w-full mt-3 text-xs"
            >
              Edit
            </Button>
          </div>

          <div className="text-center mb-6">
            <div className="inline-flex items-center px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
              Automation status: ACTIVE
            </div>
          </div>
        </div>

        <div className="flex justify-between pt-6">
          <Button variant="outline" onClick={onBack} className="text-zinc-700 border-zinc-300">
            Back
          </Button>
          <Button className="bg-red-600 text-white hover:bg-red-700">
            Disable Automation
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
