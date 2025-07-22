
import React from 'react';
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface TabNavigationProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export const TabNavigation: React.FC<TabNavigationProps> = ({
  activeTab,
  onTabChange
}) => {
  return <Tabs value={activeTab} onValueChange={onTabChange} className="w-full py-2">
      <TabsList className="grid grid-cols-4 mb-4 py-0 bg-stone-200 rounded-none w-full h-10">
        <TabsTrigger value="performance" className={`text-sm font-normal py-2 px-4 ${activeTab === 'performance' ? 'font-bold' : ''}`}>PERFORMANCE</TabsTrigger>
        <TabsTrigger value="history" className={`text-sm font-normal py-2 px-4 ${activeTab === 'history' ? 'font-bold' : ''}`}>HISTORY</TabsTrigger>
        <TabsTrigger value="withdrawals" className={`text-sm font-normal py-2 px-4 ${activeTab === 'withdrawals' ? 'font-bold' : ''}`}>WITHDRAWALS</TabsTrigger>
        <TabsTrigger value="analytics" className={`text-sm font-normal py-2 px-4 ${activeTab === 'analytics' ? 'font-bold' : ''}`}>ANALYTICS</TabsTrigger>
      </TabsList>
    </Tabs>;
};
