
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ContractSelectionProps {
  data: any;
  onUpdate: (data: any) => void;
  onNext: () => void;
  onBack: () => void;
}

export const ContractSelection: React.FC<ContractSelectionProps> = ({
  data,
  onUpdate,
  onNext,
  onBack
}) => {
  const [instrument, setInstrument] = useState(data.instrument || 'SPY Puts');
  const [strikeSelection, setStrikeSelection] = useState(data.strikeSelection || 'delta-based');
  const [deltaTarget, setDeltaTarget] = useState(data.deltaTarget || '0.30');
  const [expirationType, setExpirationType] = useState(data.expirationType || 'dte');
  const [dteRange, setDteRange] = useState(data.dteRange || '1-3');

  const handleNext = () => {
    onUpdate({
      instrument,
      strikeSelection,
      deltaTarget,
      expirationType,
      dteRange
    });
    onNext();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-light text-zinc-700">
          TRADING AUTOMATION: CONTRACT
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <h4 className="text-sm font-medium text-zinc-900 mb-4">What contracts should be traded?</h4>
          <div className="mb-4">
            <label className="block text-sm font-medium text-zinc-700 mb-2">Instrument:</label>
            <input
              type="text"
              value={instrument}
              onChange={(e) => setInstrument(e.target.value)}
              className="w-full px-3 py-2 border border-zinc-300 rounded-lg"
            />
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-zinc-900 mb-4">Strike selection:</h4>
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <input
                type="radio"
                id="fixed-strike"
                name="strikeSelection"
                value="fixed-strike"
                checked={strikeSelection === 'fixed-strike'}
                onChange={(e) => setStrikeSelection(e.target.value)}
                className="w-4 h-4"
              />
              <label htmlFor="fixed-strike" className="text-sm text-zinc-700">Fixed strike</label>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="radio"
                id="delta-based"
                name="strikeSelection"
                value="delta-based"
                checked={strikeSelection === 'delta-based'}
                onChange={(e) => setStrikeSelection(e.target.value)}
                className="w-4 h-4"
              />
              <label htmlFor="delta-based" className="text-sm text-zinc-700">Delta-based</label>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="radio"
                id="otm-percentage"
                name="strikeSelection"
                value="otm-percentage"
                checked={strikeSelection === 'otm-percentage'}
                onChange={(e) => setStrikeSelection(e.target.value)}
                className="w-4 h-4"
              />
              <label htmlFor="otm-percentage" className="text-sm text-zinc-700">% Out-of-the-money</label>
            </div>
          </div>

          {strikeSelection === 'delta-based' && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-zinc-700 mb-2">Delta target:</label>
              <input
                type="text"
                value={deltaTarget}
                onChange={(e) => setDeltaTarget(e.target.value)}
                className="w-32 px-3 py-2 border border-zinc-300 rounded-lg"
              />
            </div>
          )}
        </div>

        <div>
          <h4 className="text-sm font-medium text-zinc-900 mb-4">Expiration:</h4>
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <input
                type="radio"
                id="fixed-date"
                name="expirationType"
                value="fixed-date"
                checked={expirationType === 'fixed-date'}
                onChange={(e) => setExpirationType(e.target.value)}
                className="w-4 h-4"
              />
              <label htmlFor="fixed-date" className="text-sm text-zinc-700">Fixed date</label>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="radio"
                id="dte"
                name="expirationType"
                value="dte"
                checked={expirationType === 'dte'}
                onChange={(e) => setExpirationType(e.target.value)}
                className="w-4 h-4"
              />
              <label htmlFor="dte" className="text-sm text-zinc-700">Days to expiration (DTE)</label>
            </div>
          </div>

          {expirationType === 'dte' && (
            <div className="mt-4">
              <label className="block text-sm font-medium text-zinc-700 mb-2">DTE range:</label>
              <input
                type="text"
                value={dteRange}
                onChange={(e) => setDteRange(e.target.value)}
                placeholder="e.g., 1-3"
                className="w-32 px-3 py-2 border border-zinc-300 rounded-lg"
              />
              <span className="ml-2 text-sm text-zinc-600">days</span>
            </div>
          )}
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
