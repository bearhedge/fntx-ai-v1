
import React, { useState } from 'react';
import { TimingConfiguration } from './TimingConfiguration';
import { ContractSelection } from './ContractSelection';
import { RiskLevel } from './RiskLevel';
import { RiskManagement } from './RiskManagement';
import { ContingencyActions } from './ContingencyActions';
import { AutomationSummary } from './AutomationSummary';

export const AutomationContent: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [automationData, setAutomationData] = useState({
    timing: {},
    contract: {},
    riskLevel: {},
    riskManagement: {},
    contingency: {}
  });

  const updateAutomationData = (step: string, data: any) => {
    setAutomationData(prev => ({
      ...prev,
      [step]: data
    }));
  };

  const nextStep = () => {
    if (currentStep < 5) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return (
          <TimingConfiguration
            data={automationData.timing}
            onUpdate={(data) => updateAutomationData('timing', data)}
            onNext={nextStep}
          />
        );
      case 1:
        return (
          <ContractSelection
            data={automationData.contract}
            onUpdate={(data) => updateAutomationData('contract', data)}
            onNext={nextStep}
            onBack={prevStep}
          />
        );
      case 2:
        return (
          <RiskLevel
            data={automationData.riskLevel}
            onUpdate={(data) => updateAutomationData('riskLevel', data)}
            onNext={nextStep}
            onBack={prevStep}
          />
        );
      case 3:
        return (
          <RiskManagement
            data={automationData.riskManagement}
            onUpdate={(data) => updateAutomationData('riskManagement', data)}
            onNext={nextStep}
            onBack={prevStep}
          />
        );
      case 4:
        return (
          <ContingencyActions
            data={automationData.contingency}
            onUpdate={(data) => updateAutomationData('contingency', data)}
            onNext={nextStep}
            onBack={prevStep}
          />
        );
      case 5:
        return (
          <AutomationSummary
            data={automationData}
            onBack={prevStep}
            onEdit={(step) => setCurrentStep(step)}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="p-6">
      {renderStep()}
    </div>
  );
};
