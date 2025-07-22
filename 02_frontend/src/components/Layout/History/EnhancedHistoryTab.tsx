import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Download, ArrowUp, ArrowDown, DollarSign, TrendingUp } from 'lucide-react';
import { format } from 'date-fns';

interface Transaction {
  id: string;
  date: string;
  time: string;
  type: 'trade' | 'withdrawal' | 'deposit';
  description: string;
  amount: number;
  balance_after?: number;
  status: string;
  details?: any;
}

interface DailySummary {
  date: string;
  opening_balance: number;
  closing_balance: number;
  trades_pnl: number;
  withdrawals: number;
  deposits: number;
  net_change: number;
  is_reconciled: boolean;
}

export const EnhancedHistoryTab: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [dailySummaries, setDailySummaries] = useState<DailySummary[]>([]);
  const [filterType, setFilterType] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTransactionHistory();
  }, []);

  const fetchTransactionHistory = async () => {
    try {
      // Fetch trades
      const tradesResponse = await fetch('/api/trades/history?days=30');
      const trades = await tradesResponse.json();

      // Fetch cash movements
      const cashResponse = await fetch('/api/portfolio/withdrawals?days=30');
      const cashMovements = await cashResponse.json();

      // Fetch NAV history for balances
      const navResponse = await fetch('/api/portfolio/nav/history?days=30');
      const navHistory = await navResponse.json();

      // Combine and sort all transactions
      const allTransactions: Transaction[] = [
        // Convert trades to transaction format
        ...trades.map((trade: any) => ({
          id: trade.trade_id,
          date: format(new Date(trade.entry_time), 'yyyy-MM-dd'),
          time: format(new Date(trade.entry_time), 'HH:mm:ss'),
          type: 'trade' as const,
          description: `${trade.symbol} ${trade.strike} ${trade.option_type} - ${trade.quantity} contracts`,
          amount: trade.realized_pnl || 0,
          status: trade.status,
          details: trade
        })),
        // Convert cash movements to transaction format
        ...cashMovements.map((movement: any) => ({
          id: movement.movement_id,
          date: format(new Date(movement.movement_date), 'yyyy-MM-dd'),
          time: '00:00:00',
          type: movement.movement_type.toLowerCase() as 'withdrawal' | 'deposit',
          description: movement.description || `${movement.movement_type} - ${movement.destination_details || ''}`,
          amount: movement.movement_type === 'WITHDRAWAL' ? -Math.abs(movement.amount) : movement.amount,
          status: movement.status,
          details: movement
        }))
      ];

      // Sort by date and time descending
      allTransactions.sort((a, b) => {
        const dateA = new Date(`${a.date} ${a.time}`);
        const dateB = new Date(`${b.date} ${b.time}`);
        return dateB.getTime() - dateA.getTime();
      });

      // Calculate daily summaries
      const summaries = calculateDailySummaries(allTransactions, navHistory);

      setTransactions(allTransactions);
      setDailySummaries(summaries);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching transaction history:', error);
      setLoading(false);
    }
  };

  const calculateDailySummaries = (transactions: Transaction[], navHistory: any[]): DailySummary[] => {
    const summaryMap = new Map<string, DailySummary>();

    // Initialize with NAV data
    navHistory.forEach(nav => {
      summaryMap.set(nav.snapshot_date, {
        date: nav.snapshot_date,
        opening_balance: nav.opening_nav,
        closing_balance: nav.closing_nav || nav.opening_nav,
        trades_pnl: nav.trading_pnl || 0,
        withdrawals: 0,
        deposits: 0,
        net_change: (nav.closing_nav || nav.opening_nav) - nav.opening_nav,
        is_reconciled: nav.is_reconciled
      });
    });

    // Add transaction data
    transactions.forEach(tx => {
      const summary = summaryMap.get(tx.date) || {
        date: tx.date,
        opening_balance: 0,
        closing_balance: 0,
        trades_pnl: 0,
        withdrawals: 0,
        deposits: 0,
        net_change: 0,
        is_reconciled: false
      };

      if (tx.type === 'trade' && tx.status === 'closed') {
        summary.trades_pnl += tx.amount;
      } else if (tx.type === 'withdrawal') {
        summary.withdrawals += Math.abs(tx.amount);
      } else if (tx.type === 'deposit') {
        summary.deposits += tx.amount;
      }

      summaryMap.set(tx.date, summary);
    });

    return Array.from(summaryMap.values()).sort((a, b) => 
      new Date(b.date).getTime() - new Date(a.date).getTime()
    );
  };

  // Filter transactions
  const filteredTransactions = transactions.filter(tx => {
    const matchesType = filterType === 'all' || tx.type === filterType;
    const matchesSearch = tx.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDate = !selectedDate || tx.date === selectedDate;
    return matchesType && matchesSearch && matchesDate;
  });

  const handleExport = () => {
    const csv = [
      ['Date', 'Time', 'Type', 'Description', 'Amount', 'Status'],
      ...filteredTransactions.map(tx => [
        tx.date,
        tx.time,
        tx.type,
        tx.description,
        tx.amount.toFixed(2),
        tx.status
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transaction_history_${format(new Date(), 'yyyy-MM-dd')}.csv`;
    a.click();
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'trade': return 'bg-blue-100 text-blue-800';
      case 'withdrawal': return 'bg-red-100 text-red-800';
      case 'deposit': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Daily Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {dailySummaries.slice(0, 4).map(summary => (
          <Card key={summary.date} className="cursor-pointer hover:shadow-lg transition-shadow"
                onClick={() => setSelectedDate(summary.date === selectedDate ? null : summary.date)}>
            <CardContent className="p-4">
              <div className="flex justify-between items-start mb-2">
                <p className="text-sm text-gray-600">
                  {format(new Date(summary.date), 'MMM dd, yyyy')}
                </p>
                {summary.is_reconciled && (
                  <Badge variant="outline" className="text-green-600">Reconciled</Badge>
                )}
              </div>
              <p className="text-xl font-bold mb-1">${summary.closing_balance.toLocaleString()}</p>
              <div className={`flex items-center text-sm ${summary.net_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {summary.net_change >= 0 ? <ArrowUp className="w-3 h-3 mr-1" /> : <ArrowDown className="w-3 h-3 mr-1" />}
                ${Math.abs(summary.net_change).toFixed(2)}
              </div>
              <div className="mt-2 space-y-1 text-xs text-gray-600">
                {summary.trades_pnl !== 0 && (
                  <p>Trading: ${summary.trades_pnl.toFixed(2)}</p>
                )}
                {summary.withdrawals > 0 && (
                  <p>Withdrawals: -${summary.withdrawals.toFixed(2)}</p>
                )}
                {summary.deposits > 0 && (
                  <p>Deposits: +${summary.deposits.toFixed(2)}</p>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <Select value={filterType} onValueChange={setFilterType}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Transactions</SelectItem>
            <SelectItem value="trade">Trades Only</SelectItem>
            <SelectItem value="withdrawal">Withdrawals Only</SelectItem>
            <SelectItem value="deposit">Deposits Only</SelectItem>
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

        <Button variant="outline" onClick={handleExport}>
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Selected Date Summary */}
      {selectedDate && (
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-4">
            <p className="text-sm font-medium text-blue-800">
              Showing transactions for {format(new Date(selectedDate), 'MMMM dd, yyyy')}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Transaction History Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date & Time</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTransactions.map((tx) => (
                <TableRow key={tx.id} className="hover:bg-gray-50">
                  <TableCell>
                    <div>
                      <p className="font-medium">{format(new Date(tx.date), 'MMM dd, yyyy')}</p>
                      <p className="text-sm text-gray-600">{tx.time}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge className={getTypeColor(tx.type)} variant="secondary">
                      {tx.type.charAt(0).toUpperCase() + tx.type.slice(1)}
                    </Badge>
                  </TableCell>
                  <TableCell>{tx.description}</TableCell>
                  <TableCell className={`text-right font-medium ${tx.amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {tx.amount >= 0 ? '+' : ''}${Math.abs(tx.amount).toFixed(2)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={tx.status === 'Completed' || tx.status === 'closed' ? 'default' : 'secondary'}>
                      {tx.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};