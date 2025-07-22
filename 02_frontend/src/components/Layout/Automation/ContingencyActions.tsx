
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ContingencyActionsProps {
  data: any;
  onUpdate: (data: any) => void;
  onNext: () => void;
  onBack: () => void;
}

export const ContingencyActions: React.FC<ContingencyActionsProps> = ({
  data,
  onUpdate,
  onNext,
  onBack
}) => {
  const [assignmentRisk, setAssignmentRisk] = useState(data.assignmentRisk || 'close-itm');
  const [marketDisruption, setMarketDisruption] = useState(data.marketDisruption || 'pause-notify');
  const [performanceThreshold, setPerformanceThreshold] = useState(data.performanceThreshold || 'pause-losses');

  const handleNext = () => {
    onUpdate({
      assignmentRisk,
      marketDisruption,
      performanceThreshold
    });
    onNext();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-light text-zinc-700">
          TRADING AUTOMATION: CONTINGENCY ACTIONS
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <h4 className="text-sm font-medium text-zinc-900 mb-4">What should happen in special scenarios?</h4>
          
          <div className="space-y-6">
            <div>
              <h5 className="text-sm font-medium text-zinc-900 mb-3">Assignment risk:</h5>
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="close-itm"
                    name="assignmentRisk"
                    value="close-itm"
                    checked={assignmentRisk === 'close-itm'}
                    onChange={(e) => setAssignmentRisk(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="close-itm" className="text-sm text-zinc-700">Close position before expiration if ITM</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="allow-assignment"
                    name="assignmentRisk"
                    value="allow-assignment"
                    checked={assignmentRisk === 'allow-assignment'}
                    onChange={(e) => setAssignmentRisk(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="allow-assignment" className="text-sm text-zinc-700">Allow assignment and manage resulting position</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="roll-expiration"
                    name="assignmentRisk"
                    value="roll-expiration"
                    checked={assignmentRisk === 'roll-expiration'}
                    onChange={(e) => setAssignmentRisk(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="roll-expiration" className="text-sm text-zinc-700">Roll to next expiration if approaching ITM</label>
                </div>
              </div>
            </div>

            <div>
              <h5 className="text-sm font-medium text-zinc-900 mb-3">Market disruption:</h5>
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="pause-notify"
                    name="marketDisruption"
                    value="pause-notify"
                    checked={marketDisruption === 'pause-notify'}
                    onChange={(e) => setMarketDisruption(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="pause-notify" className="text-sm text-zinc-700">Pause automation and notify</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="close-immediately"
                    name="marketDisruption"
                    value="close-immediately"
                    checked={marketDisruption === 'close-immediately'}
                    onChange={(e) => setMarketDisruption(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="close-immediately" className="text-sm text-zinc-700">Close all positions immediately</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="continue-adjusted"
                    name="marketDisruption"
                    value="continue-adjusted"
                    checked={marketDisruption === 'continue-adjusted'}
                    onChange={(e) => setMarketDisruption(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="continue-adjusted" className="text-sm text-zinc-700">Continue with adjusted parameters</label>
                </div>
              </div>
            </div>

            <div>
              <h5 className="text-sm font-medium text-zinc-900 mb-3">Performance threshold:</h5>
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="pause-losses"
                    name="performanceThreshold"
                    value="pause-losses"
                    checked={performanceThreshold === 'pause-losses'}
                    onChange={(e) => setPerformanceThreshold(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="pause-losses" className="text-sm text-zinc-700">Pause after 3 consecutive losses</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="reduce-size"
                    name="performanceThreshold"
                    value="reduce-size"
                    checked={performanceThreshold === 'reduce-size'}
                    onChange={(e) => setPerformanceThreshold(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="reduce-size" className="text-sm text-zinc-700">Reduce position size after losses</label>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="no-adjustment"
                    name="performanceThreshold"
                    value="no-adjustment"
                    checked={performanceThreshold === 'no-adjustment'}
                    onChange={(e) => setPerformanceThreshold(e.target.value)}
                    className="w-4 h-4"
                  />
                  <label htmlFor="no-adjustment" className="text-sm text-zinc-700">No automatic adjustment</label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-between pt-6">
          <Button variant="outline" onClick={onBack} className="text-zinc-700 border-zinc-300">
            Back
          </Button>
          <Button onClick={handleNext} className="bg-zinc-900 text-white hover:bg-zinc-800">
            Save All
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
