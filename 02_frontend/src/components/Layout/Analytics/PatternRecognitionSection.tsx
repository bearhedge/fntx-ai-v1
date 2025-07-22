
import React from 'react';
import { AnalyticsSection, AnalyticsCard } from './AnalyticsSection';

export const PatternRecognitionSection: React.FC = () => {
  return (
    <AnalyticsSection title="Pattern Recognition">
      <AnalyticsCard
        title="SUCCESS PATTERNS"
        actionLabel="Apply Strategy"
        onAction={() => console.log('Apply success patterns')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Your top strategies:</span></p>
          <p>- OTM Put options</p>
          <p>- 2-3 day expiry</p>
          <p>- IV Rank &gt; 70%</p>
          <p><span className="font-medium">Win rate:</span> 78%</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="MARKET CONDITIONS"
        actionLabel="View Strategies"
        onAction={() => console.log('View market strategies')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Current environment:</span> HIGH VOLATILITY, BEARISH TREND</p>
          <p><span className="font-medium">Optimal strategies:</span></p>
          <p>- Put credit spreads</p>
          <p>- Short-term iron condors</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="FAILURE ANALYSIS"
        actionLabel="Improvement Plan"
        onAction={() => console.log('View improvement plan')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Common mistakes:</span></p>
          <p>- Holding too long</p>
          <p>- Insufficient stop loss discipline</p>
          <p>- Overtrading during low volatility</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="NEXT BEST ACTION"
        actionLabel="Execute Trade"
        onAction={() => console.log('Execute recommended trade')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Recommended trade:</span> PUT option</p>
          <p><span className="font-medium">Strike:</span> 530</p>
          <p><span className="font-medium">Expiry:</span> 3 days</p>
          <p><span className="font-medium">Confidence:</span> 87%</p>
        </div>
      </AnalyticsCard>
    </AnalyticsSection>
  );
};
