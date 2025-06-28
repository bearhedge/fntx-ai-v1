import React, { useState, useEffect } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Search, Download, ArrowUp, ArrowDown } from 'lucide-react';
import { format } from 'date-fns';

interface NAVSnapshot {
  snapshot_date: string;
  opening_nav: number;
  closing_nav: number;
  source: string;
}

interface Trade {
  trade_id: string;
  entry_time: string;
  symbol: string;
  strike_price: number;
  option_type: string;
  quantity: number;
  entry_price: number;
  exit_price: number;
  realized_pnl: number;
  entry_commission: number;
  exit_commission: number;
  status: string;
  expiration: string;
}

interface CashMovement {
  movement_id: string;
  movement_date: string;
  movement_type: string;
  amount: number;
  description: string;
  status: string;
}

interface HistoryRow {
  date: string;
  opening_nav: number;
  closing_nav: number;
  daily_change: number;
  trades: Trade[];
  cash_movements: CashMovement[];
}

export const FixedHistoryTable: React.FC = () => {
  const [historyRows, setHistoryRows] = useState<HistoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [totals, setTotals] = useState({
    totalPnl: 0,
    totalDeposits: 0,
    totalWithdrawals: 0,
    totalCommissions: 0,
    netChange: 0
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch all data
      const [navRes, tradesRes, cashRes] = await Promise.all([
        fetch('/api/portfolio/nav/history?days=30'),
        fetch('/api/trades/history?limit=100'),
        fetch('/api/portfolio/withdrawals?days=30')
      ]);

      const navSnapshots: NAVSnapshot[] = await navRes.json();
      const tradesData = await tradesRes.json();
      const cashMovements: CashMovement[] = await cashRes.json();

      // Get trades array from response
      const trades: Trade[] = Array.isArray(tradesData) ? tradesData : (tradesData.trades || []);

      console.log('NAV Snapshots:', navSnapshots);
      console.log('Trades:', trades);
      console.log('Cash Movements:', cashMovements);

      // Process data - only show dates where we have actual NAV data
      const processedRows = processHistoryData(navSnapshots, trades, cashMovements);
      setHistoryRows(processedRows);
      calculateTotals(processedRows);
      
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const processHistoryData = (navSnapshots: NAVSnapshot[], trades: Trade[], cashMovements: CashMovement[]): HistoryRow[] => {
    // Only process dates where we have actual NAV snapshots
    return navSnapshots.map(nav => {
      const navDate = nav.snapshot_date;
      
      // Find trades for this date
      const dayTrades = trades.filter(trade => {
        const tradeDate = trade.entry_time.split('T')[0];
        return tradeDate === navDate;
      });

      // Find cash movements for this date
      const dayCashMovements = cashMovements.filter(movement => {
        return movement.movement_date === navDate;
      });

      const dailyChange = nav.closing_nav - nav.opening_nav;

      return {
        date: navDate,
        opening_nav: nav.opening_nav,
        closing_nav: nav.closing_nav,
        daily_change: dailyChange,
        trades: dayTrades,
        cash_movements: dayCashMovements
      };
    }).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  };

  const calculateTotals = (rows: HistoryRow[]) => {
    const totals = rows.reduce((acc, row) => {
      // Calculate totals from trades
      row.trades.forEach(trade => {
        acc.totalPnl += trade.realized_pnl || 0;
        acc.totalCommissions += (trade.entry_commission || 0) + (trade.exit_commission || 0);
      });

      // Calculate totals from cash movements
      row.cash_movements.forEach(movement => {
        if (movement.movement_type === 'DEPOSIT') {
          acc.totalDeposits += movement.amount;
        } else if (movement.movement_type === 'WITHDRAWAL') {
          acc.totalWithdrawals += Math.abs(movement.amount);
        }
      });

      return acc;
    }, {
      totalPnl: 0,
      totalDeposits: 0,
      totalWithdrawals: 0,
      totalCommissions: 0,
      netChange: 0
    });

    totals.netChange = totals.totalPnl + totals.totalDeposits - totals.totalWithdrawals - totals.totalCommissions;
    setTotals(totals);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'MM/dd');
  };

  const formatDateTime = (dateTimeString: string) => {
    return format(new Date(dateTimeString), 'MM/dd HH:mm');
  };

  if (loading) {
    return <div className="p-4">Loading history...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-card p-4 rounded-lg border">
          <div className="text-sm text-muted-foreground">Total P&L</div>
          <div className={`text-lg font-semibold ${totals.totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(totals.totalPnl)}
          </div>
        </div>
        <div className="bg-card p-4 rounded-lg border">
          <div className="text-sm text-muted-foreground">Total Deposits</div>
          <div className="text-lg font-semibold text-green-600">
            +{formatCurrency(totals.totalDeposits)}
          </div>
        </div>
        <div className="bg-card p-4 rounded-lg border">
          <div className="text-sm text-muted-foreground">Total Withdrawals</div>
          <div className="text-lg font-semibold text-red-600">
            -{formatCurrency(totals.totalWithdrawals)}
          </div>
        </div>
        <div className="bg-card p-4 rounded-lg border">
          <div className="text-sm text-muted-foreground">Total Commissions</div>
          <div className="text-lg font-semibold text-red-600">
            -{formatCurrency(totals.totalCommissions)}
          </div>
        </div>
        <div className="bg-card p-4 rounded-lg border">
          <div className="text-sm text-muted-foreground">Net Change</div>
          <div className={`text-lg font-semibold ${totals.netChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(totals.netChange)}
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex gap-4 items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search transactions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* History Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Activity</TableHead>
              <TableHead>Opening NAV</TableHead>
              <TableHead>Closing NAV</TableHead>
              <TableHead>Daily Change</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {historyRows.map((row) => (
              <React.Fragment key={row.date}>
                {/* Main NAV row */}
                <TableRow className="border-b">
                  <TableCell className="font-medium">
                    {formatDate(row.date)}
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      {row.trades.length > 0 && (
                        <div className="text-sm text-muted-foreground">
                          {row.trades.length} trade{row.trades.length > 1 ? 's' : ''}
                        </div>
                      )}
                      {row.cash_movements.length > 0 && (
                        <div className="text-sm text-muted-foreground">
                          {row.cash_movements.length} cash movement{row.cash_movements.length > 1 ? 's' : ''}
                        </div>
                      )}
                      {row.trades.length === 0 && row.cash_movements.length === 0 && (
                        <div className="text-sm text-muted-foreground">No activity</div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono">
                    {formatCurrency(row.opening_nav)}
                  </TableCell>
                  <TableCell className="font-mono">
                    {formatCurrency(row.closing_nav)}
                  </TableCell>
                  <TableCell className={`font-mono ${row.daily_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {row.daily_change >= 0 ? '+' : ''}{formatCurrency(row.daily_change)}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">Complete</Badge>
                  </TableCell>
                </TableRow>

                {/* Trade detail rows */}
                {row.trades.map((trade) => (
                  <TableRow key={trade.trade_id} className="bg-muted/50">
                    <TableCell className="pl-8 text-sm text-muted-foreground">
                      {formatDateTime(trade.entry_time)}
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <div className="font-medium">
                          {trade.symbol} {format(new Date(trade.expiration), 'MMM dd')} {trade.strike_price}{trade.option_type?.charAt(0)}
                        </div>
                        <div className="text-muted-foreground">
                          {trade.quantity} × ${trade.entry_price} → ${trade.exit_price || 'Open'}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell></TableCell>
                    <TableCell></TableCell>
                    <TableCell className={`font-mono text-sm ${(trade.realized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      P&L: {formatCurrency(trade.realized_pnl || 0)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={trade.status === 'closed' ? 'secondary' : 'default'}>
                        {trade.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}

                {/* Cash movement detail rows */}
                {row.cash_movements.map((movement) => (
                  <TableRow key={movement.movement_id} className="bg-muted/50">
                    <TableCell className="pl-8 text-sm text-muted-foreground">
                      {formatDate(movement.movement_date)}
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <div className="font-medium">{movement.description}</div>
                        <div className="text-muted-foreground">{movement.movement_type}</div>
                      </div>
                    </TableCell>
                    <TableCell></TableCell>
                    <TableCell></TableCell>
                    <TableCell className={`font-mono text-sm ${movement.movement_type === 'DEPOSIT' ? 'text-green-600' : 'text-red-600'}`}>
                      {movement.movement_type === 'DEPOSIT' ? '+' : '-'}{formatCurrency(Math.abs(movement.amount))}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{movement.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </div>

      {historyRows.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          No NAV history available. Daily NAV data will appear here as it's imported from IBKR.
        </div>
      )}
    </div>
  );
};