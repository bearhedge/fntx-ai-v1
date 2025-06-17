
import React from 'react';
import { RiskManagementSection } from './RiskManagementSection';
import { GreeksAnalysisSection } from './GreeksAnalysisSection';
import { PatternRecognitionSection } from './PatternRecognitionSection';
import { WithdrawalAnalyticsSection } from './WithdrawalAnalyticsSection';

export const AnalyticsTab: React.FC = () => {
  return (
    <div className="space-y-8">
      <RiskManagementSection />
      <GreeksAnalysisSection />
      <PatternRecognitionSection />
      <WithdrawalAnalyticsSection />
    </div>
  );
};
