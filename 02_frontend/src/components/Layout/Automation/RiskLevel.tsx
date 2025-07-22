
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface RiskLevelProps {
  data: any;
  onUpdate: (data: any) => void;
  onNext: () => void;
  onBack: () => void;
}

export const RiskLevel: React.FC<RiskLevelProps> = ({
  data,
  onUpdate,
  onNext,
  onBack
}) => {
  const [positionSizing, setPositionSizing] = useState(data.positionSizing || 'percentage-capital');
  const [capitalAllocation, setCapitalAllocation] = useState(data.capitalAllocation || '5');
  const [maxDailyExposure, setMaxDailyExposure] = useState(data.maxDailyExposure || '15');

  const handleNext = () => {
    onUpdate({
      positionSizing,
      capitalAllocation,
      maxDailyExposure
    });
    onNext();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-light text-zinc-700">
          TRADING AUTOMATION: RISK LEVEL
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <h4 className="text-sm font-medium text-zinc-900 mb-4">How much capital should be allocated?</h4>
          
          <div className="space-y-4">
            <div>
              <h5 className="text-sm font-medium text-zinc-900 mb-3">Position sizing:</h5>
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="fixed-quantity"
                    name="positionSizing"
                    value="fixed-quantity"
                    checked={positionSizing === 'fixed-quantity'}
                    onChange={(e) => setPositionSizing(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="fixed-quantity" className="text-sm text-zinc-700">Fixed contract quantity</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="percentage-capital"
                    name="positionSizing"
                    value="percentage-capital"
                    checked={positionSizing === 'percentage-capital'}
                    onChange={(e) => setPositionSizing(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="percentage-capital" className="text-sm text-zinc-700">Percentage of available capital</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="fixed-dollar"
                    name="positionSizing"
                    value="fixed-dollar"
                    checked={positionSizing === 'fixed-dollar'}
                    onChange={(e) => setPositionSizing(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="fixed-dollar" className="text-sm text-zinc-700">Fixed dollar amount</label>
                </div>
              </div>
            </div>

            {positionSizing === 'percentage-capital' && (
              <div>
                <label className="block text-sm font-medium text-zinc-700 mb-2">Capital allocation:</label>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    value={capitalAllocation}
                    onChange={(e) => setCapitalAllocation(e.target.value)}
                    className="w-20 px-3 py-2 border border-zinc-300 rounded-lg"
                    min="1"
                    max="100"
                  />
                  <span className="text-sm text-zinc-600">% of available capital per trade</span>
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-2">Maximum daily exposure:</label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  value={maxDailyExposure}
                  onChange={(e) => setMaxDailyExposure(e.target.value)}
                  className="w-20 px-3 py-2 border border-zinc-300 rounded-lg"
                  min="1"
                  max="100"
                />
                <span className="text-sm text-zinc-600">% of account</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-between pt-6">
          <Button variant="outline" onClick={onBack} className="text-zinc-700 border-zinc-300">
            Back
          </Button>
          <Button onClick={handleNext} className="bg-zinc-900 text-white hover:bg-zinc-800">
            Next Step
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
