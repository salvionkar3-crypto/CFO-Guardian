"use client";

import React from "react";
import { AlertTriangle, ArrowUpRight } from "lucide-react";
import { ExpenseAnomaly } from "@/types";

interface ExpenseAnomaliesBannerProps {
  anomalies: ExpenseAnomaly[];
}

export const ExpenseAnomaliesBanner: React.FC<ExpenseAnomaliesBannerProps> = ({ anomalies }) => {
  if (anomalies.length === 0) return null;

  return (
    <div className="bg-slate-900/90 border border-amber-900/50 rounded-2xl p-5 shadow-xl relative overflow-hidden">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Unusual Expense Increase Alerts</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-950 text-amber-400 border border-amber-800">
                {anomalies.length} Detected
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Deterministic surge detection flagged abnormal outflow spikes compared to previous period
            </p>
          </div>
        </div>

        <span className="text-xs text-amber-400 font-mono font-medium hidden sm:inline-block">
          Guardian AI Anomaly Guard
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
        {anomalies.map((anomaly, idx) => (
          <div
            key={idx}
            className="p-3.5 rounded-xl bg-slate-950/80 border border-amber-800/40 hover:border-amber-700/60 transition flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold text-white">{anomaly.category}</span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-semibold flex items-center gap-1 ${
                    anomaly.severity === "CRITICAL"
                      ? "bg-rose-950 text-rose-400 border border-rose-800"
                      : "bg-amber-950 text-amber-400 border border-amber-800"
                  }`}
                >
                  <ArrowUpRight className="h-3 w-3" />
                  +{anomaly.increase_pct}% Spike
                </span>
              </div>

              <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">
                {anomaly.reason}
              </p>
            </div>

            <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span>Current: ${anomaly.current_amount.toLocaleString()}</span>
              <span>Previous: ${anomaly.previous_amount.toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

