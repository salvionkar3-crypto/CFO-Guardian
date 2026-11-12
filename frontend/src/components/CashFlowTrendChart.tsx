"use client";

import React from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { LineChart, BarChart2 } from "lucide-react";
import { TrendItem } from "@/types";

interface CashFlowTrendChartProps {
  trends: TrendItem[];
}

export const CashFlowTrendChart: React.FC<CashFlowTrendChartProps> = ({ trends }) => {
  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <BarChart2 className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Monthly Revenue, Expenses & Cash Flow</h3>
            <p className="text-xs text-slate-400">
              6-Month historical performance calculated directly from ledger transactions
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="flex items-center gap-1.5 text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2.5 py-1 rounded-md">
            <span className="h-2 w-2 rounded-full bg-emerald-400" /> Revenue
          </span>
          <span className="flex items-center gap-1.5 text-rose-400 bg-rose-950/60 border border-rose-800 px-2.5 py-1 rounded-md">
            <span className="h-2 w-2 rounded-full bg-rose-400" /> Expenses
          </span>
          <span className="flex items-center gap-1.5 text-cyan-400 bg-cyan-950/60 border border-cyan-800 px-2.5 py-1 rounded-md">
            <span className="h-2 w-2 rounded-full bg-cyan-400" /> Net Cash Flow
          </span>
        </div>
      </div>

      <div className="h-72 w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={trends} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis dataKey="label" stroke="#64748b" fontSize={11} tickLine={false} />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              tickFormatter={(val) => `$${val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#020617",
                border: "1px solid #1e293b",
                borderRadius: "0.75rem",
                fontSize: "12px",
                color: "#f8fafc",
              }}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(val: any, name: any) => [
                `$${Number(val || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
                name === "revenue" ? "Revenue" : name === "expenses" ? "Expenses" : "Net Cash Flow",
              ]}
            />
            <Bar dataKey="revenue" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={32} />
            <Bar dataKey="expenses" fill="#f43f5e" radius={[4, 4, 0, 0]} maxBarSize={32} />
            <Line
              type="monotone"
              dataKey="net_cash_flow"
              stroke="#06b6d4"
              strokeWidth={3}
              dot={{ r: 4, fill: "#06b6d4", stroke: "#0891b2" }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 text-[11px] text-slate-400 text-center flex items-center justify-center gap-1">
        <LineChart className="h-3 w-3 text-cyan-400" />
        <span>Net cash flow margin tracks sustained profitability across monthly billing cycles.</span>
      </div>
    </div>
  );
};

