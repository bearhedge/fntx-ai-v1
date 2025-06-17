
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export const OptionsChainAnalysis: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Expiration Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-zinc-600">Expiration: 1 DTE (Jun 9, 2025)</span>
        <Button variant="outline" size="sm">Change Expiration</Button>
      </div>

      {/* Options Chain Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b bg-gray-50">
                <tr>
                  <th className="text-left p-3 font-medium text-zinc-700" colSpan={5}>PUTS</th>
                  <th className="text-center p-3 font-medium text-zinc-700">Strike</th>
                  <th className="text-right p-3 font-medium text-zinc-700" colSpan={5}>CALLS</th>
                </tr>
                <tr className="text-xs text-zinc-500 border-b">
                  <th className="text-left p-2">Vol</th>
                  <th className="text-left p-2">OI</th>
                  <th className="text-left p-2">IV</th>
                  <th className="text-left p-2">Delta</th>
                  <th className="text-left p-2">Bid/Ask</th>
                  <th className="text-center p-2 font-medium"></th>
                  <th className="text-right p-2">Bid/Ask</th>
                  <th className="text-right p-2">Delta</th>
                  <th className="text-right p-2">IV</th>
                  <th className="text-right p-2">OI</th>
                  <th className="text-right p-2">Vol</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b hover:bg-gray-50">
                  <td className="p-2">1,245</td>
                  <td className="p-2">8,245</td>
                  <td className="p-2">26.8%</td>
                  <td className="p-2">-0.15</td>
                  <td className="p-2">0.80/0.90</td>
                  <td className="p-2 text-center font-medium">440</td>
                  <td className="p-2 text-right">9.85/10.05</td>
                  <td className="p-2 text-right">0.85</td>
                  <td className="p-2 text-right">20.2%</td>
                  <td className="p-2 text-right">5,120</td>
                  <td className="p-2 text-right">845</td>
                </tr>
                <tr className="border-b hover:bg-gray-50">
                  <td className="p-2">2,850</td>
                  <td className="p-2">10,120</td>
                  <td className="p-2">24.5%</td>
                  <td className="p-2">-0.25</td>
                  <td className="p-2">1.85/2.05</td>
                  <td className="p-2 text-center font-medium">445</td>
                  <td className="p-2 text-right">5.95/6.15</td>
                  <td className="p-2 text-right">0.75</td>
                  <td className="p-2 text-right">21.5%</td>
                  <td className="p-2 text-right">7,850</td>
                  <td className="p-2 text-right">1,250</td>
                </tr>
                <tr className="border-b hover:bg-gray-50 bg-yellow-50">
                  <td className="p-2 font-medium">4,850</td>
                  <td className="p-2 font-medium">15,420</td>
                  <td className="p-2 font-medium">22.4%</td>
                  <td className="p-2 font-medium">-0.50</td>
                  <td className="p-2 font-medium">4.55/4.75</td>
                  <td className="p-2 text-center font-bold">450</td>
                  <td className="p-2 text-right font-medium">2.95/3.15</td>
                  <td className="p-2 text-right font-medium">0.50</td>
                  <td className="p-2 text-right font-medium">22.8%</td>
                  <td className="p-2 text-right font-medium">12,540</td>
                  <td className="p-2 text-right font-medium">3,750</td>
                </tr>
                <tr className="border-b hover:bg-gray-50">
                  <td className="p-2">2,120</td>
                  <td className="p-2">9,850</td>
                  <td className="p-2">23.1%</td>
                  <td className="p-2">-0.75</td>
                  <td className="p-2">8.65/8.85</td>
                  <td className="p-2 text-center font-medium">455</td>
                  <td className="p-2 text-right">1.15/1.35</td>
                  <td className="p-2 text-right">0.25</td>
                  <td className="p-2 text-right">24.2%</td>
                  <td className="p-2 text-right">14,250</td>
                  <td className="p-2 text-right">4,120</td>
                </tr>
                <tr className="border-b hover:bg-gray-50">
                  <td className="p-2">980</td>
                  <td className="p-2">6,540</td>
                  <td className="p-2">25.7%</td>
                  <td className="p-2">-0.85</td>
                  <td className="p-2">13.4/13.6</td>
                  <td className="p-2 text-center font-medium">460</td>
                  <td className="p-2 text-right">0.35/0.55</td>
                  <td className="p-2 text-right">0.15</td>
                  <td className="p-2 text-right">26.5%</td>
                  <td className="p-2 text-right">8,320</td>
                  <td className="p-2 text-right">1,850</td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Volume Heatmap */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">VOLUME HEATMAP</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [Volume Visualization]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Highest Volume:</span>
                <span className="font-medium">450P, 455C</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Volume Concentration:</span>
                <span className="font-medium">ATM</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Put/Call Volume Ratio:</span>
                <span className="font-medium">1.35</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Unusual Activity:</span>
                <span className="font-medium">445P</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Open Interest Heatmap */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium text-zinc-700">OPEN INTEREST HEATMAP</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500 text-sm mb-4">
              [OI Visualization]
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-600">Highest OI:</span>
                <span className="font-medium">450P, 455C</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">OI Concentration:</span>
                <span className="font-medium">ATM</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Put/Call OI Ratio:</span>
                <span className="font-medium">1.15</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-600">Notable OI Change:</span>
                <span className="font-medium">+8.8% 450P</span>
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
            <li>• High open interest at 450 strike suggests potential support/resistance</li>
            <li>• Unusual volume in 445 puts may indicate defensive positioning</li>
            <li>• Put/call volume ratio of 1.35 shows bearish sentiment bias</li>
            <li>• IV skew across strikes confirms downside protection demand</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};
