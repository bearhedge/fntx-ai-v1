import React, { useEffect, useState, useCallback, useMemo } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Loader2, TrendingUp, TrendingDown } from "lucide-react";
import { format } from "date-fns";
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from "@/components/ui/pagination";

// Match the database schema for automated trade logging
type Trade = {
  trade_id: string;
  symbol: string;
  strike_price: number;
  option_type: 'PUT' | 'CALL';
  expiration: string;
  quantity: number;
  entry_time: string;
  entry_price: number;
  exit_time?: string;
  exit_price?: number;
  exit_reason?: 'expired' | 'stopped_out' | 'take_profit' | 'manual' | 'assigned';
  realized_pnl?: number;
  status: 'open' | 'closed';
  stop_loss_price?: number;
  take_profit_price?: number;
  market_snapshot?: any;
};

interface TradesListProps {
  filterStatus?: 'all' | 'open' | 'closed';
  searchTerm?: string;
  currentPage?: number;
  itemsPerPage?: number;
  onPageChange?: (page: number) => void;
  onTotalPagesChange?: (totalPages: number) => void;
}

export const TradesList: React.FC<TradesListProps> = ({ 
  filterStatus = 'all',
  searchTerm = '',
  currentPage = 1,
  itemsPerPage = 50,
  onPageChange,
  onTotalPagesChange
}) => {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch trades from API
  const fetchTrades = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterStatus !== 'all') {
        params.append('status', filterStatus);
      }
      params.append('limit', '100');
      
      const response = await fetch(`/api/trades/history?${params}`);
      if (!response.ok) throw new Error('Failed to fetch trades');
      
      const data = await response.json();
      setTrades(data.trades || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching trades:', err);
      setError('Failed to load trades');
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  // Initial fetch
  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  // WebSocket for real-time updates
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === 'trade_update') {
        if (message.event === 'new_trade') {
          // Add new trade to the list
          setTrades(prev => [message.data, ...prev]);
        } else if (message.event === 'trade_closed') {
          // Update closed trade
          setTrades(prev => prev.map(trade => 
            trade.trade_id === message.data.trade_id 
              ? { ...trade, ...message.data, status: 'closed' }
              : trade
          ));
        }
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, []);

  // Filter trades based on search term
  const filteredTrades = useMemo(() => {
    return trades.filter(trade => {
      if (!searchTerm) return true;
      const search = searchTerm.toLowerCase();
      return (
        trade.symbol.toLowerCase().includes(search) ||
        trade.strike_price.toString().includes(search) ||
        trade.option_type.toLowerCase().includes(search)
      );
    });
  }, [trades, searchTerm]);

  // Calculate pagination
  const totalPages = Math.ceil(filteredTrades.length / itemsPerPage);
  const paginatedTrades = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredTrades.slice(startIndex, endIndex);
  }, [filteredTrades, currentPage, itemsPerPage]);

  // Update total pages when filtered trades change
  useEffect(() => {
    if (onTotalPagesChange) {
      onTotalPagesChange(totalPages);
    }
  }, [totalPages, onTotalPagesChange]);

  // Format date/time
  const formatDateTime = (dateString: string) => {
    return format(new Date(dateString), 'MMM dd, HH:mm:ss');
  };

  // Format P&L with color
  const formatPnL = (pnl?: number) => {
    if (pnl === undefined || pnl === null) return '-';
    const formatted = `$${Math.abs(pnl).toFixed(2)}`;
    return (
      <span className={pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
        {pnl >= 0 ? '+' : '-'}{formatted}
      </span>
    );
  };

  // Get status badge with neutral display
  const getStatusBadge = (trade: Trade) => {
    if (trade.status === 'open') {
      return <Badge variant="default" className="bg-blue-500">Open</Badge>;
    }
    
    // Map exit reasons to more relatable terms
    let displayText = 'Closed';
    switch (trade.exit_reason) {
      case 'manual':
        // Use relatable terms based on P&L
        if (trade.realized_pnl && trade.realized_pnl < 0) {
          displayText = 'Stopped Out';
        } else if (trade.realized_pnl && trade.realized_pnl > 0) {
          displayText = 'Take Profit';
        } else {
          displayText = 'Closed';
        }
        break;
      case 'stopped_out':
        displayText = 'Stopped Out';
        break;
      case 'take_profit':
        displayText = 'Take Profit';
        break;
      case 'expired':
        displayText = 'Expired';
        break;
      case 'assigned':
        displayText = 'Assigned';
        break;
      default:
        displayText = trade.exit_reason || 'Closed';
    }
    
    // Always use neutral variant - let P&L column show profit/loss with colors
    return <Badge variant="outline" className="bg-gray-100">{displayText}</Badge>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />
        <span>Loading trades...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 text-red-500">
        {error}
      </div>
    );
  }

  if (filteredTrades.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No trades found
      </div>
    );
  }

  return (
    <div className="w-full">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>Contract</TableHead>
            <TableHead>Qty</TableHead>
            <TableHead>Entry</TableHead>
            <TableHead>Exit</TableHead>
            <TableHead>P&L</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>SL/TP</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {paginatedTrades.map((trade) => (
            <TableRow key={trade.trade_id}>
              <TableCell className="text-sm">
                {formatDateTime(trade.entry_time)}
              </TableCell>
              <TableCell className="font-medium">
                {trade.symbol} {trade.strike_price} {trade.option_type[0]}
                <div className="text-xs text-gray-500">
                  Exp: {format(new Date(trade.expiration), 'MMM dd')}
                </div>
              </TableCell>
              <TableCell>{trade.quantity}</TableCell>
              <TableCell>${trade.entry_price.toFixed(2)}</TableCell>
              <TableCell>
                {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : '-'}
              </TableCell>
              <TableCell className="font-medium">
                {formatPnL(trade.realized_pnl)}
              </TableCell>
              <TableCell>{getStatusBadge(trade)}</TableCell>
              <TableCell className="text-xs">
                {trade.stop_loss_price && (
                  <div>SL: ${trade.stop_loss_price.toFixed(2)}</div>
                )}
                {trade.take_profit_price && (
                  <div>TP: ${trade.take_profit_price.toFixed(2)}</div>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center mt-4">
          <Pagination className="py-0">
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious 
                  onClick={() => onPageChange && onPageChange(Math.max(1, currentPage - 1))} 
                  className={currentPage === 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'} 
                />
              </PaginationItem>
              
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (currentPage <= 3) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = currentPage - 2 + i;
                }
                
                return (
                  <PaginationItem key={pageNum}>
                    <PaginationLink 
                      onClick={() => onPageChange && onPageChange(pageNum)} 
                      isActive={currentPage === pageNum} 
                      className="cursor-pointer"
                    >
                      {pageNum}
                    </PaginationLink>
                  </PaginationItem>
                );
              })}
              
              <PaginationItem>
                <PaginationNext 
                  onClick={() => onPageChange && onPageChange(Math.min(totalPages, currentPage + 1))} 
                  className={currentPage === totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'} 
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}
    </div>
  );
};