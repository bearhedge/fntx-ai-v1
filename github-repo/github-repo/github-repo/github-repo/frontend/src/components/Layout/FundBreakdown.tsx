
import React from 'react';
import { Progress } from "@/components/ui/progress";
import { AvailabilityBreakdown } from '@/types/trading';

interface FundBreakdownProps {
  breakdown: AvailabilityBreakdown;
}

export const FundBreakdown: React.FC<FundBreakdownProps> = ({ breakdown }) => {
  const availablePercentage = (breakdown.available / breakdown.total) * 100;
  const lockedPercentage = (breakdown.locked / breakdown.total) * 100;
  const pendingPercentage = breakdown.pendingRelease.reduce((sum, pending) => sum + pending.amount, 0) / breakdown.total * 100;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h4 className="font-medium text-gray-900 mb-6">Fund Availability Breakdown</h4>
      <div className="space-y-6">
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-gray-700">Total Portfolio Value</span>
            <span className="font-mono text-gray-900">${breakdown.total.toLocaleString()}</span>
          </div>
          <Progress value={100} className="h-2 bg-gray-100">
            <div className="h-full bg-gray-400 rounded-full" style={{ width: '100%' }} />
          </Progress>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-gray-700">Available for Withdrawal</span>
            <span className="font-mono text-gray-900">${breakdown.available.toLocaleString()}</span>
          </div>
          <Progress value={availablePercentage} className="h-2 bg-gray-100">
            <div className="h-full bg-gray-600 rounded-full" style={{ width: `${availablePercentage}%` }} />
          </Progress>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-gray-700">Locked in Positions</span>
            <span className="font-mono text-gray-900">(${breakdown.locked.toLocaleString()})</span>
          </div>
          <Progress value={lockedPercentage} className="h-2 bg-gray-100">
            <div className="h-full bg-gray-800 rounded-full" style={{ width: `${lockedPercentage}%` }} />
          </Progress>
        </div>

        {breakdown.pendingRelease.map((pending, index) => (
          <div key={index} className="space-y-2 pl-4 border-l-2 border-gray-200">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 text-sm">
                Pending Release ({pending.reason})
              </span>
              <span className="font-mono text-gray-900 text-sm">
                ${pending.amount.toLocaleString()} on {pending.releaseDate}
              </span>
            </div>
            <Progress value={pendingPercentage} className="h-1.5 bg-gray-100">
              <div className="h-full bg-gray-500 rounded-full" style={{ width: `${pendingPercentage}%` }} />
            </Progress>
          </div>
        ))}
      </div>
    </div>
  );
};
