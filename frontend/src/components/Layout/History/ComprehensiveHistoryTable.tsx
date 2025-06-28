import React, { useState, useEffect } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Search, Download, ArrowUp, ArrowDown } from 'lucide-react';
import { format } from 'date-fns';

interface TransactionRow {
  id: string;
  datetime: string;
  type: 'trade' | 'deposit' | 'withdrawal' | 'fee';
  description: string;
  symbol?: string;
  strike?: number;
  optionType?: string;
  quantity?: number;
  entryPrice?: number;
  exitPrice?: number;
  pnl?: number;
  commission?: number;
  cashMovement?: number;
  openingBalance: number;
  closingBalance: number;
  netChange: number;
  status: string;
}

export const ComprehensiveHistoryTable: React.FC = () => {
  const [transactions, setTransactions] = useState<TransactionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [dateRange, setDateRange] = useState('30d');
  const [totals, setTotals] = useState({
    totalPnl: 0,
    totalDeposits: 0,
    totalWithdrawals: 0,
    totalCommissions: 0,
    netChange: 0
  });

  useEffect(() => {
    fetchTransactionData();
  }, [dateRange]);

  const fetchTransactionData = async () => {
    try {
      setLoading(true);
      
      // Fetch all data in parallel
      const [tradesRes, cashRes, navRes] = await Promise.all([
        fetch(`/api/trades/history?limit=100`),
        fetch(`/api/portfolio/withdrawals?days=${dateRange === 'all' ? 365 : parseInt(dateRange)}`),
        fetch(`/api/portfolio/nav/history?days=${dateRange === 'all' ? 365 : parseInt(dateRange)}`)
      ]);

      const tradesData = await tradesRes.json();
      const cashData = await cashRes.json();
      const navData = await navRes.json();
      
      console.log('Trade data:', tradesData);
      console.log('Cash movements:', cashData);
      console.log('NAV data:', navData);

      // Process and combine all transactions
      const processedTransactions = processTransactions(tradesData, cashData, navData);
      setTransactions(processedTransactions);
      calculateTotals(processedTransactions);
      
    } catch (error) {
      console.error('Error fetching transaction data:', error);
    } finally {
      setLoading(false);
    }
  };

  const processTransactions = (trades: any, cashMovements: any[], navSnapshots: any[]): TransactionRow[] => {
    const allTransactions: TransactionRow[] = [];
    
    // Create NAV lookup by date
    const navByDate = navSnapshots.reduce((acc: any, nav: any) => {
      acc[nav.snapshot_date] = nav;
      return acc;
    }, {});
    
    // Get the earliest NAV snapshot to determine starting balance
    const sortedNavs = [...navSnapshots].sort((a, b) => 
      new Date(a.snapshot_date).getTime() - new Date(b.snapshot_date).getTime()
    );
    const startingNav = sortedNavs.length > 0 ? parseFloat(sortedNavs[0].opening_nav) : 10791.86;
    let runningBalance = startingNav;

    // Get trades from the response (handle both object with trades array and direct array)
    const tradesList = Array.isArray(trades) ? trades : (trades.trades || []);

    // Combine all transactions (trades and cash movements) and sort by date
    const allEvents: any[] = [];
    
    // Add trades
    tradesList.forEach((trade: any) => {
      allEvents.push({
        ...trade,
        eventType: 'trade',
        eventTime: trade.entry_time || `${trade.trade_date}T09:30:00`
      });
    });
    
    // Add cash movements
    cashMovements.forEach((movement: any) => {
      allEvents.push({
        ...movement,
        eventType: 'cash',
        eventTime: `${movement.movement_date}T00:00:00`
      });
    });
    
    // Sort all events by time
    allEvents.sort((a, b) => new Date(a.eventTime).getTime() - new Date(b.eventTime).getTime());
    
    // Process events in chronological order to calculate running balances
    allEvents.forEach((event: any, index: number) => {
      const eventDate = event.eventTime.split('T')[0];
      const navSnapshot = navByDate[eventDate];
      
      // Use actual NAV data from database for this date
      let openingBalance = runningBalance;
      let closingBalance = runningBalance;
      
      if (navSnapshot) {
        openingBalance = parseFloat(navSnapshot.opening_nav);
        closingBalance = parseFloat(navSnapshot.closing_nav) || openingBalance;
        runningBalance = closingBalance; // Update running balance to match NAV data
      }
      
      if (event.eventType === 'trade') {
        // Format description based on trade data
        const expiry = event.expiration ? new Date(event.expiration).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
        const description = `${event.symbol || 'SPY'} ${expiry} ${event.strike_price || event.strike}${event.option_type ? event.option_type.charAt(0) : ''}`;
        
        const pnl = parseFloat(event.realized_pnl) || parseFloat(event.pnl) || 0;
        const commission = (parseFloat(event.entry_commission) || 0) + (parseFloat(event.exit_commission) || 0);
        const netChange = pnl - commission;
        
        // If no NAV snapshot, calculate the closing balance
        if (!navSnapshot) {
          closingBalance = openingBalance + netChange;
          runningBalance = closingBalance;
        }
        
        allTransactions.push({
          id: event.trade_id || event.id,
          datetime: event.eventTime,
          type: 'trade',
          description: description,
          symbol: event.symbol || 'SPY',
          strike: event.strike_price || event.strike,
          optionType: event.option_type,
          quantity: event.quantity || event.contracts,
          entryPrice: parseFloat(event.entry_price) || 0,
          exitPrice: parseFloat(event.exit_price) || 0,
          pnl: pnl,
          commission: commission,
          openingBalance: openingBalance,
          closingBalance: closingBalance,
          netChange: netChange,
          status: event.status || 'closed'
        });
      } else if (event.eventType === 'cash') {
        const amount = parseFloat(event.amount);
        const cashMovement = event.movement_type === 'DEPOSIT' ? amount : -amount;
        
        // If no NAV snapshot, calculate the closing balance
        if (!navSnapshot) {
          closingBalance = openingBalance + cashMovement;
          runningBalance = closingBalance;
        }
        
        allTransactions.push({
          id: event.movement_id,
          datetime: event.eventTime,
          type: event.movement_type.toLowerCase() as 'deposit' | 'withdrawal',
          description: event.description || `${event.movement_type}`,
          cashMovement: cashMovement,
          openingBalance: openingBalance,
          closingBalance: closingBalance,
          netChange: cashMovement,
          status: event.status || 'completed'
        });
      }
    });

    // Sort by datetime descending (most recent first for display)
    allTransactions.sort((a, b) => new Date(b.datetime).getTime() - new Date(a.datetime).getTime());

    return allTransactions;
  };

  const calculateTotals = (transactions: TransactionRow[]) => {
    const totals = transactions.reduce((acc, trans) => {
      acc.totalPnl += trans.pnl || 0;
      acc.totalCommissions += trans.commission || 0;
      if (trans.type === 'deposit') acc.totalDeposits += trans.cashMovement || 0;
      if (trans.type === 'withdrawal') acc.totalWithdrawals += Math.abs(trans.cashMovement || 0);
      return acc;
    }, {
      totalPnl: 0,
      totalDeposits: 0,
      totalWithdrawals: 0,
      totalCommissions: 0,
      netChange: 0
    });

    // Calculate net change
    totals.netChange = totals.totalPnl + totals.totalDeposits - totals.totalWithdrawals - totals.totalCommissions;
    setTotals(totals);
  };

  const filteredTransactions = transactions.filter(trans => {
    const searchLower = searchTerm.toLowerCase();
    return trans.description.toLowerCase().includes(searchLower) ||
           trans.symbol?.toLowerCase().includes(searchLower) ||
           trans.type.includes(searchLower);
  });

  const formatCurrency = (value: number | undefined) => {
    if (value === undefined) return '-';
    return value >= 0 ? `+$${value.toFixed(2)}` : `-$${Math.abs(value).toFixed(2)}`;
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'trade': return 'default';
      case 'deposit': return 'green';
      case 'withdrawal': return 'red';
      case 'fee': return 'yellow';
      default: return 'secondary';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'closed':
      case 'completed': return 'green';
      case 'open': return 'blue';
      case 'pending': return 'yellow';
      default: return 'secondary';
    }
  };

  const exportToCSV = () => {
    const headers = [
      'Date/Time', 'Type', 'Description', 'Quantity', 'Entry Price', 'Exit Price',
      'P&L', 'Commission', 'Cash In/Out', 'Opening Balance', 'Closing Balance', 
      'Net Change', 'Status'
    ];

    const rows = filteredTransactions.map(trans => [
      format(new Date(trans.datetime), 'yyyy-MM-dd HH:mm:ss'),
      trans.type,
      trans.description,
      trans.quantity || '',
      trans.entryPrice || '',
      trans.exitPrice || '',
      trans.pnl || '',
      trans.commission || '',
      trans.cashMovement || '',
      trans.openingBalance,
      trans.closingBalance,
      trans.netChange,
      trans.status
    ]);

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transaction_history_${format(new Date(), 'yyyy-MM-dd')}.csv`;
    a.click();
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96">Loading comprehensive history...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4 flex-1">
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Date range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
              <SelectItem value="all">All time</SelectItem>
            </SelectContent>
          </Select>

          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search transactions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        <Button variant="outline" onClick={exportToCSV}>
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-5 gap-4 mb-4">
        <div className="bg-gray-50 p-3 rounded-lg">
          <p className="text-sm text-gray-600">Total P&L</p>
          <p className={`text-lg font-bold ${totals.totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(totals.totalPnl)}
          </p>
        </div>
        <div className="bg-gray-50 p-3 rounded-lg">
          <p className="text-sm text-gray-600">Total Deposits</p>
          <p className="text-lg font-bold text-green-600">+${totals.totalDeposits.toFixed(2)}</p>
        </div>
        <div className="bg-gray-50 p-3 rounded-lg">
          <p className="text-sm text-gray-600">Total Withdrawals</p>
          <p className="text-lg font-bold text-red-600">-${totals.totalWithdrawals.toFixed(2)}</p>
        </div>
        <div className="bg-gray-50 p-3 rounded-lg">
          <p className="text-sm text-gray-600">Total Commissions</p>
          <p className="text-lg font-bold text-yellow-600">-${totals.totalCommissions.toFixed(2)}</p>
        </div>
        <div className="bg-gray-50 p-3 rounded-lg">
          <p className="text-sm text-gray-600">Net Change</p>
          <p className={`text-lg font-bold ${totals.netChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(totals.netChange)}
          </p>
        </div>
      </div>

      {/* Transaction Table */}
      <div className="max-h-[600px] overflow-y-auto overflow-x-auto border rounded-lg">
        <Table className="text-sm">
          <TableHeader className="sticky top-0 bg-white z-10">
            <TableRow>
              <TableHead className="whitespace-nowrap py-2 px-3">Date/Time</TableHead>
              <TableHead className="py-2 px-2">Type</TableHead>
              <TableHead className="py-2 px-3">Description</TableHead>
              <TableHead className="text-right py-2 px-2">Qty</TableHead>
              <TableHead className="text-right py-2 px-2">Entry</TableHead>
              <TableHead className="text-right py-2 px-2">Exit</TableHead>
              <TableHead className="text-right py-2 px-2">P&L</TableHead>
              <TableHead className="text-right py-2 px-2">Comm</TableHead>
              <TableHead className="text-right py-2 px-2">Cash</TableHead>
              <TableHead className="text-right py-2 px-2">Opening</TableHead>
              <TableHead className="text-right py-2 px-2">Closing</TableHead>
              <TableHead className="text-right py-2 px-2">Change</TableHead>
              <TableHead className="py-2 px-2">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredTransactions.map((trans) => (
              <TableRow key={trans.id} className="hover:bg-gray-50">
                <TableCell className="whitespace-nowrap py-2 px-3">
                  {format(new Date(trans.datetime), 'MM/dd HH:mm')}
                </TableCell>
                <TableCell className="py-2 px-2">
                  <Badge variant={getTypeColor(trans.type) as any} className="text-xs">
                    {trans.type.toUpperCase()}
                  </Badge>
                </TableCell>
                <TableCell className="py-2 px-3 max-w-[200px]">
                  <div className="truncate" title={trans.description}>
                    {trans.description}
                  </div>
                </TableCell>
                <TableCell className="text-right py-2 px-2">{trans.quantity || '-'}</TableCell>
                <TableCell className="text-right py-2 px-2">
                  {trans.entryPrice ? trans.entryPrice.toFixed(2) : '-'}
                </TableCell>
                <TableCell className="text-right py-2 px-2">
                  {trans.exitPrice ? trans.exitPrice.toFixed(2) : '-'}
                </TableCell>
                <TableCell className={`text-right py-2 px-2 font-medium ${trans.pnl && trans.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {trans.pnl !== undefined ? (trans.pnl >= 0 ? '+' : '') + trans.pnl.toFixed(2) : '-'}
                </TableCell>
                <TableCell className="text-right py-2 px-2 text-yellow-600">
                  {trans.commission ? trans.commission.toFixed(2) : '-'}
                </TableCell>
                <TableCell className={`text-right py-2 px-2 font-medium ${trans.cashMovement && trans.cashMovement >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {trans.cashMovement !== undefined ? (trans.cashMovement >= 0 ? '+' : '') + trans.cashMovement.toFixed(0) : '-'}
                </TableCell>
                <TableCell className="text-right py-2 px-2">
                  {Math.round(trans.openingBalance).toLocaleString('en-US')}
                </TableCell>
                <TableCell className="text-right py-2 px-2 font-medium">
                  {Math.round(trans.closingBalance).toLocaleString('en-US')}
                </TableCell>
                <TableCell className={`text-right py-2 px-2 font-medium ${trans.netChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {trans.netChange >= 0 ? '+' : ''}{trans.netChange.toFixed(2)}
                </TableCell>
                <TableCell className="py-2 px-2">
                  <Badge variant={getStatusColor(trans.status) as any} className="text-xs">
                    {trans.status.toUpperCase()}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};