
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface RiskManagementProps {
  data: any;
  onUpdate: (data: any) => void;
  onNext: () => void;
  onBack: () => void;
}

export const RiskManagement: React.FC<RiskManagementProps> = ({
  data,
  onUpdate,
  onNext,
  onBack
}) => {
  const [stopLossStrategy, setStopLossStrategy] = useState(data.stopLossStrategy || 'multiple-premium');
  const [stopLossLevel, setStopLossLevel] = useState(data.stopLossLevel || '3');
  const [takeProfitStrategy, setTakeProfitStrategy] = useState(data.takeProfitStrategy || 'percentage-premium');
  const [takeProfitLevel, setTakeProfitLevel] = useState(data.takeProfitLevel || '80');

  const handleNext = () => {
    onUpdate({
      stopLossStrategy,
      stopLossLevel,
      takeProfitStrategy,
      takeProfitLevel
    });
    onNext();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-light text-zinc-700">
          TRADING AUTOMATION: RISK MANAGEMENT
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <h4 className="text-sm font-medium text-zinc-900 mb-4">Set stop-loss and take-profit levels:</h4>
          
          <div className="space-y-6">
            <div>
              <h5 className="text-sm font-medium text-zinc-900 mb-3">Stop-loss strategy:</h5>
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="fixed-price"
                    name="stopLossStrategy"
                    value="fixed-price"
                    checked={stopLossStrategy === 'fixed-price'}
                    onChange={(e) => setStopLossStrategy(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="fixed-price" className="text-sm text-zinc-700">Fixed price</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="multiple-premium"
                    name="stopLossStrategy"
                    value="multiple-premium"
                    checked={stopLossStrategy === 'multiple-premium'}
                    onChange={(e) => setStopLossStrategy(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="multiple-premium" className="text-sm text-zinc-700">Multiple of premium</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="percentage-loss"
                    name="stopLossStrategy"
                    value="percentage-loss"
                    checked={stopLossStrategy === 'percentage-loss'}
                    onChange={(e) => setStopLossStrategy(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="percentage-loss" className="text-sm text-zinc-700">Percentage loss</label>
                </div>
              </div>

              {stopLossStrategy === 'multiple-premium' && (
                <div className="mt-4">
                  <label className="block text-sm font-medium text-zinc-700 mb-2">Stop-loss level:</label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      value={stopLossLevel}
                      onChange={(e) => setStopLossLevel(e.target.value)}
                      className="w-20 px-3 py-2 border border-zinc-300 rounded-lg"
                      min="1"
                      step="0.1"
                    />
                    <span className="text-sm text-zinc-600">x premium collected</span>
                  </div>
                </div>
              )}
            </div>

            <div>
              <h5 className="text-sm font-medium text-zinc-900 mb-3">Take-profit strategy:</h5>
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="fixed-price-profit"
                    name="takeProfitStrategy"
                    value="fixed-price"
                    checked={takeProfitStrategy === 'fixed-price'}
                    onChange={(e) => setTakeProfitStrategy(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="fixed-price-profit" className="text-sm text-zinc-700">Fixed price</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="percentage-premium"
                    name="takeProfitStrategy"
                    value="percentage-premium"
                    checked={takeProfitStrategy === 'percentage-premium'}
                    onChange={(e) => setTakeProfitStrategy(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="percentage-premium" className="text-sm text-zinc-700">Percentage of premium</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="time-based"
                    name="takeProfitStrategy"
                    value="time-based"
                    checked={takeProfitStrategy === 'time-based'}
                    onChange={(e) => setTakeProfitStrategy(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="time-based" className="text-sm text-zinc-700">Time-based</label>
                </div>
              </div>

              {takeProfitStrategy === 'percentage-premium' && (
                <div className="mt-4">
                  <label className="block text-sm font-medium text-zinc-700 mb-2">Take-profit level:</label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      value={takeProfitLevel}
                      onChange={(e) => setTakeProfitLevel(e.target.value)}
                      className="w-20 px-3 py-2 border border-zinc-300 rounded-lg"
                      min="1"
                      max="100"
                    />
                    <span className="text-sm text-zinc-600">% of premium collected</span>
                  </div>
                </div>
              )}
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
