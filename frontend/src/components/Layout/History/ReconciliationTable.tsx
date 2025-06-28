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
  trading_pnl?: number;
  source: string;
}

interface Trade {
  trade_id: string;
  entry_time: string;
  exit_time?: string;
  symbol: string;
  strike_price: number;
  option_type: string;
  quantity: number;
  entry_price: number;
  exit_price: number;
  exit_reason?: string;
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

interface DayData {
  date: string;
  opening_nav: number;
  closing_nav: number;
  nav_change: number;
  trades: Trade[];
  cash_movements: CashMovement[];
  
  // Reconciliation components
  realized_pnl: number;
  total_commissions: number;
  net_deposits: number;
  unexplained_change: number;
  
  isExpanded: boolean;
}

export const ReconciliationTable: React.FC = () => {
  const [daysData, setDaysData] = useState<DayData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch all data starting from June 20, 2025
      const [navRes, tradesRes, cashRes] = await Promise.all([
        fetch('/api/portfolio/nav/history?start_date=2025-06-20&days=30'),
        fetch('/api/trades/history?limit=100&start_date=2025-06-20'),
        fetch('/api/portfolio/withdrawals?start_date=2025-06-20&days=30')
      ]);

      const navSnapshots: NAVSnapshot[] = await navRes.json();
      const tradesData = await tradesRes.json();
      const cashMovements: CashMovement[] = await cashRes.json();

      // Get trades array from response
      const trades: Trade[] = Array.isArray(tradesData) ? tradesData : (tradesData.trades || []);

      console.log('NAV Snapshots:', navSnapshots);
      console.log('Trades:', trades);
      console.log('Cash Movements:', cashMovements);

      // Process data with proper reconciliation
      const processedDays = processReconciliationData(navSnapshots, trades, cashMovements);
      setDaysData(processedDays);
      
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const processReconciliationData = (
    navSnapshots: NAVSnapshot[], 
    trades: Trade[], 
    cashMovements: CashMovement[]
  ): DayData[] => {
    return navSnapshots.map(nav => {
      const dayDate = nav.snapshot_date;
      
      // Get all trades for this day
      const dayTrades = trades
        .filter(trade => trade.entry_time.split('T')[0] === dayDate)
        .sort((a, b) => new Date(a.entry_time).getTime() - new Date(b.entry_time).getTime());

      // Get all cash movements for this day
      const dayCashMovements = cashMovements
        .filter(movement => movement.movement_date === dayDate);

      // Calculate reconciliation components with correct P&L for short options
      let realized_pnl = 0;
      let total_commissions = 0;

      dayTrades.forEach(trade => {
        // Calculate correct P&L for short options
        let correct_pnl = 0;
        if (trade.exit_price !== null) {
          if (trade.quantity < 0) {
            // Short position: collected premium minus cost to close
            if (trade.exit_price === 0) {
              // Expired worthless - we keep the premium
              correct_pnl = (trade.entry_price * Math.abs(trade.quantity) * 100) 
                           - (trade.entry_commission || 0) 
                           - (trade.exit_commission || 0);
            } else {
              // Bought to close
              correct_pnl = ((trade.entry_price - trade.exit_price) * Math.abs(trade.quantity) * 100) 
                           - (trade.entry_commission || 0) 
                           - (trade.exit_commission || 0);
            }
          } else {
            // Long position: exit value minus entry cost
            correct_pnl = ((trade.exit_price - trade.entry_price) * trade.quantity * 100) 
                         - (trade.entry_commission || 0) 
                         - (trade.exit_commission || 0);
          }
        }
        
        realized_pnl += correct_pnl;
        total_commissions += (trade.entry_commission || 0) + (trade.exit_commission || 0);
      });

      // Calculate net deposits/withdrawals
      let net_deposits = 0;
      dayCashMovements.forEach(movement => {
        if (movement.movement_type === 'DEPOSIT') {
          net_deposits += movement.amount;
        } else if (movement.movement_type === 'WITHDRAWAL') {
          net_deposits -= Math.abs(movement.amount);
        }
      });

      // Calculate the expected vs actual change
      const nav_change = nav.closing_nav - nav.opening_nav;
      const expected_change = realized_pnl - total_commissions + net_deposits;
      
      // If we have trading_pnl from IBKR, use it to calculate unexplained change
      const ibkr_trading_pnl = nav.trading_pnl || 0;
      const unexplained_change = ibkr_trading_pnl ? 
        (nav_change - net_deposits) - ibkr_trading_pnl : 
        nav_change - expected_change;

      return {
        date: dayDate,
        opening_nav: nav.opening_nav,
        closing_nav: nav.closing_nav,
        nav_change: nav_change,
        trades: dayTrades,
        cash_movements: dayCashMovements,
        realized_pnl: realized_pnl,
        total_commissions: total_commissions,
        net_deposits: net_deposits,
        unexplained_change: unexplained_change,
        isExpanded: dayTrades.length > 0 || dayCashMovements.length > 0 || Math.abs(unexplained_change) > 0.01
      };
    }).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  };

  const toggleDay = (date: string) => {
    setDaysData(prev => prev.map(day => 
      day.date === date ? { ...day, isExpanded: !day.isExpanded } : day
    ));
  };

  const formatCurrency = (amount: number, currency: 'USD' | 'HKD' = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatDualCurrency = (usdAmount: number, hkdAmount?: number) => {
    const usd = formatCurrency(usdAmount, 'USD');
    if (hkdAmount !== undefined) {
      const hkd = formatCurrency(hkdAmount, 'HKD');
      return `${usd} (${hkd})`;
    }
    return usd;
  };

  // Exchange rate from IBKR statement: 7.8496 HKD/USD
  const USD_TO_HKD_RATE = 7.8496;

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'MMMM d, yyyy');
  };

  const formatTime = (dateTimeString: string) => {
    return format(new Date(dateTimeString), 'HH:mm');
  };

  if (loading) {
    return <div className="p-4">Loading NAV reconciliation...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">NAV Reconciliation</h3>
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
              <TableHead>Date / Trading Activity</TableHead>
              <TableHead className="text-right">Price / Amount<br/><span className="text-xs font-normal">USD (HKD)</span></TableHead>
              <TableHead className="text-right">P&L<br/><span className="text-xs font-normal">USD (HKD)</span></TableHead>
              <TableHead className="text-right">Commission<br/><span className="text-xs font-normal">USD (HKD)</span></TableHead>
              <TableHead className="text-right">NAV Change<br/><span className="text-xs font-normal">HKD Base</span></TableHead>
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
                  <TableCell className="font-semibold">
                    {formatDate(day.date)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="text-sm">
                      <div>{formatCurrency(day.opening_nav, 'HKD')} → {formatCurrency(day.closing_nav, 'HKD')}</div>
                      <div className="text-xs text-muted-foreground">Account Base Currency (IBKR)</div>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    {day.realized_pnl !== 0 && (
                      <div className="text-sm">
                        <div className={day.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {day.realized_pnl >= 0 ? '+' : ''}{formatDualCurrency(day.realized_pnl / USD_TO_HKD_RATE, day.realized_pnl)}
                        </div>
                        <div className="text-xs text-muted-foreground">USD (HKD)</div>
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {day.total_commissions > 0 && (
                      <div className="text-sm">
                        <div className="text-red-600">-{formatDualCurrency(day.total_commissions / USD_TO_HKD_RATE, day.total_commissions)}</div>
                        <div className="text-xs text-muted-foreground">USD (HKD)</div>
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-right font-semibold">
                    <div className="text-sm">
                      <div className={day.nav_change >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {day.nav_change >= 0 ? '+' : ''}{formatCurrency(day.nav_change, 'HKD')}
                      </div>
                      <div className="text-xs text-muted-foreground">HKD Change</div>
                    </div>
                  </TableCell>
                </TableRow>

                {/* Expanded details */}
                {day.isExpanded && (
                  <>
                    {/* Opening Balance */}
                    <TableRow className="text-sm text-muted-foreground">
                      <TableCell></TableCell>
                      <TableCell colSpan={4}>Opening Balance</TableCell>
                      <TableCell className="text-right font-mono">
                        <div className="text-sm">
                          <div>{formatCurrency(day.opening_nav, 'HKD')}</div>
                          <div className="text-xs text-muted-foreground">HKD Base (IBKR)</div>
                        </div>
                      </TableCell>
                    </TableRow>

                    {/* Trades - Entry and Exit shown separately */}
                    {day.trades.map((trade) => {
                      const entryAction = trade.quantity < 0 ? 'SELL TO OPEN' : 'BUY TO OPEN';
                      let exitAction = '';
                      let exitDescription = '';
                      
                      if (trade.status === 'open') {
                        exitAction = 'STILL OPEN';
                        exitDescription = 'Position remains open';
                      } else if (trade.exit_reason === 'expired') {
                        exitAction = 'EXPIRED';
                        exitDescription = 'Option expired worthless';
                      } else if (trade.exit_reason === 'stopped_out') {
                        exitAction = trade.quantity < 0 ? 'BUY TO CLOSE' : 'SELL TO CLOSE';
                        exitDescription = 'Stop loss triggered';
                      } else {
                        exitAction = trade.quantity < 0 ? 'BUY TO CLOSE' : 'SELL TO CLOSE';
                        exitDescription = 'Manual close';
                      }

                      return (
                        <React.Fragment key={trade.trade_id}>
                          {/* Entry Row */}
                          <TableRow className="text-sm">
                            <TableCell></TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <span className="text-muted-foreground">{formatTime(trade.entry_time)}</span>
                                <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                                  {entryAction}
                                </Badge>
                                <span className="font-medium">
                                  {Math.abs(trade.quantity)} {trade.symbol} {trade.strike_price}{trade.option_type?.charAt(0)}
                                </span>
                              </div>
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              <div className="text-sm">
                                <div>@${trade.entry_price.toFixed(4)} USD</div>
                                <div className="text-xs text-muted-foreground">Contract Price (IBKR)</div>
                              </div>
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {/* P&L for entry is just the premium effect */}
                            </TableCell>
                            <TableCell className="text-right font-mono">
                              {trade.entry_commission > 0 && (
                                <div className="text-sm">
                                  <div className="text-red-600">-{formatDualCurrency(trade.entry_commission / USD_TO_HKD_RATE, trade.entry_commission)}</div>
                                  <div className="text-xs text-muted-foreground">USD (HKD)</div>
                                </div>
                              )}
                            </TableCell>
                            <TableCell></TableCell>
                          </TableRow>

                          {/* Exit Row (if closed) */}
                          {trade.status === 'closed' && (
                            <TableRow className="text-sm">
                              <TableCell></TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2 ml-4">
                                  <span className="text-muted-foreground">
                                    {trade.exit_time ? formatTime(trade.exit_time) : '16:20'}
                                  </span>
                                  <Badge 
                                    variant="outline" 
                                    className={`text-xs ${
                                      trade.exit_reason === 'expired' 
                                        ? 'bg-gray-50 text-gray-700 border-gray-200'
                                        : trade.exit_reason === 'stopped_out'
                                        ? 'bg-red-50 text-red-700 border-red-200'
                                        : 'bg-green-50 text-green-700 border-green-200'
                                    }`}
                                  >
                                    {exitAction}
                                  </Badge>
                                  <span className="text-sm text-muted-foreground">
                                    {exitDescription}
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell className="text-right font-mono">
                                <div className="text-sm">
                                  <div>@${(trade.exit_price || 0).toFixed(4)} USD</div>
                                  <div className="text-xs text-muted-foreground">Exit Price (IBKR)</div>
                                </div>
                              </TableCell>
                              <TableCell className="text-right font-mono">
                                {trade.realized_pnl !== null && (
                                  <div className="text-sm">
                                    <div className={trade.realized_pnl >= 0 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                                      {trade.realized_pnl >= 0 ? '+' : ''}{formatDualCurrency(trade.realized_pnl / USD_TO_HKD_RATE, trade.realized_pnl)}
                                    </div>
                                    <div className="text-xs text-muted-foreground">USD (HKD)</div>
                                  </div>
                                )}
                              </TableCell>
                              <TableCell className="text-right font-mono">
                                {trade.exit_commission > 0 && (
                                  <div className="text-sm">
                                    <div className="text-red-600">-{formatDualCurrency(trade.exit_commission / USD_TO_HKD_RATE, trade.exit_commission)}</div>
                                    <div className="text-xs text-muted-foreground">USD (HKD)</div>
                                  </div>
                                )}
                              </TableCell>
                              <TableCell></TableCell>
                            </TableRow>
                          )}

                          {/* Open Position Status */}
                          {trade.status === 'open' && (
                            <TableRow className="text-sm">
                              <TableCell></TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2 ml-4">
                                  <Badge variant="outline" className="text-xs bg-yellow-50 text-yellow-700 border-yellow-200">
                                    {exitAction}
                                  </Badge>
                                  <span className="text-sm text-muted-foreground">
                                    {exitDescription}
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell className="text-right font-mono text-muted-foreground">
                                TBD
                              </TableCell>
                              <TableCell className="text-right font-mono text-muted-foreground">
                                TBD
                              </TableCell>
                              <TableCell></TableCell>
                              <TableCell></TableCell>
                            </TableRow>
                          )}
                        </React.Fragment>
                      );
                    })}

                    {/* Cash Movements */}
                    {day.cash_movements.map((movement) => (
                      <TableRow key={movement.movement_id} className="text-sm">
                        <TableCell></TableCell>
                        <TableCell>
                          <span className="text-muted-foreground">
                            {movement.movement_time ? formatTime(movement.movement_date + 'T' + movement.movement_time) : '00:00'}
                          </span>
                          {' '}
                          {movement.description || movement.movement_type}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          <div className="text-sm">
                            <span className={movement.movement_type === 'DEPOSIT' ? 'text-green-600' : 'text-red-600'}>
                              {movement.movement_type === 'DEPOSIT' ? '+' : '-'}{formatDualCurrency(Math.abs(movement.amount) / USD_TO_HKD_RATE, Math.abs(movement.amount))}
                            </span>
                            <div className="text-xs text-muted-foreground">USD (HKD)</div>
                          </div>
                        </TableCell>
                        <TableCell></TableCell>
                        <TableCell></TableCell>
                        <TableCell></TableCell>
                      </TableRow>
                    ))}

                    {/* Reconciliation Summary */}
                    <TableRow className="border-t text-sm font-medium">
                      <TableCell></TableCell>
                      <TableCell>Daily Summary</TableCell>
                      <TableCell className="text-right">
                        {day.net_deposits !== 0 && (
                          <div className="text-sm">
                            <span className={day.net_deposits >= 0 ? 'text-green-600' : 'text-red-600'}>
                              Cash: {day.net_deposits >= 0 ? '+' : ''}{formatDualCurrency(day.net_deposits / USD_TO_HKD_RATE, day.net_deposits)}
                            </span>
                            <div className="text-xs text-muted-foreground">USD (HKD)</div>
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {day.realized_pnl !== 0 && (
                          <div className="text-sm">
                            <span className={day.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                              {day.realized_pnl >= 0 ? '+' : ''}{formatDualCurrency(day.realized_pnl / USD_TO_HKD_RATE, day.realized_pnl)}
                            </span>
                            <div className="text-xs text-muted-foreground">USD (HKD)</div>
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {day.total_commissions > 0 && (
                          <div className="text-sm">
                            <span className="text-red-600">-{formatDualCurrency(day.total_commissions / USD_TO_HKD_RATE, day.total_commissions)}</span>
                            <div className="text-xs text-muted-foreground">USD (HKD)</div>
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="text-sm">
                          <div>Expected: {formatCurrency(day.opening_nav + day.realized_pnl - day.total_commissions + day.net_deposits, 'HKD')}</div>
                          <div className="text-xs text-muted-foreground">HKD Base</div>
                        </div>
                      </TableCell>
                    </TableRow>

                    {/* Unexplained change */}
                    {Math.abs(day.unexplained_change) > 0.01 && (
                      <TableRow className="text-sm">
                        <TableCell></TableCell>
                        <TableCell className="text-orange-600">
                          Unexplained Change (Unrealized P&L, Interest, Fees)
                        </TableCell>
                        <TableCell></TableCell>
                        <TableCell></TableCell>
                        <TableCell></TableCell>
                        <TableCell className="text-right font-mono text-orange-600">
                          <div className="text-sm">
                            <div>{day.unexplained_change >= 0 ? '+' : ''}{formatCurrency(day.unexplained_change, 'HKD')}</div>
                            <div className="text-xs text-muted-foreground">HKD Change</div>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}

                    {/* Closing Balance */}
                    <TableRow className="text-sm font-medium">
                      <TableCell></TableCell>
                      <TableCell colSpan={4}>Closing Balance</TableCell>
                      <TableCell className="text-right font-mono">
                        <div className="text-sm">
                          <div>{formatCurrency(day.closing_nav, 'HKD')}</div>
                          <div className="text-xs text-muted-foreground">HKD Base (IBKR)</div>
                        </div>
                      </TableCell>
                    </TableRow>
                  </>
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