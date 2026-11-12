"use client";

import React from "react";
import { Repeat, CalendarClock } from "lucide-react";
import { RecurringExpensesResponse } from "@/types";

interface RecurringExpensesCardProps {
  recurring: RecurringExpensesResponse | null;
}

export const RecurringExpensesCard: React.FC<RecurringExpensesCardProps> = ({ recurring }) => {
  const items = recurring?.items ?? [];
  const totalMonthly = recurring?.total_recurring_monthly ?? 0;
  const totalAnnual = recurring?.total_recurring_annual ?? 0;

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400">
              <Repeat className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Recurring Vendor Subscriptions</h3>
              <p className="text-xs text-slate-400">Automated recurring obligations identified by pattern & frequency</p>
            </div>
          </div>

          <div className="text-right">
            <div className="text-sm font-extrabold font-mono text-teal-400">
              ${totalMonthly.toLocaleString("en-US", { minimumFractionDigits: 2 })}/mo
            </div>
            <div className="text-[10px] text-slate-400 font-mono">
              ${totalAnnual.toLocaleString("en-US", { minimumFractionDigits: 2 })}/yr committed
            </div>
          </div>
        </div>

        {items.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500">
            No recurring vendor commitments detected yet.
          </div>
        ) : (
          <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
            {items.map((item, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 hover:border-slate-700 transition flex items-center justify-between gap-3"
              >
                <div>
                  <div className="text-xs font-semibold text-white">{item.vendor_name}</div>
                  <div className="text-[10px] text-slate-400 flex items-center gap-2 mt-0.5">
                    <span className="font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/60 px-1.5 py-0.2 rounded">
                      {item.category}
                    </span>
                    <span>• {item.frequency}</span>
                    {item.last_paid_date && (
                      <span>• Last: {item.last_paid_date}</span>
                    )}
                  </div>
                </div>

                <div className="text-right font-mono">
                  <div className="text-xs font-bold text-white">
                    ${item.amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    ${item.annualized_amount.toLocaleString("en-US", { minimumFractionDigits: 0 })}/yr
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-slate-800/60 text-[11px] text-slate-400 text-center flex items-center justify-center gap-1">
        <CalendarClock className="h-3 w-3 text-teal-400" />
        <span>Guardian AI monitors recurring obligations to prevent unapproved price hikes.</span>
      </div>
    </div>
  );
};

