
import React, { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';

interface WaitingPeriodTimerProps {
  totalMinutes: number;
  remainingMinutes: number;
  reason: string;
}

export const WaitingPeriodTimer = ({ totalMinutes, remainingMinutes: initialRemaining, reason }: WaitingPeriodTimerProps) => {
  const [remainingMinutes, setRemainingMinutes] = useState(initialRemaining);

  useEffect(() => {
    if (remainingMinutes > 0) {
      const timer = setInterval(() => {
        setRemainingMinutes(prev => Math.max(0, prev - 1));
      }, 60000); // Update every minute

      return () => clearInterval(timer);
    }
  }, [remainingMinutes]);

  const progress = ((totalMinutes - remainingMinutes) / totalMinutes) * 100;
  const hours = Math.floor(remainingMinutes / 60);
  const minutes = remainingMinutes % 60;

  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
      <div className="flex items-center space-x-2 mb-3">
        <Clock className="w-4 h-4 text-blue-600" />
        <h4 className="font-semibold text-gray-800">Waiting Period</h4>
      </div>
      
      <div className="mb-3">
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      
      <div className="text-center mb-3">
        <div className="text-2xl font-bold text-gray-800">
          {hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`}
        </div>
        <div className="text-sm text-gray-600">remaining</div>
      </div>
      
      <div className="text-xs text-gray-600 bg-white rounded p-2 border">
        <strong>Reason:</strong> {reason}
      </div>
    </div>
  );
};
