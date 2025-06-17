
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const PriceActionAnalysis: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Price Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-light text-zinc-700">PRICE METRICS</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-6 text-sm">
            <div>
              <span className="text-zinc-600">Current Price:</span>
              <span className="ml-2 font-medium">$450.25 <span className="text-green-600">(+0.35%)</span></span>
            </div>
            <div>
              <span className="text-zinc-600">Daily Range:</span>
              <span className="ml-2 font-medium">$449.10 - $451.30</span>
            </div>
            <div>
              <span className="text-zinc-600">Support:</span>
              <span className="ml-2 font-medium">$448.50</span>
            </div>
            <div>
              <span className="text-zinc-600">Resistance:</span>
              <span className="ml-2 font-medium">$452.75</span>
            </div>
            <div>
              <span className="text-zinc-600">Expected Move (1d):</span>
              <span className="ml-2 font-medium">+/-$2.25</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Technical Levels */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">TECHNICAL LEVELS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Technical Chart]
            </div>
            <div className="space-y-2 text-sm">
              <div className="text-zinc-600 font-medium mb-2">Key Levels:</div>
              <div>• Support: $448.50, $445.80</div>
              <div>• Resistance: $452.75, $455.20</div>
              <div>• 50 DMA: $447.85</div>
              <div>• 200 DMA: $442.30</div>
            </div>
          </CardContent>
        </Card>

        {/* Implied Move Analysis */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">IMPLIED MOVE ANALYSIS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Implied Move Chart]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">1-Day Implied Move:</span>
                <span className="font-medium">+/-$2.25</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">1-Week Implied Move:</span>
                <span className="font-medium">+/-$5.10</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Implied vs Historical:</span>
                <span className="font-medium">IMPLIED &gt; HISTORICAL</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Realized Move (Avg):</span>
                <span className="font-medium">+/-$1.85</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Price vs. Volatility */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">PRICE VS. VOLATILITY</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Price/Vol Chart]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Price Trend:</span>
                <span className="font-medium">SIDEWAYS</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Volatility Trend:</span>
                <span className="font-medium">RISING</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Price/Vol Correlation:</span>
                <span className="font-medium">-0.65</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Volatility Regime:</span>
                <span className="font-medium">MODERATE</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Market Internals */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">MARKET INTERNALS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Internals Chart]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Advance/Decline:</span>
                <span className="font-medium">+1.2:1</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Up/Down Volume:</span>
                <span className="font-medium">+1.5:1</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">New Highs/Lows:</span>
                <span className="font-medium">125/42</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Market Breadth:</span>
                <span className="font-medium">POSITIVE</span>
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
            <li>• Sideways price action with rising volatility favors premium selling</li>
            <li>• Implied move exceeds historical realized move by 21%</li>
            <li>• Strong support at $448.50 aligns with high put open interest</li>
            <li>• Positive market internals suggest limited downside risk</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};
