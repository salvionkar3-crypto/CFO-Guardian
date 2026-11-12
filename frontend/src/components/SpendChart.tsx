"use client";

import React from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { BarChart3 } from "lucide-react";
import { CompanyMetrics } from "@/types";

interface SpendChartProps {
  metrics: CompanyMetrics | null;
}

export const SpendChart: React.FC<SpendChartProps> = ({ metrics }) => {
  const chartData = [
    { name: "Monthly Budget", amount: metrics?.monthly_budget || 35000, fill: "#3b82f6" },
    { name: "Spent to Date", amount: metrics?.monthly_spent || 16400, fill: "#06b6d4" },
    { name: "Remaining", amount: metrics?.budget_remaining || 18600, fill: "#10b981" },
    { name: "Est. Daily Burn", amount: (metrics?.burn_rate_daily || 1166) * 10, fill: "#8b5cf6" },
  ];

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <BarChart3 className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Treasury & Burn Analytics</h3>
              <p className="text-xs text-slate-400">Real-time liquidity and operational expenditure</p>
            </div>
          </div>
          <span className="text-xs font-mono font-medium text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded">
            Runway: {metrics?.runway_months || 0} Mo
          </span>
        </div>
      </div>

      <div className="h-64 w-full mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
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
              formatter={(val: any) => [`$${Number(val || 0).toLocaleString()}`, "Amount"]}
            />
            <Bar dataKey="amount" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 text-[11px] text-slate-400 text-center">
        Guardian AI continuously recalibrates treasury runway upon every approved payout.
      </div>
    </div>
  );
};
