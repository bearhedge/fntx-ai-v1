import React from 'react';
import { Button } from "@/components/ui/button";
interface AnalyticsSectionProps {
  title: string;
  children: React.ReactNode;
}
export const AnalyticsSection: React.FC<AnalyticsSectionProps> = ({
  title,
  children
}) => {
  return <div className="space-y-4">
      <h3 className="border-gray-0 pb-2 text-zinc-950 font-extralight text-lg text-center ">
        {title}
      </h3>
      <div className="grid grid-cols-2 gap-4">
        {children}
      </div>
    </div>;
};
interface AnalyticsCardProps {
  title: string;
  children: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
}
export const AnalyticsCard: React.FC<AnalyticsCardProps> = ({
  title,
  children,
  actionLabel,
  onAction
}) => {
  return <div className="rounded-lg p-4 space-y-3 border border-gray-200 bg-gray-200">
      <h4 className="text-gray-900 text-sm uppercase tracking-wide font-light">
        {title}
      </h4>
      <div className="space-y-2 text-sm text-gray-700">
        {children}
      </div>
      {actionLabel && onAction && <Button variant="outline" size="sm" onClick={onAction} className="w-full text-gray-950 font-light text-sm">
          {actionLabel}
        </Button>}
    </div>;
};