
import React from 'react';
import { MandateOverview } from './MandateOverview';
import { MandateDetails } from './MandateDetails';
import { ComplianceVerification } from './ComplianceVerification';
import { ModificationRequest } from './ModificationRequest';

export const PermissionsContent: React.FC = () => {
  return (
    <div className="p-6 space-y-8">
      <MandateOverview />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MandateDetails />
        <ComplianceVerification />
      </div>
      <ModificationRequest />
    </div>
  );
};
