
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const OpenInterestAnalysis: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Open Interest Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-light text-zinc-700">OPEN INTEREST METRICS</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-6 text-sm">
            <div>
              <span className="text-zinc-600">Total Put OI:</span>
              <span className="ml-2 font-medium">125,450</span>
            </div>
            <div>
              <span className="text-zinc-600">Total Call OI:</span>
              <span className="ml-2 font-medium">108,750</span>
            </div>
            <div>
              <span className="text-zinc-600">Put/Call OI Ratio:</span>
              <span className="ml-2 font-medium">1.15</span>
            </div>
            <div>
              <span className="text-zinc-600">OI Change (1d):</span>
              <span className="ml-2 font-medium">+8.8% at 450P</span>
            </div>
            <div>
              <span className="text-zinc-600">OI Percentile:</span>
              <span className="ml-2 font-medium">92%</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* OI by Strike */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">OI BY STRIKE</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [OI Strike Chart]
            </div>
            <div className="space-y-2 text-sm">
              <div className="text-zinc-600 font-medium mb-2">Key Strikes:</div>
              <div>• 450: 15,420 (Put)</div>
              <div>• 455: 14,250 (Call)</div>
              <div>• 445: 10,120 (Put)</div>
              <div>• 460: 8,320 (Call)</div>
            </div>
          </CardContent>
        </Card>

        {/* OI Change Over Time */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">OI CHANGE OVER TIME</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [OI Change Chart]
            </div>
            <div className="space-y-2 text-sm">
              <div className="text-zinc-600 font-medium mb-2">Notable Changes:</div>
              <div>• 450P: +1,245 contracts</div>
              <div>• 445P: +850 contracts</div>
              <div>• 455C: +920 contracts</div>
              <div className="mt-3">
                <span className="text-zinc-600">Accumulation Pattern:</span>
                <span className="ml-2 font-medium">BEARISH</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Volume/OI Ratio */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">VOLUME/OI RATIO</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [V/OI Chart]
            </div>
            <div className="space-y-2 text-sm">
              <div className="text-zinc-600 font-medium mb-2">High V/OI Ratios:</div>
              <div>• 445P: 0.28</div>
              <div>• 450P: 0.31</div>
              <div>• 455C: 0.29</div>
              <div className="mt-3">
                <span className="text-zinc-600">Unusual Activity:</span>
                <span className="ml-2 font-medium">445P, 450P</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Put/Call Analysis */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">PUT/CALL ANALYSIS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Put/Call Chart]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Put/Call Volume:</span>
                <span className="font-medium">1.35</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Put/Call OI:</span>
                <span className="font-medium">1.15</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Put/Call Premium:</span>
                <span className="font-medium">1.42</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Put/Call IV:</span>
                <span className="font-medium">1.08</span>
              </div>
              <div className="mt-3">
                <span className="text-zinc-600">Sentiment:</span>
                <span className="ml-2 font-medium">BEARISH</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Trading Implications */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-light text-zinc-700">TRADING IMPLICATIONS</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-zinc-600">
            <li>• High OI concentration at 450 strike may act as price magnet</li>
            <li>• Increasing put OI suggests growing downside protection demand</li>
            <li>• Elevated V/OI ratio at 445P indicates active positioning</li>
            <li>• Overall put/call metrics confirm bearish sentiment bias</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};
