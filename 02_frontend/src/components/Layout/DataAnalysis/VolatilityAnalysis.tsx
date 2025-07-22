
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const VolatilityAnalysis: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Volatility Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-light text-zinc-700">VOLATILITY METRICS</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-6 text-sm">
            <div>
              <span className="text-zinc-600">Current IV:</span>
              <span className="ml-2 font-medium">22.4% <span className="text-green-600">(+1.2%)</span></span>
            </div>
            <div>
              <span className="text-zinc-600">IV Rank:</span>
              <span className="ml-2 font-medium">65%</span>
            </div>
            <div>
              <span className="text-zinc-600">IV Percentile:</span>
              <span className="ml-2 font-medium">72%</span>
            </div>
            <div>
              <span className="text-zinc-600">Historical Vol (30d):</span>
              <span className="ml-2 font-medium">18.7%</span>
            </div>
            <div>
              <span className="text-zinc-600">IV/HV Ratio:</span>
              <span className="ml-2 font-medium">1.20</span>
            </div>
            <div>
              <span className="text-zinc-600">VIX Term Structure:</span>
              <span className="ml-2 font-medium">Contango</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Volatility Skew */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">VOLATILITY SKEW</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Skew Chart Visualization]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Put Skew:</span>
                <span className="font-medium">STEEP</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Call Skew:</span>
                <span className="font-medium">MODERATE</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Put/Call Skew Ratio:</span>
                <span className="font-medium">1.15</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">25-Delta Risk Reversal:</span>
                <span className="font-medium">2.3%</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Volatility Term Structure */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">VOLATILITY TERM STRUCTURE</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Term Structure Chart]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Structure:</span>
                <span className="font-medium">NORMAL</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Front-month IV:</span>
                <span className="font-medium">22.4%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Back-month IV:</span>
                <span className="font-medium">21.8%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">IV Differential:</span>
                <span className="font-medium">+0.6%</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Volatility Smile */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">VOLATILITY SMILE</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Smile Chart Visualization]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">ATM IV:</span>
                <span className="font-medium">22.4%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">10-Delta Put IV:</span>
                <span className="font-medium">26.8%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">10-Delta Call IV:</span>
                <span className="font-medium">23.5%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Smile Curvature:</span>
                <span className="font-medium">PRONOUNCED</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Volatility Surface */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">VOLATILITY SURFACE</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Surface Visualization]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Surface Shape:</span>
                <span className="font-medium">NORMAL</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Skew Consistency:</span>
                <span className="font-medium">HIGH</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Term Structure Consistency:</span>
                <span className="font-medium">MODERATE</span>
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
            <li>• Elevated IV Rank (65%) suggests favorable conditions for premium selling</li>
            <li>• Steep put skew indicates market concern about downside risk</li>
            <li>• IV/HV ratio of 1.20 shows options are slightly overpriced</li>
            <li>• Normal term structure suggests no immediate volatility events expected</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};
