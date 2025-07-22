
import React from 'react';
import { AnalyticsSection, AnalyticsCard } from './AnalyticsSection';

export const RiskManagementSection: React.FC = () => {
  return (
    <AnalyticsSection title="Risk Management">
      <AnalyticsCard
        title="STOP-LOSS OPTIMIZER"
        actionLabel="Apply to All Trades"
        onAction={() => console.log('Apply stop-loss optimization')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Optimal stop-loss:</span> 3.2x premium</p>
          <p className="text-gray-600">($176 per contract)</p>
          <p><span className="font-medium">Win rate with this level:</span> 78%</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="DELTA/THETA BALANCE"
        actionLabel="View Strategy"
        onAction={() => console.log('View delta/theta strategy')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Current portfolio:</span></p>
          <p>Delta: -0.32</p>
          <p>Theta: +0.15</p>
          <p><span className="font-medium">Recommendation:</span> Increase theta exposure by 20%</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="TAKE-PROFIT TIMING"
        actionLabel="Apply to All Trades"
        onAction={() => console.log('Apply take-profit timing')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Optimal take-profit:</span> 45% of premium</p>
          <p className="text-gray-600">($24.75 per contract)</p>
          <p><span className="font-medium">Best timing:</span> Day 2 (40% time decay)</p>
        </div>
      </AnalyticsCard>

      <AnalyticsCard
        title="RISK ASSESSMENT"
        actionLabel="Adjust Parameters"
        onAction={() => console.log('Adjust risk parameters')}
      >
        <div className="space-y-1">
          <p><span className="font-medium">Current risk profile:</span> MODERATE (0.68)</p>
          <p><span className="font-medium">Optimal risk level based on history:</span> LOW-MODERATE (0.45)</p>
        </div>
      </AnalyticsCard>
    </AnalyticsSection>
  );
};
