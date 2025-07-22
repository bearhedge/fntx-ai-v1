
import React from 'react';
import { AnalyticsSection, AnalyticsCard } from './AnalyticsSection';

export const WithdrawalAnalyticsSection: React.FC = () => {
  return (
    <AnalyticsSection title="Withdrawal Analytics">
      <AnalyticsCard
        title="WITHDRAWAL OPTIMIZER"
        actionLabel="Schedule Withdrawal"
        onAction={() => console.log('Schedule optimized withdrawal')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Optimal withdrawal:</span> $1,850 this month</p>
          <p><span className="font-medium">Based on:</span></p>
          <p>- Trading performance</p>
          <p>- Upcoming liquidity</p>
          <p>- Historical patterns</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="LIQUIDITY FORECAST"
        actionLabel="View Forecast"
        onAction={() => console.log('View liquidity forecast')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Next 30 days:</span> +$2,320 available on June 15</p>
          <p><span className="font-medium">Next 90 days:</span> +$5,640 total</p>
          <p className="text-gray-600">(see detailed timeline)</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="WITHDRAWAL IMPACT"
        actionLabel="Adjust Strategy"
        onAction={() => console.log('Adjust withdrawal strategy')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Effect on portfolio:</span></p>
          <p>- 8% capital reduction</p>
          <p>- 5% reduced exposure</p>
          <p>- Minimal impact on strategy performance</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="WITHDRAWAL PATTERNS"
        actionLabel="Optimize Schedule"
        onAction={() => console.log('Optimize withdrawal schedule')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Your withdrawal frequency:</span> Monthly</p>
          <p><span className="font-medium">Avg withdrawal:</span> $1,240 (12% of NAV)</p>
        </div>
      </AnalyticsCard>
    </AnalyticsSection>
  );
};
