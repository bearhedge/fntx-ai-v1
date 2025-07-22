
import React from 'react';
import { AnalyticsSection, AnalyticsCard } from './AnalyticsSection';

export const GreeksAnalysisSection: React.FC = () => {
  return (
    <AnalyticsSection title="Greeks Analysis">
      <AnalyticsCard
        title="DELTA EXPOSURE"
        actionLabel="Adjust Positions"
        onAction={() => console.log('Adjust delta positions')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Current portfolio:</span> Delta: -0.32</p>
          <p className="text-gray-600">(32% probability)</p>
          <p><span className="font-medium">Recommended range:</span> -0.25 to -0.40</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="THETA DECAY CURVE"
        actionLabel="View Decay Chart"
        onAction={() => console.log('View theta decay chart')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Current positions:</span> $15.20/day decay</p>
          <p><span className="font-medium">Optimal exit point:</span> June 12 (3 days)</p>
          <p className="text-gray-600">(40% time value)</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="VEGA RISK PROFILE"
        actionLabel="Volatility Strategy"
        onAction={() => console.log('View volatility strategy')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Volatility exposure:</span> MODERATE</p>
          <p><span className="font-medium">IV Rank:</span> 68%</p>
          <p className="text-gray-600">(Premium selling favorable)</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="GAMMA SCALPING"
        actionLabel="Hedging Strategy"
        onAction={() => console.log('View hedging strategy')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Current gamma:</span> 0.08</p>
          <p><span className="font-medium">Potential daily profit from hedging:</span> $45 per contract</p>
        </div>
      </AnalyticsCard>
    </AnalyticsSection>
  );
};
