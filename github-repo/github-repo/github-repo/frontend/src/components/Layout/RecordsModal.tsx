import { TradesList } from "../../components/TradesList";
import React, { useState, useMemo } from 'react';
import { X, ChevronDown, ExternalLink, Brain, ChevronUp, Download, Search, Calendar as CalendarIcon, HelpCircle } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from "@/components/ui/pagination";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { TabNavigation } from './TabNavigation';
import { WithdrawalTab } from './WithdrawalTab';
import { WithdrawalRecord, AvailabilityBreakdown } from '@/types/trading';
import { AnalyticsTab } from './Analytics/AnalyticsTab';

interface RecordDetails {
  time: string;
  waitTime: number;
  premium: number;
  otmPercent: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  ivRank: number;
  stopLossRatio: number;
  takeProfitRatio: number;
  blockchainTxId: string;
  optimalExit: boolean;
}
interface Record {
  id: string;
  date: string;
  type: 'Put' | 'Call' | 'Both';
  strike: string;
  risk: 'Low' | 'Moderate' | 'High';
  volume: number;
  result: 'Expired' | 'Exercised';
  pnl: number;
  details: RecordDetails;
}
interface RecordsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Updated performance metrics to include the 4 new ratios - now 16 total for 4x4 grid
const performanceMetrics = [{
  label: "DPI",
  value: "0.05x"
}, {
  label: "RVPI",
  value: "0.95x"
}, {
  label: "TVPI",
  value: "1.00x"
}, {
  label: "MOIC",
  value: "1.00x"
}, {
  label: "IRR",
  value: "0.40%"
}, {
  label: "NAV",
  value: "HKD 1,000,000"
}, {
  label: "Principal",
  value: "HKD 1,000,000"
}, {
  label: "Exercise Ratio",
  value: "8.00%"
}, {
  label: "Time to Liquidity",
  value: "3.4 hours"
}, {
  label: "Sharpe Ratio",
  value: "1.00"
}, {
  label: "Take-profit Ratio",
  value: "10%"
}, {
  label: "Stop-loss Ratio",
  value: "40%"
}, {
  label: "Stop-loss Multiple",
  value: "3.00x"
}, {
  label: "Take-profit Multiple",
  value: "0.15x"
}, {
  label: "Maximum Drawdown",
  value: "5%"
}, {
  label: "Win Rate",
  value: "40%"
}];
export const RecordsModal: React.FC<RecordsModalProps> = ({
  isOpen,
  onClose
}) => {
  const [activeTab, setActiveTab] = useState('performance');
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [sortBy, setSortBy] = useState('date');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [selectedTimeframe, setSelectedTimeframe] = useState('3M');
  const [flippedCard, setFlippedCard] = useState<string | null>(null);
  const [customDateRange, setCustomDateRange] = useState<{
    from?: Date;
    to?: Date;
  }>({});
  const [isCustomDateOpen, setIsCustomDateOpen] = useState(false);
  const recordsPerPage = 50;

  // Sample withdrawal data
  const sampleWithdrawals: WithdrawalRecord[] = [{
    id: '1',
    date: '6/2/2025',
    amount: 350,
    status: 'Pending',
    destination: 'Bank Account (****1234)',
    transactionId: 'TXN001',
    fees: 5
  }, {
    id: '2',
    date: '5/28/2025',
    amount: 500,
    status: 'Completed',
    destination: 'Bank Account (****1234)',
    transactionId: 'TXN002',
    fees: 5
  }, {
    id: '3',
    date: '5/15/2025',
    amount: 1200,
    status: 'Completed',
    destination: 'Crypto Wallet (0x1234...)',
    transactionId: 'TXN003',
    fees: 15
  }, {
    id: '4',
    date: '4/30/2025',
    amount: 800,
    status: 'Completed',
    destination: 'Bank Account (****1234)',
    transactionId: 'TXN004',
    fees: 5
  }];
  const availabilityBreakdown: AvailabilityBreakdown = {
    total: 18820,
    available: 2500,
    locked: 14000,
    pendingRelease: [{
      amount: 2320,
      releaseDate: '6/15/2025',
      reason: 'Options expiry'
    }]
  };
  const filteredAndSortedRecords = useMemo(() => {
    let filtered = sampleData;

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(record => record.date.toLowerCase().includes(searchTerm.toLowerCase()) || record.type.toLowerCase().includes(searchTerm.toLowerCase()) || record.strike.toLowerCase().includes(searchTerm.toLowerCase()) || record.risk.toLowerCase().includes(searchTerm.toLowerCase()));
    }

    // Apply type filter
    if (filterType !== 'all') {
      filtered = filtered.filter(record => record.type.toLowerCase() === filterType);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'date':
          return new Date(b.date).getTime() - new Date(a.date).getTime();
        case 'pnl':
          return b.pnl - a.pnl;
        case 'risk':
          const riskOrder = {
            'Low': 1,
            'Moderate': 2,
            'High': 3
          };
          return riskOrder[b.risk] - riskOrder[a.risk];
        default:
          return 0;
      }
    });
    return filtered;
  }, [searchTerm, filterType, sortBy]);
  const totalPages = Math.ceil(filteredAndSortedRecords.length / recordsPerPage);
  const currentRecords = filteredAndSortedRecords.slice((currentPage - 1) * recordsPerPage, currentPage * recordsPerPage);
  const getResultIcon = (result: string) => {
    switch (result) {
      case 'Expired':
        return '✓';
      case 'Exercised':
        return '!';
      default:
        return '?';
    }
  };
  const handleRowClick = (recordId: string) => {
    setExpandedRow(expandedRow === recordId ? null : recordId);
  };
  const handleCardClick = (metricLabel: string) => {
    setFlippedCard(flippedCard === metricLabel ? null : metricLabel);
  };
  const handleExport = () => {
    console.log('Exporting CSV...');
  };
  const handleTimeframeChange = (timeframe: string) => {
    if (timeframe === 'Custom Date') {
      setIsCustomDateOpen(true);
    } else {
      setSelectedTimeframe(timeframe);
      setCustomDateRange({});
    }
  };
  const formatCustomDateRange = () => {
    if (customDateRange.from && customDateRange.to) {
      return `${format(customDateRange.from, "MMM dd")} - ${format(customDateRange.to, "MMM dd, yyyy")}`;
    } else if (customDateRange.from) {
      return `From ${format(customDateRange.from, "MMM dd, yyyy")}`;
    }
    return "Custom Date";
  };
  return <TooltipProvider>
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-7xl h-[95vh] flex flex-col bg-white p-0">
          <DialogHeader className="p-6 flex-shrink-0 bg-gray-300">
            <div className="flex items-center justify-between">
              <DialogTitle className="text-xl text-black font-semibold">RECORDS</DialogTitle>
            </div>
          </DialogHeader>

          <div className="flex-shrink-0 px-6">
            <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
          </div>

          <div className="flex-1 overflow-hidden">
            <ScrollArea className="h-full">
              <div className="px-6 pb-6">
                {activeTab === 'performance' && <div className="space-y-6">
                    {/* Performance Metrics Section */}
                    <div className="flex items-center justify-between py-[5px]">
                      <h3 className="text-gray-900 text-xl font-extralight"></h3>
                      <div className="flex gap-2">
                        {['1W', '1M', '3M', '6M', 'YTD', '1Y', 'ALL'].map(timeframe => <Button key={timeframe} variant={selectedTimeframe === timeframe ? "default" : "outline"} size="sm" onClick={() => handleTimeframeChange(timeframe)} className="h-8 text-white hover:bg-white-300 text-xs bg-zinc-500 hover:bg-zinc-500 px-[20px]">
                            {timeframe}
                          </Button>)}
                        <Popover open={isCustomDateOpen} onOpenChange={setIsCustomDateOpen}>
                          <PopoverTrigger asChild>
                            <Button variant={customDateRange.from ? "default" : "outline"} size="sm" className="h-8 border-gray-200 text-white px-[20px] text-xs bg-zinc-500 hover:bg-zinc-500">
                              <CalendarIcon className="w-3 h-3 mr-1" />
                              {formatCustomDateRange()}
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-auto p-0" align="end">
                            <Calendar mode="range" selected={{
                          from: customDateRange.from,
                          to: customDateRange.to
                        }} onSelect={range => {
                          setCustomDateRange(range || {});
                          if (range?.from && range?.to) {
                            setSelectedTimeframe('Custom Date');
                            setIsCustomDateOpen(false);
                          }
                        }} disabled={date => date > new Date() || date < new Date(new Date().getFullYear() - 1)} initialFocus />
                          </PopoverContent>
                        </Popover>
                      </div>
                    </div>
                    
                    {/* Performance Metrics Grid - 4 columns x 4 rows with narrower boxes */}
                    <div className="grid grid-cols-4 gap-3 w-full">
                      {performanceMetrics.map((metric, index) => <div key={metric.label} className="bg-gray-200 rounded-lg p-3 flex flex-col text-center min-h-[100px] hover:bg-gray-300 transition-colors duration-200">
                          <div className="text-xs font-normal text-gray-700 mb-2 pt-1">{metric.label}</div>
                          <div className="flex-1 flex items-center justify-center">
                            <div className="text-lg font-bold text-gray-900">{metric.value}</div>
                          </div>
                        </div>)}
                    </div>
                  </div>}

                {activeTab === 'history' && <div className="space-y-4">
                    {/* Controls */}
                    <div className="flex items-center gap-4">
                      <Select value={filterType} onValueChange={setFilterType}>
                        <SelectTrigger className="w-32">
                          <SelectValue placeholder="Filter" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Types</SelectItem>
                          <SelectItem value="put">Put</SelectItem>
                          <SelectItem value="call">Call</SelectItem>
                          <SelectItem value="both">Both</SelectItem>
                        </SelectContent>
                      </Select>

                      <Select value={sortBy} onValueChange={setSortBy}>
                        <SelectTrigger className="w-32">
                          <SelectValue placeholder="Sort by" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="date">Date</SelectItem>
                          <SelectItem value="pnl">PnL</SelectItem>
                          <SelectItem value="risk">Risk</SelectItem>
                        </SelectContent>
                      </Select>

                      <div className="relative flex-1 max-w-sm">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <Input placeholder="Search records..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="pl-10" />
                      </div>

                      <Button variant="outline" onClick={handleExport} className="gap-2 text-inherit font-normal">
                        <Download className="w-4 h-4" />
                        Export CSV
                      </Button>
                    </div>
                    {/* Table */}
                    <TradesList />
                    {/* Pagination */}
                    <div className="flex items-center justify-center mt-4">
                      <Pagination className="py-0">
                        <PaginationContent>
                          <PaginationItem>
                            <PaginationPrevious onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} className={currentPage === 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'} />
                          </PaginationItem>
                          
                          {Array.from({
                        length: Math.min(5, totalPages)
                      }, (_, i) => {
                        const pageNum = i + 1;
                        return <PaginationItem key={pageNum}>
                                <PaginationLink onClick={() => setCurrentPage(pageNum)} isActive={currentPage === pageNum} className="cursor-pointer">
                                  {pageNum}
                                </PaginationLink>
                              </PaginationItem>;
                      })}
                          
                          <PaginationItem>
                            <PaginationNext onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} className={currentPage === totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'} />
                          </PaginationItem>
                        </PaginationContent>
                      </Pagination>
                    </div>
                  </div>}

                {activeTab === 'withdrawals' && <WithdrawalTab availableBalance={2500} withdrawalHistory={sampleWithdrawals} availabilityBreakdown={availabilityBreakdown} />}

                {activeTab === 'analytics' && <AnalyticsTab />}
              </div>
            </ScrollArea>
          </div>
        </DialogContent>
      </Dialog>
    </TooltipProvider>;
};
const sampleData: Record[] = [
// Page 1 records (first 50)
{
  id: '1',
  date: '6/30/2025',
  type: 'Put',
  strike: '557P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -320,
  details: {
    time: '14:32 EST',
    waitTime: 2.1,
    premium: 0.55,
    otmPercent: 2.5,
    delta: -0.13,
    gamma: 0.02,
    theta: 0.19,
    vega: 0.11,
    ivRank: 78,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x1234...',
    optimalExit: true
  }
}, {
  id: '2',
  date: '6/27/2025',
  type: 'Both',
  strike: '556C / 556P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 310,
  details: {
    time: '09:15 EST',
    waitTime: 3.2,
    premium: 0.39,
    otmPercent: 1.8,
    delta: 0.22,
    gamma: 0.03,
    theta: -0.15,
    vega: 0.09,
    ivRank: 65,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x5678...',
    optimalExit: true
  }
}, {
  id: '3',
  date: '6/26/2025',
  type: 'Call',
  strike: '555C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -300,
  details: {
    time: '10:15 EST',
    waitTime: 1.5,
    premium: 0.40,
    otmPercent: 3.2,
    delta: -0.18,
    gamma: 0.03,
    theta: 0.22,
    vega: 0.14,
    ivRank: 82,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x9abc...',
    optimalExit: false
  }
}, {
  id: '4',
  date: '6/25/2025',
  type: 'Put',
  strike: '554P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 290,
  details: {
    time: '11:30 EST',
    waitTime: 2.8,
    premium: 0.45,
    otmPercent: 2.1,
    delta: -0.15,
    gamma: 0.02,
    theta: 0.18,
    vega: 0.12,
    ivRank: 75,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0xdef0...',
    optimalExit: true
  }
}, {
  id: '5',
  date: '6/24/2025',
  type: 'Both',
  strike: '553C / 553P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -280,
  details: {
    time: '13:45 EST',
    waitTime: 1.9,
    premium: 0.52,
    otmPercent: 2.8,
    delta: 0.20,
    gamma: 0.03,
    theta: -0.16,
    vega: 0.10,
    ivRank: 80,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x1fed...',
    optimalExit: false
  }
}, {
  id: '6',
  date: '6/23/2025',
  type: 'Call',
  strike: '552C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 270,
  details: {
    time: '15:20 EST',
    waitTime: 3.5,
    premium: 0.35,
    otmPercent: 1.5,
    delta: 0.25,
    gamma: 0.04,
    theta: -0.18,
    vega: 0.08,
    ivRank: 68,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x2abc...',
    optimalExit: true
  }
}, {
  id: '7',
  date: '6/20/2025',
  type: 'Put',
  strike: '551P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -260,
  details: {
    time: '09:45 EST',
    waitTime: 2.3,
    premium: 0.48,
    otmPercent: 2.4,
    delta: -0.16,
    gamma: 0.02,
    theta: 0.20,
    vega: 0.13,
    ivRank: 77,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x3def...',
    optimalExit: false
  }
}, {
  id: '8',
  date: '6/19/2025',
  type: 'Both',
  strike: '550C / 550P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 250,
  details: {
    time: '11:15 EST',
    waitTime: 4.1,
    premium: 0.38,
    otmPercent: 1.7,
    delta: 0.18,
    gamma: 0.03,
    theta: -0.14,
    vega: 0.09,
    ivRank: 72,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x4fed...',
    optimalExit: true
  }
}, {
  id: '9',
  date: '6/18/2025',
  type: 'Call',
  strike: '549C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -240,
  details: {
    time: '14:50 EST',
    waitTime: 2.7,
    premium: 0.42,
    otmPercent: 2.9,
    delta: 0.23,
    gamma: 0.04,
    theta: -0.17,
    vega: 0.11,
    ivRank: 85,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x5abc...',
    optimalExit: false
  }
}, {
  id: '10',
  date: '6/17/2025',
  type: 'Put',
  strike: '548P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 230,
  details: {
    time: '10:25 EST',
    waitTime: 3.0,
    premium: 0.46,
    otmPercent: 2.2,
    delta: -0.14,
    gamma: 0.02,
    theta: 0.19,
    vega: 0.12,
    ivRank: 73,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x6def...',
    optimalExit: true
  }
}, {
  id: '11',
  date: '6/16/2025',
  type: 'Both',
  strike: '547C / 547P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -220,
  details: {
    time: '12:40 EST',
    waitTime: 1.8,
    premium: 0.50,
    otmPercent: 3.1,
    delta: 0.21,
    gamma: 0.03,
    theta: -0.15,
    vega: 0.10,
    ivRank: 88,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x7fed...',
    optimalExit: false
  }
}, {
  id: '12',
  date: '6/13/2025',
  type: 'Call',
  strike: '546C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 210,
  details: {
    time: '16:10 EST',
    waitTime: 3.6,
    premium: 0.33,
    otmPercent: 1.4,
    delta: 0.26,
    gamma: 0.04,
    theta: -0.19,
    vega: 0.07,
    ivRank: 66,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x8abc...',
    optimalExit: true
  }
}, {
  id: '13',
  date: '6/12/2025',
  type: 'Put',
  strike: '545P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -200,
  details: {
    time: '09:30 EST',
    waitTime: 2.4,
    premium: 0.47,
    otmPercent: 2.6,
    delta: -0.17,
    gamma: 0.02,
    theta: 0.21,
    vega: 0.14,
    ivRank: 79,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x9def...',
    optimalExit: false
  }
}, {
  id: '14',
  date: '6/11/2025',
  type: 'Both',
  strike: '544C / 544P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 190,
  details: {
    time: '11:55 EST',
    waitTime: 4.2,
    premium: 0.36,
    otmPercent: 1.6,
    delta: 0.19,
    gamma: 0.03,
    theta: -0.13,
    vega: 0.09,
    ivRank: 70,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0xafed...',
    optimalExit: true
  }
}, {
  id: '15',
  date: '6/10/2025',
  type: 'Call',
  strike: '543C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -180,
  details: {
    time: '13:25 EST',
    waitTime: 2.6,
    premium: 0.44,
    otmPercent: 3.0,
    delta: 0.24,
    gamma: 0.04,
    theta: -0.18,
    vega: 0.11,
    ivRank: 86,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0xbabc...',
    optimalExit: false
  }
}, {
  id: '16',
  date: '6/9/2025',
  type: 'Put',
  strike: '542P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 170,
  details: {
    time: '15:05 EST',
    waitTime: 3.1,
    premium: 0.41,
    otmPercent: 2.0,
    delta: -0.15,
    gamma: 0.02,
    theta: 0.17,
    vega: 0.12,
    ivRank: 74,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0xcdef...',
    optimalExit: true
  }
}, {
  id: '17',
  date: '6/6/2025',
  type: 'Both',
  strike: '541C / 541P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -160,
  details: {
    time: '10:20 EST',
    waitTime: 1.7,
    premium: 0.53,
    otmPercent: 3.3,
    delta: 0.22,
    gamma: 0.03,
    theta: -0.16,
    vega: 0.10,
    ivRank: 90,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0xdfed...',
    optimalExit: false
  }
}, {
  id: '18',
  date: '6/5/2025',
  type: 'Call',
  strike: '540C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 150,
  details: {
    time: '12:35 EST',
    waitTime: 3.7,
    premium: 0.31,
    otmPercent: 1.3,
    delta: 0.27,
    gamma: 0.04,
    theta: -0.20,
    vega: 0.06,
    ivRank: 64,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0xeabc...',
    optimalExit: true
  }
}, {
  id: '19',
  date: '6/4/2025',
  type: 'Put',
  strike: '539P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -140,
  details: {
    time: '14:15 EST',
    waitTime: 2.5,
    premium: 0.49,
    otmPercent: 2.7,
    delta: -0.18,
    gamma: 0.02,
    theta: 0.22,
    vega: 0.15,
    ivRank: 81,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0xfdef...',
    optimalExit: false
  }
}, {
  id: '20',
  date: '6/3/2025',
  type: 'Both',
  strike: '538C / 538P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 130,
  details: {
    time: '16:45 EST',
    waitTime: 4.3,
    premium: 0.34,
    otmPercent: 1.5,
    delta: 0.20,
    gamma: 0.03,
    theta: -0.12,
    vega: 0.08,
    ivRank: 69,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x10fed...',
    optimalExit: true
  }
}, {
  id: '21',
  date: '6/2/2025',
  type: 'Call',
  strike: '537C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -120,
  details: {
    time: '09:50 EST',
    waitTime: 2.8,
    premium: 0.43,
    otmPercent: 3.2,
    delta: 0.25,
    gamma: 0.04,
    theta: -0.19,
    vega: 0.12,
    ivRank: 87,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x11abc...',
    optimalExit: false
  }
}, {
  id: '22',
  date: '5/30/2025',
  type: 'Put',
  strike: '536P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 110,
  details: {
    time: '11:40 EST',
    waitTime: 3.2,
    premium: 0.40,
    otmPercent: 1.9,
    delta: -0.16,
    gamma: 0.02,
    theta: 0.18,
    vega: 0.13,
    ivRank: 76,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x12def...',
    optimalExit: true
  }
}, {
  id: '23',
  date: '5/29/2025',
  type: 'Both',
  strike: '535C / 535P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -100,
  details: {
    time: '13:10 EST',
    waitTime: 1.6,
    premium: 0.54,
    otmPercent: 3.4,
    delta: 0.23,
    gamma: 0.03,
    theta: -0.17,
    vega: 0.11,
    ivRank: 92,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x13fed...',
    optimalExit: false
  }
}, {
  id: '24',
  date: '5/28/2025',
  type: 'Call',
  strike: '534C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 90,
  details: {
    time: '15:30 EST',
    waitTime: 3.8,
    premium: 0.29,
    otmPercent: 1.2,
    delta: 0.28,
    gamma: 0.04,
    theta: -0.21,
    vega: 0.05,
    ivRank: 62,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x14abc...',
    optimalExit: true
  }
}, {
  id: '25',
  date: '5/27/2025',
  type: 'Put',
  strike: '533P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -80,
  details: {
    time: '10:05 EST',
    waitTime: 2.6,
    premium: 0.51,
    otmPercent: 2.8,
    delta: -0.19,
    gamma: 0.02,
    theta: 0.23,
    vega: 0.16,
    ivRank: 83,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x15def...',
    optimalExit: false
  }
}, {
  id: '26',
  date: '5/23/2025',
  type: 'Both',
  strike: '532C / 532P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 70,
  details: {
    time: '12:25 EST',
    waitTime: 4.4,
    premium: 0.32,
    otmPercent: 1.4,
    delta: 0.21,
    gamma: 0.03,
    theta: -0.11,
    vega: 0.07,
    ivRank: 67,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x16fed...',
    optimalExit: true
  }
}, {
  id: '27',
  date: '5/22/2025',
  type: 'Call',
  strike: '531C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -60,
  details: {
    time: '14:55 EST',
    waitTime: 2.9,
    premium: 0.45,
    otmPercent: 3.3,
    delta: 0.26,
    gamma: 0.04,
    theta: -0.20,
    vega: 0.13,
    ivRank: 89,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x17abc...',
    optimalExit: false
  }
}, {
  id: '28',
  date: '5/21/2025',
  type: 'Put',
  strike: '530P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 50,
  details: {
    time: '16:20 EST',
    waitTime: 3.3,
    premium: 0.38,
    otmPercent: 1.8,
    delta: -0.17,
    gamma: 0.02,
    theta: 0.19,
    vega: 0.14,
    ivRank: 78,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x18def...',
    optimalExit: true
  }
}, {
  id: '29',
  date: '5/20/2025',
  type: 'Put',
  strike: '528P',
  risk: 'Moderate',
  volume: 3,
  result: 'Exercised',
  pnl: -120,
  details: {
    time: '09:40 EST',
    waitTime: 1.5,
    premium: 0.56,
    otmPercent: 3.5,
    delta: -0.20,
    gamma: 0.02,
    theta: 0.24,
    vega: 0.12,
    ivRank: 94,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x19fed...',
    optimalExit: false
  }
}, {
  id: '30',
  date: '5/19/2025',
  type: 'Call',
  strike: '534C',
  risk: 'Low',
  volume: 2,
  result: 'Expired',
  pnl: 78,
  details: {
    time: '11:15 EST',
    waitTime: 3.9,
    premium: 0.27,
    otmPercent: 1.1,
    delta: 0.29,
    gamma: 0.04,
    theta: -0.22,
    vega: 0.04,
    ivRank: 60,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x1aabc...',
    optimalExit: true
  }
}, {
  id: '31',
  date: '5/16/2025',
  type: 'Put',
  strike: '530P',
  risk: 'Moderate',
  volume: 1,
  result: 'Expired',
  pnl: 55,
  details: {
    time: '13:35 EST',
    waitTime: 2.7,
    premium: 0.52,
    otmPercent: 2.9,
    delta: -0.21,
    gamma: 0.02,
    theta: 0.25,
    vega: 0.17,
    ivRank: 85,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x1bdef...',
    optimalExit: false
  }
}, {
  id: '32',
  date: '5/15/2025',
  type: 'Call',
  strike: '558C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 330,
  details: {
    time: '15:50 EST',
    waitTime: 4.5,
    premium: 0.30,
    otmPercent: 1.3,
    delta: 0.22,
    gamma: 0.03,
    theta: -0.10,
    vega: 0.06,
    ivRank: 65,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x1cfed...',
    optimalExit: true
  }
}, {
  id: '33',
  date: '5/14/2025',
  type: 'Both',
  strike: '559C / 559P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -340,
  details: {
    time: '10:10 EST',
    waitTime: 3.0,
    premium: 0.47,
    otmPercent: 3.4,
    delta: 0.27,
    gamma: 0.04,
    theta: -0.21,
    vega: 0.14,
    ivRank: 91,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x1dabc...',
    optimalExit: false
  }
}, {
  id: '34',
  date: '5/13/2025',
  type: 'Put',
  strike: '560P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 350,
  details: {
    time: '12:45 EST',
    waitTime: 3.4,
    premium: 0.36,
    otmPercent: 1.7,
    delta: -0.18,
    gamma: 0.02,
    theta: 0.20,
    vega: 0.15,
    ivRank: 80,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x1edef...',
    optimalExit: true
  }
}, {
  id: '35',
  date: '5/12/2025',
  type: 'Call',
  strike: '561C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -360,
  details: {
    time: '14:30 EST',
    waitTime: 1.4,
    premium: 0.58,
    otmPercent: 3.6,
    delta: -0.22,
    gamma: 0.02,
    theta: 0.26,
    vega: 0.13,
    ivRank: 96,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x1ffed...',
    optimalExit: false
  }
}, {
  id: '36',
  date: '5/9/2025',
  type: 'Both',
  strike: '562C / 562P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 370,
  details: {
    time: '16:05 EST',
    waitTime: 4.0,
    premium: 0.25,
    otmPercent: 1.0,
    delta: 0.30,
    gamma: 0.04,
    theta: -0.23,
    vega: 0.03,
    ivRank: 58,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x20abc...',
    optimalExit: true
  }
}, {
  id: '37',
  date: '5/8/2025',
  type: 'Put',
  strike: '563P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -380,
  details: {
    time: '09:25 EST',
    waitTime: 2.8,
    premium: 0.53,
    otmPercent: 3.0,
    delta: -0.23,
    gamma: 0.02,
    theta: 0.27,
    vega: 0.18,
    ivRank: 87,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x21def...',
    optimalExit: false
  }
}, {
  id: '38',
  date: '5/7/2025',
  type: 'Call',
  strike: '564C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 390,
  details: {
    time: '11:50 EST',
    waitTime: 4.6,
    premium: 0.28,
    otmPercent: 1.2,
    delta: 0.23,
    gamma: 0.03,
    theta: -0.09,
    vega: 0.05,
    ivRank: 63,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x22fed...',
    optimalExit: true
  }
}, {
  id: '39',
  date: '5/6/2025',
  type: 'Both',
  strike: '565C / 565P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: -400,
  details: {
    time: '13:20 EST',
    waitTime: 3.1,
    premium: 0.48,
    otmPercent: 3.5,
    delta: 0.28,
    gamma: 0.04,
    theta: -0.22,
    vega: 0.15,
    ivRank: 93,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x23abc...',
    optimalExit: false
  }
}, {
  id: '40',
  date: '5/2/2025',
  type: 'Put',
  strike: '566P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 410,
  details: {
    time: '15:35 EST',
    waitTime: 3.5,
    premium: 0.35,
    otmPercent: 1.6,
    delta: -0.19,
    gamma: 0.02,
    theta: 0.21,
    vega: 0.16,
    ivRank: 82,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x24def...',
    optimalExit: true
  }
}, {
  id: '41',
  date: '5/1/2025',
  type: 'Call',
  strike: '567C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -420,
  details: {
    time: '10:15 EST',
    waitTime: 1.3,
    premium: 0.59,
    otmPercent: 3.7,
    delta: -0.24,
    gamma: 0.02,
    theta: 0.28,
    vega: 0.14,
    ivRank: 98,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x25fed...',
    optimalExit: false
  }
}, {
  id: '42',
  date: '4/30/2025',
  type: 'Both',
  strike: '568C / 568P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 430,
  details: {
    time: '12:00 EST',
    waitTime: 4.1,
    premium: 0.24,
    otmPercent: 0.9,
    delta: 0.31,
    gamma: 0.04,
    theta: -0.24,
    vega: 0.02,
    ivRank: 56,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x26abc...',
    optimalExit: true
  }
}, {
  id: '43',
  date: '4/29/2025',
  type: 'Put',
  strike: '569P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -440,
  details: {
    time: '14:25 EST',
    waitTime: 2.9,
    premium: 0.54,
    otmPercent: 3.1,
    delta: -0.25,
    gamma: 0.02,
    theta: 0.29,
    vega: 0.19,
    ivRank: 89,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x27def...',
    optimalExit: false
  }
}, {
  id: '44',
  date: '4/28/2025',
  type: 'Call',
  strike: '570C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 450,
  details: {
    time: '16:40 EST',
    waitTime: 4.7,
    premium: 0.26,
    otmPercent: 1.1,
    delta: 0.24,
    gamma: 0.03,
    theta: -0.08,
    vega: 0.04,
    ivRank: 61,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x28fed...',
    optimalExit: true
  }
}, {
  id: '45',
  date: '4/25/2025',
  type: 'Both',
  strike: '571C / 571P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -460,
  details: {
    time: '09:35 EST',
    waitTime: 3.2,
    premium: 0.49,
    otmPercent: 3.6,
    delta: 0.29,
    gamma: 0.04,
    theta: -0.23,
    vega: 0.16,
    ivRank: 95,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x29abc...',
    optimalExit: false
  }
}, {
  id: '46',
  date: '4/24/2025',
  type: 'Put',
  strike: '572P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 470,
  details: {
    time: '11:05 EST',
    waitTime: 3.6,
    premium: 0.33,
    otmPercent: 1.5,
    delta: -0.20,
    gamma: 0.02,
    theta: 0.22,
    vega: 0.17,
    ivRank: 84,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x2adef...',
    optimalExit: true
  }
}, {
  id: '47',
  date: '4/23/2025',
  type: 'Call',
  strike: '573C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -480,
  details: {
    time: '13:45 EST',
    waitTime: 1.2,
    premium: 0.60,
    otmPercent: 3.8,
    delta: -0.26,
    gamma: 0.02,
    theta: 0.30,
    vega: 0.15,
    ivRank: 100,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x2bfed...',
    optimalExit: false
  }
}, {
  id: '48',
  date: '4/22/2025',
  type: 'Both',
  strike: '574C / 574P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 490,
  details: {
    time: '15:15 EST',
    waitTime: 4.2,
    premium: 0.22,
    otmPercent: 0.8,
    delta: 0.32,
    gamma: 0.04,
    theta: -0.25,
    vega: 0.01,
    ivRank: 54,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x2cabc...',
    optimalExit: true
  }
}, {
  id: '49',
  date: '4/17/2025',
  type: 'Put',
  strike: '575P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -500,
  details: {
    time: '10:30 EST',
    waitTime: 3.0,
    premium: 0.55,
    otmPercent: 3.2,
    delta: -0.27,
    gamma: 0.02,
    theta: 0.31,
    vega: 0.20,
    ivRank: 91,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x2ddef...',
    optimalExit: false
  }
}, {
  id: '50',
  date: '4/16/2025',
  type: 'Call',
  strike: '576C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 510,
  details: {
    time: '12:55 EST',
    waitTime: 4.8,
    premium: 0.24,
    otmPercent: 1.0,
    delta: 0.25,
    gamma: 0.03,
    theta: -0.07,
    vega: 0.03,
    ivRank: 59,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x2efed...',
    optimalExit: true
  }
},
// Page 2 records (records 51-100)
{
  id: '51',
  date: '4/15/2025',
  type: 'Both',
  strike: '577C / 577P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -520,
  details: {
    time: '14:20 EST',
    waitTime: 3.3,
    premium: 0.50,
    otmPercent: 3.7,
    delta: 0.30,
    gamma: 0.04,
    theta: -0.24,
    vega: 0.17,
    ivRank: 97,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x2ffed...',
    optimalExit: false
  }
}, {
  id: '52',
  date: '4/14/2025',
  type: 'Put',
  strike: '578P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 530,
  details: {
    time: '16:45 EST',
    waitTime: 3.7,
    premium: 0.34,
    otmPercent: 1.4,
    delta: -0.21,
    gamma: 0.02,
    theta: 0.23,
    vega: 0.18,
    ivRank: 86,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x30abc...',
    optimalExit: true
  }
}, {
  id: '53',
  date: '4/11/2025',
  type: 'Call',
  strike: '579C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -540,
  details: {
    time: '11:10 EST',
    waitTime: 1.1,
    premium: 0.61,
    otmPercent: 3.9,
    delta: -0.27,
    gamma: 0.02,
    theta: 0.31,
    vega: 0.16,
    ivRank: 102,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x31def...',
    optimalExit: false
  }
}, {
  id: '54',
  date: '4/10/2025',
  type: 'Both',
  strike: '580C / 580P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 550,
  details: {
    time: '13:30 EST',
    waitTime: 4.3,
    premium: 0.21,
    otmPercent: 0.7,
    delta: 0.33,
    gamma: 0.04,
    theta: -0.26,
    vega: 0.01,
    ivRank: 52,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x32fed...',
    optimalExit: true
  }
}, {
  id: '55',
  date: '4/9/2025',
  type: 'Put',
  strike: '581P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -560,
  details: {
    time: '15:55 EST',
    waitTime: 3.1,
    premium: 0.56,
    otmPercent: 3.3,
    delta: -0.28,
    gamma: 0.02,
    theta: 0.32,
    vega: 0.21,
    ivRank: 93,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x33abc...',
    optimalExit: false
  }
}, {
  id: '56',
  date: '4/8/2025',
  type: 'Call',
  strike: '582C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 570,
  details: {
    time: '10:20 EST',
    waitTime: 4.9,
    premium: 0.23,
    otmPercent: 0.9,
    delta: 0.26,
    gamma: 0.03,
    theta: -0.06,
    vega: 0.02,
    ivRank: 57,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x34def...',
    optimalExit: true
  }
}, {
  id: '57',
  date: '4/7/2025',
  type: 'Both',
  strike: '583C / 583P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -580,
  details: {
    time: '12:45 EST',
    waitTime: 3.4,
    premium: 0.51,
    otmPercent: 3.8,
    delta: 0.31,
    gamma: 0.04,
    theta: -0.25,
    vega: 0.18,
    ivRank: 99,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x35fed...',
    optimalExit: false
  }
}, {
  id: '58',
  date: '4/4/2025',
  type: 'Put',
  strike: '584P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 590,
  details: {
    time: '15:10 EST',
    waitTime: 3.8,
    premium: 0.33,
    otmPercent: 1.3,
    delta: -0.22,
    gamma: 0.02,
    theta: 0.24,
    vega: 0.19,
    ivRank: 88,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x36abc...',
    optimalExit: true
  }
}, {
  id: '59',
  date: '4/3/2025',
  type: 'Call',
  strike: '585C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -600,
  details: {
    time: '09:35 EST',
    waitTime: 1.0,
    premium: 0.62,
    otmPercent: 4.0,
    delta: -0.28,
    gamma: 0.02,
    theta: 0.33,
    vega: 0.17,
    ivRank: 104,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x37def...',
    optimalExit: false
  }
}, {
  id: '60',
  date: '4/2/2025',
  type: 'Both',
  strike: '586C / 586P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 610,
  details: {
    time: '11:50 EST',
    waitTime: 4.4,
    premium: 0.20,
    otmPercent: 0.6,
    delta: 0.34,
    gamma: 0.04,
    theta: -0.27,
    vega: 0.00,
    ivRank: 50,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x38fed...',
    optimalExit: true
  }
}, {
  id: '61',
  date: '4/1/2025',
  type: 'Put',
  strike: '587P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -620,
  details: {
    time: '14:15 EST',
    waitTime: 3.2,
    premium: 0.57,
    otmPercent: 3.4,
    delta: -0.29,
    gamma: 0.02,
    theta: 0.34,
    vega: 0.22,
    ivRank: 95,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x39abc...',
    optimalExit: false
  }
}, {
  id: '62',
  date: '3/31/2025',
  type: 'Call',
  strike: '588C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 630,
  details: {
    time: '16:40 EST',
    waitTime: 5.0,
    premium: 0.22,
    otmPercent: 0.8,
    delta: 0.27,
    gamma: 0.03,
    theta: -0.05,
    vega: 0.01,
    ivRank: 55,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x3adef...',
    optimalExit: true
  }
}, {
  id: '63',
  date: '3/28/2025',
  type: 'Both',
  strike: '589C / 589P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -640,
  details: {
    time: '10:05 EST',
    waitTime: 3.5,
    premium: 0.52,
    otmPercent: 3.9,
    delta: 0.32,
    gamma: 0.04,
    theta: -0.26,
    vega: 0.19,
    ivRank: 101,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x3bfed...',
    optimalExit: false
  }
}, {
  id: '64',
  date: '3/27/2025',
  type: 'Put',
  strike: '590P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 650,
  details: {
    time: '12:30 EST',
    waitTime: 3.9,
    premium: 0.32,
    otmPercent: 1.2,
    delta: -0.23,
    gamma: 0.02,
    theta: 0.25,
    vega: 0.20,
    ivRank: 90,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x3cabc...',
    optimalExit: true
  }
}, {
  id: '65',
  date: '3/26/2025',
  type: 'Call',
  strike: '591C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -660,
  details: {
    time: '14:55 EST',
    waitTime: 0.9,
    premium: 0.63,
    otmPercent: 4.1,
    delta: -0.29,
    gamma: 0.02,
    theta: 0.35,
    vega: 0.18,
    ivRank: 106,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x3ddef...',
    optimalExit: false
  }
}, {
  id: '66',
  date: '3/25/2025',
  type: 'Both',
  strike: '592C / 592P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 670,
  details: {
    time: '09:20 EST',
    waitTime: 4.5,
    premium: 0.19,
    otmPercent: 0.5,
    delta: 0.35,
    gamma: 0.04,
    theta: -0.28,
    vega: -0.01,
    ivRank: 48,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x3efed...',
    optimalExit: true
  }
}, {
  id: '67',
  date: '3/24/2025',
  type: 'Put',
  strike: '593P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -680,
  details: {
    time: '11:45 EST',
    waitTime: 3.3,
    premium: 0.58,
    otmPercent: 3.5,
    delta: -0.30,
    gamma: 0.02,
    theta: 0.36,
    vega: 0.23,
    ivRank: 97,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x3fabc...',
    optimalExit: false
  }
}, {
  id: '68',
  date: '3/21/2025',
  type: 'Call',
  strike: '594C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 690,
  details: {
    time: '14:10 EST',
    waitTime: 5.1,
    premium: 0.21,
    otmPercent: 0.7,
    delta: 0.28,
    gamma: 0.03,
    theta: -0.04,
    vega: 0.00,
    ivRank: 53,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x40def...',
    optimalExit: true
  }
}, {
  id: '69',
  date: '3/20/2025',
  type: 'Both',
  strike: '595C / 595P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -700,
  details: {
    time: '16:35 EST',
    waitTime: 3.6,
    premium: 0.53,
    otmPercent: 4.0,
    delta: 0.33,
    gamma: 0.04,
    theta: -0.27,
    vega: 0.20,
    ivRank: 103,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x41fed...',
    optimalExit: false
  }
}, {
  id: '70',
  date: '3/19/2025',
  type: 'Put',
  strike: '596P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 710,
  details: {
    time: '09:00 EST',
    waitTime: 4.0,
    premium: 0.31,
    otmPercent: 1.1,
    delta: -0.24,
    gamma: 0.02,
    theta: 0.26,
    vega: 0.21,
    ivRank: 92,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x42abc...',
    optimalExit: true
  }
}, {
  id: '71',
  date: '3/18/2025',
  type: 'Call',
  strike: '597C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -720,
  details: {
    time: '11:25 EST',
    waitTime: 0.8,
    premium: 0.64,
    otmPercent: 4.2,
    delta: -0.30,
    gamma: 0.02,
    theta: 0.37,
    vega: 0.19,
    ivRank: 108,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x43def...',
    optimalExit: false
  }
}, {
  id: '72',
  date: '3/17/2025',
  type: 'Both',
  strike: '598C / 598P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 730,
  details: {
    time: '13:50 EST',
    waitTime: 4.6,
    premium: 0.18,
    otmPercent: 0.4,
    delta: 0.36,
    gamma: 0.04,
    theta: -0.29,
    vega: -0.02,
    ivRank: 46,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x44fed...',
    optimalExit: true
  }
}, {
  id: '73',
  date: '3/14/2025',
  type: 'Put',
  strike: '599P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -740,
  details: {
    time: '16:15 EST',
    waitTime: 3.4,
    premium: 0.59,
    otmPercent: 3.6,
    delta: -0.31,
    gamma: 0.02,
    theta: 0.38,
    vega: 0.24,
    ivRank: 99,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x45abc...',
    optimalExit: false
  }
}, {
  id: '74',
  date: '3/13/2025',
  type: 'Call',
  strike: '600C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 750,
  details: {
    time: '10:40 EST',
    waitTime: 5.2,
    premium: 0.20,
    otmPercent: 0.6,
    delta: 0.29,
    gamma: 0.03,
    theta: -0.03,
    vega: -0.01,
    ivRank: 51,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x46def...',
    optimalExit: true
  }
}, {
  id: '75',
  date: '3/12/2025',
  type: 'Both',
  strike: '601C / 601P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -760,
  details: {
    time: '13:05 EST',
    waitTime: 3.7,
    premium: 0.54,
    otmPercent: 4.1,
    delta: 0.34,
    gamma: 0.04,
    theta: -0.28,
    vega: 0.21,
    ivRank: 105,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x47fed...',
    optimalExit: false
  }
}, {
  id: '76',
  date: '3/11/2025',
  type: 'Put',
  strike: '602P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 770,
  details: {
    time: '15:30 EST',
    waitTime: 4.1,
    premium: 0.30,
    otmPercent: 1.0,
    delta: -0.25,
    gamma: 0.02,
    theta: 0.27,
    vega: 0.22,
    ivRank: 94,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x48abc...',
    optimalExit: true
  }
}, {
  id: '77',
  date: '3/10/2025',
  type: 'Call',
  strike: '603C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -780,
  details: {
    time: '09:55 EST',
    waitTime: 0.7,
    premium: 0.65,
    otmPercent: 4.3,
    delta: -0.31,
    gamma: 0.02,
    theta: 0.39,
    vega: 0.20,
    ivRank: 110,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x49def...',
    optimalExit: false
  }
}, {
  id: '78',
  date: '3/7/2025',
  type: 'Both',
  strike: '604C / 604P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 790,
  details: {
    time: '12:20 EST',
    waitTime: 4.7,
    premium: 0.17,
    otmPercent: 0.3,
    delta: 0.37,
    gamma: 0.04,
    theta: -0.30,
    vega: -0.03,
    ivRank: 44,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x4afed...',
    optimalExit: true
  }
}, {
  id: '79',
  date: '3/6/2025',
  type: 'Put',
  strike: '605P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -800,
  details: {
    time: '14:45 EST',
    waitTime: 3.5,
    premium: 0.60,
    otmPercent: 3.7,
    delta: -0.32,
    gamma: 0.02,
    theta: 0.40,
    vega: 0.25,
    ivRank: 101,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x4babc...',
    optimalExit: false
  }
}, {
  id: '80',
  date: '3/5/2025',
  type: 'Call',
  strike: '606C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 810,
  details: {
    time: '17:10 EST',
    waitTime: 5.3,
    premium: 0.19,
    otmPercent: 0.5,
    delta: 0.30,
    gamma: 0.03,
    theta: -0.02,
    vega: -0.02,
    ivRank: 49,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x4cdef...',
    optimalExit: true
  }
}, {
  id: '81',
  date: '3/4/2025',
  type: 'Both',
  strike: '607C / 607P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -820,
  details: {
    time: '11:35 EST',
    waitTime: 3.8,
    premium: 0.55,
    otmPercent: 4.2,
    delta: 0.35,
    gamma: 0.04,
    theta: -0.29,
    vega: 0.22,
    ivRank: 107,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x4dfed...',
    optimalExit: false
  }
}, {
  id: '82',
  date: '3/3/2025',
  type: 'Put',
  strike: '608P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 830,
  details: {
    time: '14:00 EST',
    waitTime: 4.2,
    premium: 0.29,
    otmPercent: 0.9,
    delta: -0.26,
    gamma: 0.02,
    theta: 0.28,
    vega: 0.23,
    ivRank: 96,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x4eabc...',
    optimalExit: true
  }
}, {
  id: '83',
  date: '2/28/2025',
  type: 'Call',
  strike: '609C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -840,
  details: {
    time: '16:25 EST',
    waitTime: 0.6,
    premium: 0.66,
    otmPercent: 4.4,
    delta: -0.32,
    gamma: 0.02,
    theta: 0.41,
    vega: 0.21,
    ivRank: 112,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x4fdef...',
    optimalExit: false
  }
}, {
  id: '84',
  date: '2/27/2025',
  type: 'Both',
  strike: '610C / 610P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 850,
  details: {
    time: '10:50 EST',
    waitTime: 4.8,
    premium: 0.16,
    otmPercent: 0.2,
    delta: 0.38,
    gamma: 0.04,
    theta: -0.31,
    vega: -0.04,
    ivRank: 42,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x50fed...',
    optimalExit: true
  }
}, {
  id: '85',
  date: '2/26/2025',
  type: 'Put',
  strike: '611P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -860,
  details: {
    time: '13:15 EST',
    waitTime: 3.6,
    premium: 0.61,
    otmPercent: 3.8,
    delta: -0.33,
    gamma: 0.02,
    theta: 0.42,
    vega: 0.26,
    ivRank: 103,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x51abc...',
    optimalExit: false
  }
}, {
  id: '86',
  date: '2/25/2025',
  type: 'Call',
  strike: '612C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 870,
  details: {
    time: '15:40 EST',
    waitTime: 5.4,
    premium: 0.18,
    otmPercent: 0.4,
    delta: 0.31,
    gamma: 0.03,
    theta: -0.01,
    vega: -0.03,
    ivRank: 47,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x52def...',
    optimalExit: true
  }
}, {
  id: '87',
  date: '2/24/2025',
  type: 'Both',
  strike: '613C / 613P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -880,
  details: {
    time: '10:05 EST',
    waitTime: 3.9,
    premium: 0.56,
    otmPercent: 4.3,
    delta: 0.36,
    gamma: 0.04,
    theta: -0.30,
    vega: 0.23,
    ivRank: 109,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x53fed...',
    optimalExit: false
  }
}, {
  id: '88',
  date: '2/21/2025',
  type: 'Put',
  strike: '614P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 890,
  details: {
    time: '12:30 EST',
    waitTime: 4.3,
    premium: 0.28,
    otmPercent: 0.8,
    delta: -0.27,
    gamma: 0.02,
    theta: 0.29,
    vega: 0.24,
    ivRank: 98,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x54abc...',
    optimalExit: true
  }
}, {
  id: '89',
  date: '2/20/2025',
  type: 'Call',
  strike: '615C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -900,
  details: {
    time: '14:55 EST',
    waitTime: 0.5,
    premium: 0.67,
    otmPercent: 4.5,
    delta: -0.33,
    gamma: 0.02,
    theta: 0.43,
    vega: 0.22,
    ivRank: 114,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x55def...',
    optimalExit: false
  }
}, {
  id: '90',
  date: '2/19/2025',
  type: 'Both',
  strike: '616C / 616P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 910,
  details: {
    time: '17:20 EST',
    waitTime: 4.9,
    premium: 0.15,
    otmPercent: 0.1,
    delta: 0.39,
    gamma: 0.04,
    theta: -0.32,
    vega: -0.05,
    ivRank: 40,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x56fed...',
    optimalExit: true
  }
}, {
  id: '91',
  date: '2/18/2025',
  type: 'Put',
  strike: '617P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -920,
  details: {
    time: '11:45 EST',
    waitTime: 3.7,
    premium: 0.62,
    otmPercent: 3.9,
    delta: -0.34,
    gamma: 0.02,
    theta: 0.44,
    vega: 0.27,
    ivRank: 105,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x57abc...',
    optimalExit: false
  }
}, {
  id: '92',
  date: '2/14/2025',
  type: 'Call',
  strike: '618C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 930,
  details: {
    time: '14:10 EST',
    waitTime: 5.5,
    premium: 0.17,
    otmPercent: 0.3,
    delta: 0.32,
    gamma: 0.03,
    theta: 0.00,
    vega: -0.04,
    ivRank: 45,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x58def...',
    optimalExit: true
  }
}, {
  id: '93',
  date: '2/13/2025',
  type: 'Both',
  strike: '619C / 619P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -940,
  details: {
    time: '16:35 EST',
    waitTime: 4.0,
    premium: 0.57,
    otmPercent: 4.4,
    delta: 0.37,
    gamma: 0.04,
    theta: -0.31,
    vega: 0.24,
    ivRank: 111,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x59fed...',
    optimalExit: false
  }
}, {
  id: '94',
  date: '2/12/2025',
  type: 'Put',
  strike: '620P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 950,
  details: {
    time: '09:00 EST',
    waitTime: 4.4,
    premium: 0.27,
    otmPercent: 0.7,
    delta: -0.28,
    gamma: 0.02,
    theta: 0.30,
    vega: 0.25,
    ivRank: 100,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x5aabc...',
    optimalExit: true
  }
}, {
  id: '95',
  date: '2/11/2025',
  type: 'Call',
  strike: '621C',
  risk: 'Moderate',
  volume: 2,
  result: 'Exercised',
  pnl: -960,
  details: {
    time: '11:25 EST',
    waitTime: 0.4,
    premium: 0.68,
    otmPercent: 4.6,
    delta: -0.34,
    gamma: 0.02,
    theta: 0.45,
    vega: 0.23,
    ivRank: 116,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x5bdef...',
    optimalExit: false
  }
}, {
  id: '96',
  date: '2/10/2025',
  type: 'Both',
  strike: '622C / 622P',
  risk: 'High',
  volume: 3,
  result: 'Expired',
  pnl: 970,
  details: {
    time: '13:50 EST',
    waitTime: 5.0,
    premium: 0.14,
    otmPercent: 0.0,
    delta: 0.40,
    gamma: 0.04,
    theta: -0.33,
    vega: -0.06,
    ivRank: 38,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x5cfed...',
    optimalExit: true
  }
}, {
  id: '97',
  date: '2/7/2025',
  type: 'Put',
  strike: '623P',
  risk: 'Low',
  volume: 1,
  result: 'Exercised',
  pnl: -980,
  details: {
    time: '16:15 EST',
    waitTime: 3.8,
    premium: 0.63,
    otmPercent: 4.0,
    delta: -0.35,
    gamma: 0.02,
    theta: 0.46,
    vega: 0.28,
    ivRank: 107,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x5dabc...',
    optimalExit: false
  }
}, {
  id: '98',
  date: '2/6/2025',
  type: 'Call',
  strike: '624C',
  risk: 'Moderate',
  volume: 2,
  result: 'Expired',
  pnl: 990,
  details: {
    time: '10:40 EST',
    waitTime: 5.6,
    premium: 0.16,
    otmPercent: 0.2,
    delta: 0.33,
    gamma: 0.03,
    theta: 0.01,
    vega: -0.05,
    ivRank: 43,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x5edef...',
    optimalExit: true
  }
}, {
  id: '99',
  date: '2/5/2025',
  type: 'Both',
  strike: '625C / 625P',
  risk: 'High',
  volume: 3,
  result: 'Exercised',
  pnl: -1000,
  details: {
    time: '13:05 EST',
    waitTime: 4.1,
    premium: 0.58,
    otmPercent: 4.5,
    delta: 0.38,
    gamma: 0.04,
    theta: -0.32,
    vega: 0.25,
    ivRank: 113,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x5ffed...',
    optimalExit: false
  }
}, {
  id: '100',
  date: '2/4/2025',
  type: 'Put',
  strike: '626P',
  risk: 'Low',
  volume: 1,
  result: 'Expired',
  pnl: 1010,
  details: {
    time: '15:30 EST',
    waitTime: 4.5,
    premium: 0.26,
    otmPercent: 0.6,
    delta: -0.29,
    gamma: 0.02,
    theta: 0.31,
    vega: 0.26,
    ivRank: 102,
    stopLossRatio: 3,
    takeProfitRatio: 0.5,
    blockchainTxId: '0x60abc...',
    optimalExit: true
  }
}];
