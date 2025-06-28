import React, { useState, useEffect } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, Download } from 'lucide-react';
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
  movement_time?: string;
  movement_type: string;
  amount: number;
  description: string;
  status: string;
}

interface DayEvent {
  time: string;
  type: 'opening' | 'trade' | 'cash' | 'summary' | 'closing';
  description: string;
  entry_price?: number;
  exit_price?: number;
  pnl?: number;
  commission?: number;
  cash_movement?: number;
  running_nav: number;
  trade?: Trade;
  cash?: CashMovement;
}

interface DayData {
  date: string;
  opening_nav: number;
  closing_nav: number;
  events: DayEvent[];
  total_pnl: number;
  total_commission: number;
  total_deposits: number;
  total_withdrawals: number;
  net_change: number;
  isExpanded: boolean;
}

export const ComprehensiveNAVTable: React.FC = () => {
  const [daysData, setDaysData] = useState<DayData[]>([]);
  const [loading, setLoading] = useState(true);

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

      // Process data into comprehensive day views
      const processedDays = processComprehensiveData(navSnapshots, trades, cashMovements);
      setDaysData(processedDays);
      
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const processComprehensiveData = (
    navSnapshots: NAVSnapshot[], 
    trades: Trade[], 
    cashMovements: CashMovement[]
  ): DayData[] => {
    return navSnapshots.map(nav => {
      const dayDate = nav.snapshot_date;
      const events: DayEvent[] = [];
      let runningNav = nav.opening_nav;
      
      // Add opening balance event
      events.push({
        time: '00:00',
        type: 'opening',
        description: 'Opening Balance',
        running_nav: runningNav
      });

      // Get all trades for this day
      const dayTrades = trades
        .filter(trade => trade.entry_time.split('T')[0] === dayDate)
        .sort((a, b) => new Date(a.entry_time).getTime() - new Date(b.entry_time).getTime());

      // Get all cash movements for this day
      const dayCashMovements = cashMovements
        .filter(movement => movement.movement_date === dayDate)
        .sort((a, b) => {
          const timeA = movement.movement_time || '00:00';
          const timeB = b.movement_time || '00:00';
          return timeA.localeCompare(timeB);
        });

      // Process trades
      let totalPnl = 0;
      let totalCommission = 0;

      dayTrades.forEach(trade => {
        const time = format(new Date(trade.entry_time), 'HH:mm');
        const pnl = trade.realized_pnl || 0;
        const commission = (trade.entry_commission || 0) + (trade.exit_commission || 0);
        const netImpact = pnl - commission;
        
        runningNav += netImpact;
        totalPnl += pnl;
        totalCommission += commission;

        events.push({
          time,
          type: 'trade',
          description: `${trade.symbol} ${format(new Date(trade.expiration), 'MMM d')} ${trade.strike_price}${trade.option_type?.charAt(0) || ''}`,
          entry_price: trade.entry_price,
          exit_price: trade.exit_price,
          pnl: pnl,
          commission: commission,
          running_nav: runningNav,
          trade: trade
        });
      });

      // Process cash movements
      let totalDeposits = 0;
      let totalWithdrawals = 0;

      dayCashMovements.forEach(movement => {
        const time = movement.movement_time || '12:00';
        const amount = movement.amount;
        
        if (movement.movement_type === 'DEPOSIT') {
          runningNav += amount;
          totalDeposits += amount;
        } else if (movement.movement_type === 'WITHDRAWAL') {
          runningNav -= Math.abs(amount);
          totalWithdrawals += Math.abs(amount);
        }

        events.push({
          time,
          type: 'cash',
          description: movement.description || movement.movement_type,
          cash_movement: movement.movement_type === 'DEPOSIT' ? amount : -Math.abs(amount),
          running_nav: runningNav,
          cash: movement
        });
      });

      // Sort all events by time
      events.sort((a, b) => {
        if (a.type === 'opening') return -1;
        if (b.type === 'opening') return 1;
        if (a.type === 'closing') return 1;
        if (b.type === 'closing') return -1;
        return a.time.localeCompare(b.time);
      });

      // Add daily summary
      if (dayTrades.length > 0 || dayCashMovements.length > 0) {
        events.push({
          time: '',
          type: 'summary',
          description: 'Daily Summary',
          pnl: totalPnl,
          commission: totalCommission,
          cash_movement: totalDeposits - totalWithdrawals,
          running_nav: runningNav
        });
      }

      // Add closing balance event
      events.push({
        time: '23:59',
        type: 'closing',
        description: 'Closing Balance',
        running_nav: nav.closing_nav
      });

      const netChange = nav.closing_nav - nav.opening_nav;

      return {
        date: dayDate,
        opening_nav: nav.opening_nav,
        closing_nav: nav.closing_nav,
        events,
        total_pnl: totalPnl,
        total_commission: totalCommission,
        total_deposits: totalDeposits,
        total_withdrawals: totalWithdrawals,
        net_change: netChange,
        isExpanded: totalPnl !== 0 || totalDeposits !== 0 || totalWithdrawals !== 0 // Auto-expand days with activity
      };
    }).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  };

  const toggleDay = (date: string) => {
    setDaysData(prev => prev.map(day => 
      day.date === date ? { ...day, isExpanded: !day.isExpanded } : day
    ));
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'MMMM d, yyyy');
  };

  if (loading) {
    return <div className="p-4">Loading comprehensive history...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Comprehensive NAV Reconciliation</h3>
        <Button variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-md border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="w-16"></TableHead>
              <TableHead className="w-20">Time</TableHead>
              <TableHead>Description</TableHead>
              <TableHead className="text-right">Entry</TableHead>
              <TableHead className="text-right">Exit</TableHead>
              <TableHead className="text-right">P&L</TableHead>
              <TableHead className="text-right">Comm</TableHead>
              <TableHead className="text-right">Cash</TableHead>
              <TableHead className="text-right">Running NAV</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {daysData.map((day) => (
              <React.Fragment key={day.date}>
                {/* Day header row */}
                <TableRow 
                  className="bg-primary/5 hover:bg-primary/10 cursor-pointer border-t-2"
                  onClick={() => toggleDay(day.date)}
                >
                  <TableCell>
                    <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                      {day.isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </Button>
                  </TableCell>
                  <TableCell colSpan={7} className="font-semibold">
                    {formatDate(day.date)}
                  </TableCell>
                  <TableCell className="text-right font-semibold">
                    <span className={day.net_change >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {day.net_change >= 0 ? '+' : ''}{formatCurrency(day.net_change)}
                    </span>
                  </TableCell>
                </TableRow>

                {/* Day details */}
                {day.isExpanded && day.events.map((event, idx) => (
                  <TableRow 
                    key={`${day.date}-${idx}`}
                    className={
                      event.type === 'opening' || event.type === 'closing' 
                        ? 'bg-muted/30 font-medium' 
                        : event.type === 'summary'
                        ? 'bg-primary/5 border-t font-medium'
                        : ''
                    }
                  >
                    <TableCell></TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {event.time}
                    </TableCell>
                    <TableCell className={event.type === 'summary' ? 'italic' : ''}>
                      {event.description}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {event.entry_price ? `$${event.entry_price.toFixed(2)}` : ''}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {event.exit_price ? `$${event.exit_price.toFixed(2)}` : ''}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {event.pnl !== undefined && event.pnl !== 0 && (
                        <span className={event.pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {event.pnl >= 0 ? '+' : ''}{formatCurrency(event.pnl)}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {event.commission ? (
                        <span className="text-red-600">-{formatCurrency(event.commission)}</span>
                      ) : ''}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {event.cash_movement !== undefined && event.cash_movement !== 0 && (
                        <span className={event.cash_movement >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {event.cash_movement >= 0 ? '+' : ''}{formatCurrency(Math.abs(event.cash_movement))}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono font-medium">
                      {formatCurrency(event.running_nav)}
                    </TableCell>
                  </TableRow>
                ))}

                {/* Summary row if day is collapsed */}
                {!day.isExpanded && (
                  <TableRow className="text-sm text-muted-foreground">
                    <TableCell></TableCell>
                    <TableCell colSpan={7}>
                      {formatCurrency(day.opening_nav)} → {formatCurrency(day.closing_nav)}
                      {day.total_pnl > 0 && ` • P&L: +${formatCurrency(day.total_pnl)}`}
                      {day.total_deposits > 0 && ` • Deposits: +${formatCurrency(day.total_deposits)}`}
                    </TableCell>
                    <TableCell></TableCell>
                  </TableRow>
                )}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </div>

      {daysData.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          No NAV history available. Daily NAV data will appear here as it's imported from IBKR.
        </div>
      )}
    </div>
  );
};