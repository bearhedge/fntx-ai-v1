import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowUp, ArrowDown, DollarSign, TrendingUp, AlertCircle, CheckCircle, HelpCircle } from 'lucide-react';
import { Line, LineChart, ResponsiveContainer, XAxis, YAxis, Tooltip as RechartsTooltip, CartesianGrid } from 'recharts';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';

interface NAVData {
  current_nav: number;
  available_cash: number;
  positions_value: number;
  pending_withdrawals: number;
  ytd_withdrawals: number;
  last_updated: string;
}

interface NAVHistory {
  snapshot_date: string;
  opening_nav: number;
  closing_nav: number | null;
  trading_pnl: number | null;
  is_reconciled: boolean;
}

interface ReconciliationStatus {
  date: string;
  status: string;
  discrepancy: number | null;
  is_balanced: boolean;
}

export const PerformanceContent: React.FC = () => {
  const [navData, setNavData] = useState<NAVData | null>(null);
  const [navHistory, setNavHistory] = useState<NAVHistory[]>([]);
  const [reconciliation, setReconciliation] = useState<ReconciliationStatus[]>([]);
  const [timeframe, setTimeframe] = useState<'7d' | '30d' | '90d'>('30d');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNavData();
    fetchNavHistory();
    fetchReconciliation();
  }, [timeframe]);

  const fetchNavData = async () => {
    try {
      const response = await fetch('/api/portfolio/nav/current');
      const data = await response.json();
      setNavData(data);
    } catch (error) {
      console.error('Error fetching NAV data:', error);
    }
  };

  const fetchNavHistory = async () => {
    try {
      const days = timeframe === '7d' ? 7 : timeframe === '30d' ? 30 : 90;
      const response = await fetch(`/api/portfolio/nav/history?days=${days}`);
      const data = await response.json();
      setNavHistory(data);
    } catch (error) {
      console.error('Error fetching NAV history:', error);
    }
  };

  const fetchReconciliation = async () => {
    try {
      const days = timeframe === '7d' ? 7 : timeframe === '30d' ? 30 : 90;
      const response = await fetch(`/api/portfolio/reconciliation/status?days=${days}`);
      const data = await response.json();
      setReconciliation(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching reconciliation:', error);
      setLoading(false);
    }
  };

  const runReconciliation = async () => {
    try {
      const response = await fetch('/api/portfolio/reconciliation/run', { method: 'POST' });
      if (response.ok) {
        fetchReconciliation();
      }
    } catch (error) {
      console.error('Error running reconciliation:', error);
    }
  };

  // Calculate performance metrics
  const calculateMetrics = () => {
    if (!navHistory.length) return { change: 0, changePercent: 0, isPositive: true };
    
    const firstNav = navHistory[navHistory.length - 1].opening_nav;
    const lastNav = navHistory[0].closing_nav || navHistory[0].opening_nav;
    const change = lastNav - firstNav;
    const changePercent = (change / firstNav) * 100;
    
    return {
      change,
      changePercent,
      isPositive: change >= 0
    };
  };

  const metrics = calculateMetrics();

  // Prepare chart data
  const chartData = navHistory.map(item => ({
    date: new Date(item.snapshot_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    nav: item.closing_nav || item.opening_nav,
    pnl: item.trading_pnl || 0
  })).reverse();

  if (loading) {
    return <div className="flex items-center justify-center h-96">Loading...</div>;
  }

  // Performance metrics data
  const performanceMetrics = [
    { label: "DPI", value: "0.05x", tooltip: "Distributions to Paid-In capital" },
    { label: "RVPI", value: "0.95x", tooltip: "Residual Value to Paid-In capital" },
    { label: "TVPI", value: "1.00x", tooltip: "Total Value to Paid-In capital" },
    { label: "MOIC", value: "1.00x", tooltip: "Multiple on Invested Capital" },
    { label: "IRR", value: "0.40%", tooltip: "Internal Rate of Return" },
    { label: "NAV", value: `HKD ${navData?.current_nav.toLocaleString() || '0'}`, tooltip: "Net Asset Value" },
    { label: "Principal", value: "HKD 1,000,000", tooltip: "Initial Investment" },
    { label: "Exercise Ratio", value: "8.00%", tooltip: "Options Exercised / Total Traded" },
    { label: "Time to Liquidity", value: "3.4 hours", tooltip: "Average time to exit positions" },
    { label: "Sharpe Ratio", value: "1.00", tooltip: "Risk-adjusted returns" },
    { label: "Take-profit Ratio", value: "10%", tooltip: "Percentage take profit target" },
    { label: "Stop-loss Ratio", value: "40%", tooltip: "Percentage stop loss limit" },
    { label: "Stop-loss Multiple", value: "3.00x", tooltip: "Risk/Reward ratio" },
    { label: "Take-profit Multiple", value: "0.15x", tooltip: "Profit target multiple" },
    { label: "Maximum Drawdown", value: "5%", tooltip: "Largest peak-to-trough decline" },
    { label: "Win Rate", value: "40%", tooltip: "Percentage of profitable trades" }
  ];

  return (
    <TooltipProvider>
      <div className="space-y-6">
      {/* Performance Metrics Grid */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Performance Metrics</h3>
        <div className="grid grid-cols-4 gap-3">
          {performanceMetrics.map((metric, index) => (
            <Card key={index} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">{metric.label}</p>
                    <p className="text-lg font-bold">{metric.value}</p>
                  </div>
                  <Tooltip>
                    <TooltipTrigger>
                      <HelpCircle className="w-4 h-4 text-gray-400" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{metric.tooltip}</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* NAV Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Net Asset Value</p>
                <p className="text-2xl font-bold">${navData?.current_nav.toLocaleString() || '0'}</p>
                <div className={`flex items-center text-sm ${metrics.isPositive ? 'text-green-600' : 'text-red-600'}`}>
                  {metrics.isPositive ? <ArrowUp className="w-4 h-4 mr-1" /> : <ArrowDown className="w-4 h-4 mr-1" />}
                  {Math.abs(metrics.changePercent).toFixed(2)}% (${Math.abs(metrics.change).toLocaleString()})
                </div>
              </div>
              <DollarSign className="w-8 h-8 text-gray-400" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Available Cash</p>
                <p className="text-2xl font-bold">${navData?.available_cash.toLocaleString() || '0'}</p>
                <p className="text-sm text-gray-500">
                  {navData && navData.pending_withdrawals > 0 
                    ? `$${navData.pending_withdrawals.toLocaleString()} pending`
                    : 'No pending withdrawals'}
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-gray-400" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Positions Value</p>
                <p className="text-2xl font-bold">${navData?.positions_value.toLocaleString() || '0'}</p>
                <p className="text-sm text-gray-500">Open positions</p>
              </div>
              <TrendingUp className="w-8 h-8 text-gray-400" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">YTD Withdrawals</p>
                <p className="text-2xl font-bold">${navData?.ytd_withdrawals.toLocaleString() || '0'}</p>
                <p className="text-sm text-gray-500">Total withdrawn</p>
              </div>
              <DollarSign className="w-8 h-8 text-gray-400" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* NAV Chart */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>NAV History</CardTitle>
            <div className="flex gap-2">
              {(['7d', '30d', '90d'] as const).map(tf => (
                <Button
                  key={tf}
                  variant={timeframe === tf ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTimeframe(tf)}
                >
                  {tf}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" stroke="#888" fontSize={12} />
                <YAxis stroke="#888" fontSize={12} />
                <RechartsTooltip 
                  formatter={(value: any) => `$${Number(value).toLocaleString()}`}
                  contentStyle={{ backgroundColor: '#fff', border: '1px solid #e0e0e0' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="nav" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Reconciliation Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Daily Reconciliation Status</CardTitle>
            <Button onClick={runReconciliation} size="sm">
              Run Reconciliation
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {reconciliation.slice(0, 7).map(item => (
              <div key={item.date} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div>
                    {item.is_balanced ? (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-yellow-500" />
                    )}
                  </div>
                  <div>
                    <p className="font-medium">
                      {new Date(item.date).toLocaleDateString('en-US', { 
                        weekday: 'short', 
                        month: 'short', 
                        day: 'numeric' 
                      })}
                    </p>
                    <p className="text-sm text-gray-600">
                      {item.status === 'balanced' ? 'Balanced' : 
                       item.status === 'pending' ? 'Pending' : 'Discrepancy'}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  {item.discrepancy && Math.abs(item.discrepancy) > 0.01 && (
                    <p className="text-sm text-red-600">
                      ${Math.abs(item.discrepancy).toFixed(2)} discrepancy
                    </p>
                  )}
                  {item.is_balanced && (
                    <p className="text-sm text-green-600">Reconciled</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
    </TooltipProvider>
  );
};