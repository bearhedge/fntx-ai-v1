
import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { VolatilityAnalysis } from './VolatilityAnalysis';
import { GreeksAnalysis } from './GreeksAnalysis';
import { OptionsChainAnalysis } from './OptionsChainAnalysis';
import { OpenInterestAnalysis } from './OpenInterestAnalysis';
import { PriceActionAnalysis } from './PriceActionAnalysis';

export const DataAnalysisContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState('volatility');

  return (
    <div className="p-6">
      {/* Market Overview Header */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between text-sm text-gray-700">
          <div className="flex items-center space-x-6">
            <span className="font-medium">SPY: $450.25 <span className="text-green-600">(+0.35%)</span></span>
            <span>IV Rank: 65%</span>
            <span>VIX: 18.5</span>
          </div>
          <span>Date: Jun 8, 2025</span>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5 mb-6">
          <TabsTrigger value="volatility" className="text-sm">Volatility</TabsTrigger>
          <TabsTrigger value="greeks" className="text-sm">Greeks</TabsTrigger>
          <TabsTrigger value="options-chain" className="text-sm">Options Chain</TabsTrigger>
          <TabsTrigger value="open-interest" className="text-sm">Open Interest</TabsTrigger>
          <TabsTrigger value="price-action" className="text-sm">Price Action</TabsTrigger>
        </TabsList>

        <TabsContent value="volatility">
          <VolatilityAnalysis />
        </TabsContent>
        
        <TabsContent value="greeks">
          <GreeksAnalysis />
        </TabsContent>
        
        <TabsContent value="options-chain">
          <OptionsChainAnalysis />
        </TabsContent>
        
        <TabsContent value="open-interest">
          <OpenInterestAnalysis />
        </TabsContent>
        
        <TabsContent value="price-action">
          <PriceActionAnalysis />
        </TabsContent>
      </Tabs>
    </div>
  );
};
