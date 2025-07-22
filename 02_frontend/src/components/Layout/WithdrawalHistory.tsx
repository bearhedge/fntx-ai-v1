
import React, { useState } from 'react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Search, Download, ExternalLink } from 'lucide-react';
import { WithdrawalRecord } from '@/types/trading';
interface WithdrawalHistoryProps {
  withdrawals: WithdrawalRecord[];
}
export const WithdrawalHistory: React.FC<WithdrawalHistoryProps> = ({
  withdrawals
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const filteredWithdrawals = withdrawals.filter(withdrawal => withdrawal.date.toLowerCase().includes(searchTerm.toLowerCase()) || withdrawal.destination.toLowerCase().includes(searchTerm.toLowerCase()) || withdrawal.status.toLowerCase().includes(searchTerm.toLowerCase()));
  const handleExport = () => {
    console.log('Exporting withdrawal history...');
  };
  return <div className="space-y-4">
      <div className="flex items-center gap-4 justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input placeholder="Search..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="pl-10 font-normal" />
        </div>
        <Button variant="outline" onClick={handleExport} className="gap-2 font-normal">
          <Download className="w-4 h-4" />
          Export CSV
        </Button>
      </div>

      <div className="font-normal border rounded-lg overflow-hidden ">
        <Table>
          <TableHeader className="bg-gray-50">
            <TableRow>
              <TableHead className="w-24 font-normal">Date</TableHead>
              <TableHead className="w-32 text-right font-normal">Amount</TableHead>
              <TableHead className="font-normal">Destination</TableHead>
              <TableHead className="w-24 text-center font-normal">Status</TableHead>
              <TableHead className="w-20 text-center font-normal">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredWithdrawals.map((withdrawal, index) => <TableRow key={withdrawal.id} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-25'}>
                <TableCell className="font-normal text-sm">{withdrawal.date}</TableCell>
                <TableCell className="text-right font-normal">
                  ${withdrawal.amount.toLocaleString()}
                </TableCell>
                <TableCell className="text-sm font-normal">{withdrawal.destination}</TableCell>
                <TableCell className="text-center">
                  <span className="px-2 py-1 rounded-full text-xs font-normal bg-gray-100 text-gray-900">
                    {withdrawal.status}
                  </span>
                </TableCell>
                <TableCell className="text-center">
                  <Button variant="ghost" size="sm" className="w-8 h-8 p-0" onClick={() => console.log('View details:', withdrawal.id)}>
                    <ExternalLink className="w-4 h-4" />
                  </Button>
                </TableCell>
              </TableRow>)}
          </TableBody>
        </Table>
      </div>

      {filteredWithdrawals.length === 0 && <div className="text-center py-8 text-gray-500">
          <p className="font-normal">No withdrawals found</p>
        </div>}
    </div>;
};
