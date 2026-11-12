"use client";

import React from "react";
import { TrendingUp, TrendingDown, DollarSign, Wallet, ArrowUpRight, ArrowDownRight, Calendar } from "lucide-react";
import { FinancialSummary } from "@/types";

interface FinancialSummaryCardsProps {
  summary: FinancialSummary | null;
  period: string;
  onPeriodChange: (newPeriod: string) => void;
}

export const FinancialSummaryCards: React.FC<FinancialSummaryCardsProps> = ({
  summary,
  period,
  onPeriodChange,
}) => {
  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return "$0.00";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
    }).format(val);
  };

  const isNetPositive = (summary?.net_cash_flow ?? 0) >= 0;
  const revGrowth = summary?.revenue_growth_pct ?? 0;
  const expChange = summary?.expense_change_pct ?? 0;

  return (
    <div className="space-y-4">
      {/* Header and Period Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span>Treasury & Cash Flow Condition</span>
            <span className="text-xs font-mono font-normal px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">
              Deterministic Python Engine
            </span>
          </h2>
          <p className="text-xs text-slate-400">
            Real-time ledger calculations with period-over-period growth comparisons
          </p>
        </div>

        {/* Period Selector Tabs */}
        <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 p-1 rounded-xl text-xs">
          <Calendar className="h-3.5 w-3.5 text-slate-400 ml-1.5 mr-0.5" />
          {[
            { key: "current_month", label: "This Month" },
            { key: "last_month", label: "Last Month" },
            { key: "last_3_months", label: "3 Months" },
            { key: "last_6_months", label: "6 Months" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => onPeriodChange(tab.key)}
              className={`px-2.5 py-1 rounded-lg font-medium transition ${
                period === tab.key
                  ? "bg-cyan-600 text-white shadow-sm font-semibold"
                  : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 4 Core Financial Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Total Revenue */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Revenue</span>
            <div className="h-8 w-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-white tracking-tight">
            {formatCurrency(summary?.total_revenue)}
          </div>
          <div className="mt-2 flex items-center justify-between text-xs">
            <div className={`flex items-center font-semibold ${revGrowth >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {revGrowth >= 0 ? <ArrowUpRight className="h-3.5 w-3.5 mr-0.5" /> : <ArrowDownRight className="h-3.5 w-3.5 mr-0.5" />}
              <span>{Math.abs(revGrowth)}% growth</span>
            </div>
            <span className="text-slate-500 text-[11px]">prev: {formatCurrency(summary?.previous_revenue)}</span>
          </div>
        </div>

        {/* 2. Total Expenses */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Expenses</span>
            <div className="h-8 w-8 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
              <TrendingDown className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-white tracking-tight">
            {formatCurrency(summary?.total_expenses)}
          </div>
          <div className="mt-2 flex items-center justify-between text-xs">
            <div className={`flex items-center font-semibold ${expChange <= 0 ? "text-emerald-400" : "text-amber-400"}`}>
              {expChange > 0 ? <ArrowUpRight className="h-3.5 w-3.5 mr-0.5" /> : <ArrowDownRight className="h-3.5 w-3.5 mr-0.5" />}
              <span>{expChange > 0 ? `+${expChange}%` : `${expChange}%`} change</span>
            </div>
            <span className="text-slate-500 text-[11px]">prev: {formatCurrency(summary?.previous_expenses)}</span>
          </div>
        </div>

        {/* 3. Net Cash Flow */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Net Cash Flow</span>
            <div className={`h-8 w-8 rounded-xl border flex items-center justify-center ${
              isNetPositive
                ? "bg-cyan-500/10 border-cyan-500/20 text-cyan-400"
                : "bg-rose-500/10 border-rose-500/20 text-rose-400"
            }`}>
              <DollarSign className="h-4 w-4" />
            </div>
          </div>
          <div className={`text-2xl font-extrabold tracking-tight ${isNetPositive ? "text-cyan-400" : "text-rose-400"}`}>
            {formatCurrency(summary?.net_cash_flow)}
          </div>
          <div className="mt-2 flex items-center justify-between text-xs">
            <span className="text-slate-300 font-medium">Margin: {summary?.cash_flow_margin_pct ?? 0}%</span>
            <span className="text-slate-500 text-[11px]">
              {summary && summary.net_cash_flow_change >= 0 ? `+$${summary.net_cash_flow_change}` : `-$${Math.abs(summary?.net_cash_flow_change ?? 0)}`}
            </span>
          </div>
        </div>

        {/* 4. Treasury & Runway */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Treasury Runway</span>
            <div className="h-8 w-8 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
              <Wallet className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-white tracking-tight">
            {summary?.runway_months ?? 0} <span className="text-sm font-normal text-slate-400">Months</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
            <span>Treasury: {formatCurrency(summary?.treasury_balance)}</span>
            <span className="text-violet-400 font-medium">{summary?.total_transactions ?? 0} txs</span>
          </div>
        </div>
      </div>
    </div>
  );
};

