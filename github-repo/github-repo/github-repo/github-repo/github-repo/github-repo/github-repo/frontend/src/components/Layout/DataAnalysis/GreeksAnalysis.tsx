
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const GreeksAnalysis: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Greeks Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-light text-zinc-700">GREEKS OVERVIEW</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <p className="text-sm text-zinc-600 mb-2">Selected Option: SPY 450 Put (1 DTE)</p>
            <div className="flex items-center space-x-6 text-sm">
              <span>Price: $4.65 <span className="text-green-600">(+8.1%)</span></span>
              <span>Volume: 4,850</span>
              <span>OI: 15,420</span>
              <span>IV: 22.4%</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* First-Order Greeks Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Delta Analysis */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">DELTA ANALYSIS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Delta Visualization]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Delta:</span>
                <span className="font-medium">-0.30</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Probability ITM:</span>
                <span className="font-medium">30%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Hedge Ratio:</span>
                <span className="font-medium">30 shares/opt</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Delta Dollars:</span>
                <span className="font-medium">$1,350</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Delta/Theta Ratio:</span>
                <span className="font-medium">2.5</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Theta Analysis */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">THETA ANALYSIS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Theta Decay Curve]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Theta:</span>
                <span className="font-medium">-0.12</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Daily Decay:</span>
                <span className="font-medium">$12 per contract</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Weekend Effect:</span>
                <span className="font-medium">+$8 per day</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Optimal Hold Time:</span>
                <span className="font-medium">12-16 hrs</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Theta Acceleration:</span>
                <span className="font-medium">HIGH</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Gamma Analysis */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">GAMMA ANALYSIS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Gamma Visualization]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Gamma:</span>
                <span className="font-medium">0.04</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Gamma Exposure:</span>
                <span className="font-medium">$180 per 1%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Gamma Scalping Threshold:</span>
                <span className="font-medium">$0.90 move</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Gamma Risk:</span>
                <span className="font-medium">MODERATE</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Vega Analysis */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">VEGA ANALYSIS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Vega Visualization]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Vega:</span>
                <span className="font-medium">0.18</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Vega Exposure:</span>
                <span className="font-medium">$18 per 1% IV</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">IV Change (1d):</span>
                <span className="font-medium">+1.2%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Vega Effect:</span>
                <span className="font-medium">+$21.60</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Vega Risk:</span>
                <span className="font-medium">MODERATE</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Second-Order Greeks */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-light text-zinc-700">SECOND-ORDER GREEKS</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-6 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-600">Charm (Delta Decay):</span>
              <span className="font-medium">-0.01</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-600">Color (Gamma Decay):</span>
              <span className="font-medium">-0.008</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-600">Vanna (Delta/Volatility):</span>
              <span className="font-medium">-0.15</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-600">Vomma (Vega/Volatility):</span>
              <span className="font-medium">0.04</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-600">Zomma (Gamma/Volatility):</span>
              <span className="font-medium">-0.02</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-600">Ultima (Vomma/Volatility):</span>
              <span className="font-medium">0.005</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Trading Implications */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-light text-zinc-700">TRADING IMPLICATIONS</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-zinc-600">
            <li>• 30% probability of expiring ITM suggests favorable odds for sellers</li>
            <li>• High theta decay acceleration in final 12-16 hours</li>
            <li>• Moderate gamma risk indicates manageable price sensitivity</li>
            <li>• Vega exposure suggests monitoring volatility changes closely</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};
