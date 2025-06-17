
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

interface TimingConfigurationProps {
  data: any;
  onUpdate: (data: any) => void;
  onNext: () => void;
}

export const TimingConfiguration: React.FC<TimingConfigurationProps> = ({
  data,
  onUpdate,
  onNext
}) => {
  const [executionType, setExecutionType] = useState(data.executionType || 'weekly');
  const [executionDays, setExecutionDays] = useState(data.executionDays || ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']);
  const [executionTime, setExecutionTime] = useState(data.executionTime || '09:45');

  const handleNext = () => {
    onUpdate({
      executionType,
      executionDays,
      executionTime
    });
    onNext();
  };

  const toggleDay = (day: string) => {
    if (executionDays.includes(day)) {
      setExecutionDays(executionDays.filter(d => d !== day));
    } else {
      setExecutionDays([...executionDays, day]);
    }
  };

  const days = [
    { key: 'monday', label: 'Monday' },
    { key: 'tuesday', label: 'Tuesday' },
    { key: 'wednesday', label: 'Wednesday' },
    { key: 'thursday', label: 'Thursday' },
    { key: 'friday', label: 'Friday' },
    { key: 'saturday', label: 'Saturday' },
    { key: 'sunday', label: 'Sunday' }
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-light text-zinc-700">
          TRADING AUTOMATION: TIMING
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <h4 className="text-sm font-medium text-zinc-900 mb-4">When should this automation execute?</h4>
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <input
                type="radio"
                id="daily"
                name="executionType"
                value="daily"
                checked={executionType === 'daily'}
                onChange={(e) => setExecutionType(e.target.value)}
                className="w-4 h-4"
              />
              <label htmlFor="daily" className="text-sm text-zinc-700">Daily at specific time</label>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="radio"
                id="weekly"
                name="executionType"
                value="weekly"
                checked={executionType === 'weekly'}
                onChange={(e) => setExecutionType(e.target.value)}
                className="w-4 h-4"
              />
              <label htmlFor="weekly" className="text-sm text-zinc-700">Weekly on selected days</label>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="radio"
                id="market-events"
                name="executionType"
                value="market-events"
                checked={executionType === 'market-events'}
                onChange={(e) => setExecutionType(e.target.value)}
                className="w-4 h-4"
              />
              <label htmlFor="market-events" className="text-sm text-zinc-700">On market events</label>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="radio"
                id="technical"
                name="executionType"
                value="technical"
                checked={executionType === 'technical'}
                onChange={(e) => setExecutionType(e.target.value)}
                className="w-4 h-4"
              />
              <label htmlFor="technical" className="text-sm text-zinc-700">On technical indicators</label>
            </div>
          </div>
        </div>

        {executionType === 'weekly' && (
          <div>
            <h4 className="text-sm font-medium text-zinc-900 mb-4">Execution days:</h4>
            <div className="grid grid-cols-4 gap-3">
              {days.map((day) => (
                <div key={day.key} className="flex items-center space-x-2">
                  <Checkbox
                    id={day.key}
                    checked={executionDays.includes(day.key)}
                    onCheckedChange={() => toggleDay(day.key)}
                  />
                  <label htmlFor={day.key} className="text-sm text-zinc-700">{day.label}</label>
                </div>
              ))}
            </div>
          </div>
        )}

        <div>
          <h4 className="text-sm font-medium text-zinc-900 mb-2">Execution time:</h4>
          <input
            type="time"
            value={executionTime}
            onChange={(e) => setExecutionTime(e.target.value)}
            className="px-3 py-2 border border-zinc-300 rounded-lg"
          />
          <span className="ml-2 text-sm text-zinc-600">EST</span>
        </div>

        <div className="flex justify-between pt-6">
          <Button variant="outline" disabled className="text-zinc-700 border-zinc-300">
            Cancel
          </Button>
          <Button onClick={handleNext} className="bg-zinc-900 text-white hover:bg-zinc-800">
            Next Step
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
