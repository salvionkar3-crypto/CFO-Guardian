"use client";

import React from "react";
import { DollarSign, Flame, Clock, ShieldCheck } from "lucide-react";
import { CompanyMetrics } from "@/types";

interface MetricCardsProps {
  metrics: CompanyMetrics | null;
}

export const MetricCards: React.FC<MetricCardsProps> = ({ metrics }) => {
  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return "$0.00";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(val);
  };

  const remainingBudget = metrics?.budget_remaining ?? 0;
  const monthlyBudget = metrics?.monthly_budget ?? 35000;
  const budgetSpentPct = monthlyBudget > 0 ? Math.round(((monthlyBudget - remainingBudget) / monthlyBudget) * 100) : 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Total Treasury Balance */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Company Treasury</span>
          <div className="h-9 w-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <DollarSign className="h-5 w-5" />
          </div>
        </div>
        <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          {formatCurrency(metrics?.total_balance)}
        </div>
        <div className="mt-2 flex items-center text-xs text-emerald-400 font-medium">
          <span>Operating Currency: {metrics?.operating_currency || "USD"}</span>
        </div>
      </div>

      {/* Monthly Budget & Burn */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Monthly Budget</span>
          <div className="h-9 w-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <Flame className="h-5 w-5" />
          </div>
        </div>
        <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          {formatCurrency(remainingBudget)}
          <span className="text-xs font-normal text-slate-400 ml-1.5">left</span>
        </div>
        <div className="mt-2 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full rounded-full ${
              budgetSpentPct > 85 ? "bg-rose-500" : budgetSpentPct > 60 ? "bg-amber-500" : "bg-cyan-500"
            }`}
            style={{ width: `${Math.min(100, budgetSpentPct)}%` }}
          />
        </div>
        <div className="mt-1.5 flex justify-between text-[11px] text-slate-400">
          <span>{budgetSpentPct}% utilized</span>
          <span>Budget: {formatCurrency(metrics?.monthly_budget)}</span>
        </div>
      </div>

      {/* Runway Months */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Financial Runway</span>
          <div className="h-9 w-9 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
            <Clock className="h-5 w-5" />
          </div>
        </div>
        <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          {metrics?.runway_months ?? 0}{" "}
          <span className="text-sm font-normal text-slate-400">Months</span>
        </div>
        <div className="mt-2 flex items-center text-xs text-violet-400 font-medium">
          <span>Daily Burn: {formatCurrency(metrics?.burn_rate_daily)}/day</span>
        </div>
      </div>

      {/* Guardian Shield Status */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Guardian Risk AI</span>
          <div className="h-9 w-9 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
            <ShieldCheck className="h-5 w-5" />
          </div>
        </div>
        <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400 tracking-tight flex items-center gap-2">
          <span>Active</span>
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </span>
        </div>
        <div className="mt-2 text-xs text-slate-400 font-medium truncate">
          Duplicate & Velocity Filters Armed
        </div>
      </div>
    </div>
  );
};

