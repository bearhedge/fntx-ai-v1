import React, { useEffect, useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

// Update this type to match your backend fields.
type Trade = {
  id: number;
  symbol: string;
  strike: number;
  premium: number;
  expiry: string;
  type: string; // "put" or "call"
  timestamp?: string;
  volume?: number;
};

type GroupedRow = {
  id: number;
  symbol: string;
  strikes: string;
  premiums: string;
  expiry: string;
  timestamp: string;
  volume: string;
};

export const TradesList: React.FC = () => {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/trades")
      .then((res) => res.json())
      .then((data) => {
        setTrades(data);
        setLoading(false);
      });
  }, []);

  // Group both trades into a single row by expiry
  let groupedRow: GroupedRow | null = null;

  if (trades.length > 0) {
    const put = trades.find(t => t.type === "put");
    const call = trades.find(t => t.type === "call");
    groupedRow = {
      id: 1,
      symbol: trades[0].symbol,
      strikes: `${put ? put.strike + "P" : ""} ${call ? call.strike + "C" : ""}`.trim(),
      premiums: `${put ? put.premium + "(P)" : ""} ${call ? call.premium + "(C)" : ""}`.trim(),
      expiry: trades[0].expiry,
      timestamp: put?.timestamp || call?.timestamp || "-",
      volume: `${put && put.volume !== undefined ? put.volume + "(P)" : "-"} ${call && call.volume !== undefined ? call.volume + "(C)" : "-"}`.trim(),
    };
  }

  if (loading) return <div>Loading trades...</div>;

  return (
    <div>
      <h2 className="text-xl font-bold mb-2">Trades</h2>
      <Table className="w-full">
        <TableHeader>
          <TableRow className="bg-gray-700 no-header-hover">
            <TableHead className="text-center text-white font-bold">ID</TableHead>
            <TableHead className="text-center text-white font-bold">Symbol</TableHead>
            <TableHead className="text-center text-white font-bold">Strikes</TableHead>
            <TableHead className="text-center text-white font-bold">Premiums</TableHead>
            <TableHead className="text-center text-white font-bold">Volume</TableHead>
            <TableHead className="text-center text-white font-bold">Timestamp</TableHead>
            <TableHead className="text-center text-white font-bold">Expiry</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {groupedRow && (
            <TableRow className="bg-white text-black">
              <TableCell className="text-center">{groupedRow.id}</TableCell>
              <TableCell className="text-center">{groupedRow.symbol}</TableCell>
              <TableCell className="text-center">{groupedRow.strikes}</TableCell>
              <TableCell className="text-center">{groupedRow.premiums}</TableCell>
              <TableCell className="text-center">{groupedRow.volume}</TableCell>
              <TableCell className="text-center">
                {groupedRow.timestamp !== "-" ? new Date(groupedRow.timestamp).toLocaleString() : "-"}
              </TableCell>
              <TableCell className="text-center">{groupedRow.expiry}</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
};