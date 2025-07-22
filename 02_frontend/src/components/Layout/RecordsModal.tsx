import React, { useState, useMemo } from 'react';
import { X, ChevronDown, ExternalLink, Brain, ChevronUp, Download, Search, Calendar as CalendarIcon, HelpCircle } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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
import { PerformanceContent } from './Performance/PerformanceContent';
import { SimpleReconciliationTable } from './History/SimpleReconciliationTable';

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
  const [totalPages, setTotalPages] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [sortBy, setSortBy] = useState('date');
  const [selectedTimeframe, setSelectedTimeframe] = useState('3M');
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
  
  // Reset page when filters change
  React.useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, filterType]);
  
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
                {activeTab === 'performance' && <PerformanceContent />}

                {activeTab === 'history' && <SimpleReconciliationTable />}

                {activeTab === 'withdrawals' && <WithdrawalTab availableBalance={2500} withdrawalHistory={sampleWithdrawals} availabilityBreakdown={availabilityBreakdown} />}

                {activeTab === 'analytics' && <AnalyticsTab />}
              </div>
            </ScrollArea>
          </div>
        </DialogContent>
      </Dialog>
    </TooltipProvider>;
};