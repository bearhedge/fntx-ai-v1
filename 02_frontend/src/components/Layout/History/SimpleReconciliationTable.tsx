import React, { useState, useEffect } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';

interface TradeData {
  timestamp: string;
  opening_nav: number;
  closing_nav: number;
  contract: string;
  price: number;
  volume: number;
  commission: number;
  proceeds: number;
  status: string;
  pnl: number;
}

export const SimpleReconciliationTable: React.FC = () => {
  const [trades, setTrades] = useState<TradeData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch trades and NAV data
      const [tradesRes, navRes] = await Promise.all([
        fetch('/api/trades/history?limit=100&start_date=2025-06-20'),
        fetch('/api/portfolio/nav/history?start_date=2025-06-20&days=30')
      ]);

      const tradesData = await tradesRes.json();
      const navSnapshots = await navRes.json();
      
      // Convert to HKD and format for display
      const processedTrades = processTradesData(tradesData, navSnapshots);
      setTrades(processedTrades);
      
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const processTradesData = (tradesData: any, navSnapshots: any[]): TradeData[] => {
    const trades = Array.isArray(tradesData) ? tradesData : (tradesData.trades || []);
    const navByDate: Record<string, any> = {};
    
    navSnapshots.forEach(nav => {
      navByDate[nav.snapshot_date] = nav;
    });

    // IBKR exchange rate
    const USD_TO_HKD = 7.85;

    return trades.map(trade => {
      const tradeDate = trade.entry_time.split('T')[0];
      const nav = navByDate[tradeDate] || { opening_nav: 0, closing_nav: 0 };
      
      // Convert USD to HKD using IBKR rate
      const priceHKD = parseFloat(trade.entry_price) * USD_TO_HKD;
      const commissionHKD = parseFloat(trade.entry_commission) * USD_TO_HKD;
      const proceedsHKD = parseFloat(trade.entry_price) * Math.abs(trade.quantity) * 100 * USD_TO_HKD;
      
      // Determine status and P&L
      let status = 'OPEN';
      let pnlHKD = 0;
      
      if (trade.status === 'closed') {
        if (trade.exit_reason === 'expired') {
          status = 'EXPIRED';
          // Use IBKR P&L values directly
          pnlHKD = proceedsHKD - commissionHKD - (parseFloat(trade.exit_commission || 0) * USD_TO_HKD);
        } else {
          status = 'CLOSED';
          const exitCostHKD = parseFloat(trade.exit_price) * Math.abs(trade.quantity) * 100 * USD_TO_HKD;
          pnlHKD = proceedsHKD - exitCostHKD - commissionHKD - (parseFloat(trade.exit_commission || 0) * USD_TO_HKD);
        }
      }

      return {
        timestamp: new Date(trade.entry_time).toLocaleString('en-US', { 
          year: 'numeric', 
          month: '2-digit', 
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        }).replace(',', ''),
        opening_nav: parseFloat(nav.opening_nav),
        closing_nav: parseFloat(nav.closing_nav),
        contract: `SPY ${trade.strike_price}${trade.option_type[0]}`,
        price: priceHKD,
        volume: Math.abs(trade.quantity),
        commission: commissionHKD,
        proceeds: proceedsHKD,
        status: status,
        pnl: pnlHKD
      };
    });
  };

  const exportCSV = () => {
    const headers = ['Timestep', 'Opening NAV', 'Closing NAV', 'Contracts', 'Price', 'Volume', 'Commission', 'Proceeds', 'Status', 'PnL'];
    const rows = trades.map(t => [
      t.timestamp,
      t.opening_nav.toFixed(2),
      t.closing_nav.toFixed(2),
      t.contract,
      t.price.toFixed(2),
      t.volume,
      t.commission.toFixed(2),
      t.proceeds.toFixed(2),
      t.status,
      t.pnl.toFixed(2)
    ]);
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'nav_reconciliation.csv';
    a.click();
  };

  if (loading) {
    return <div className="p-4">Loading NAV reconciliation...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">NAV Reconciliation (HKD)</h3>
        <Button variant="outline" size="sm" onClick={exportCSV}>
          <Download className="h-4 w-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-md border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead>Timestep</TableHead>
              <TableHead className="text-right">Opening NAV</TableHead>
              <TableHead className="text-right">Closing NAV</TableHead>
              <TableHead>Contracts</TableHead>
              <TableHead className="text-right">Price</TableHead>
              <TableHead className="text-right">Volume</TableHead>
              <TableHead className="text-right">Commission</TableHead>
              <TableHead className="text-right">Proceeds</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">PnL</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {trades.map((trade, index) => (
              <TableRow key={index}>
                <TableCell className="font-mono text-sm">{trade.timestamp}</TableCell>
                <TableCell className="text-right font-mono">{trade.opening_nav.toFixed(2)}</TableCell>
                <TableCell className="text-right font-mono">{trade.closing_nav.toFixed(2)}</TableCell>
                <TableCell className="font-medium">{trade.contract}</TableCell>
                <TableCell className="text-right font-mono">{trade.price.toFixed(2)}</TableCell>
                <TableCell className="text-right">{trade.volume}</TableCell>
                <TableCell className="text-right font-mono text-red-600">{trade.commission.toFixed(2)}</TableCell>
                <TableCell className="text-right font-mono">{trade.proceeds.toFixed(2)}</TableCell>
                <TableCell>
                  <span className={`text-xs font-medium px-2 py-1 rounded ${
                    trade.status === 'EXPIRED' ? 'bg-gray-100 text-gray-700' :
                    trade.status === 'CLOSED' ? 'bg-blue-100 text-blue-700' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>
                    {trade.status}
                  </span>
                </TableCell>
                <TableCell className={`text-right font-mono font-medium ${
                  trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Summary from IBKR */}
      <div className="mt-6 p-4 bg-muted rounded-lg">
        <h4 className="font-semibold mb-2">IBKR Statement Totals (HKD)</h4>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Total Proceeds:</span>
            <span className="ml-2 font-mono font-medium">706.50</span>
          </div>
          <div>
            <span className="text-muted-foreground">Total Commissions:</span>
            <span className="ml-2 font-mono font-medium text-red-600">101.29</span>
          </div>
          <div>
            <span className="text-muted-foreground">Total Realized P&L:</span>
            <span className="ml-2 font-mono font-medium text-green-600">486.44</span>
          </div>
        </div>
        <div className="mt-2 text-xs text-muted-foreground">
          Exchange Rate: 7.85 HKD/USD (IBKR Statement Average)
        </div>
      </div>

      {trades.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          No trading data available for the selected period.
        </div>
      )}
    </div>
  );
};