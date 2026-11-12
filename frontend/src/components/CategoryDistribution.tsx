"use client";

import React from "react";
import { PieChart, Layers } from "lucide-react";
import { CategoryBreakdownItem } from "@/types";

interface CategoryDistributionProps {
  categories: CategoryBreakdownItem[];
  totalExpenses: number;
}

const CATEGORY_COLORS = [
  "from-blue-500 to-indigo-600",
  "from-cyan-500 to-teal-600",
  "from-violet-500 to-purple-600",
  "from-amber-500 to-orange-600",
  "from-pink-500 to-rose-600",
  "from-emerald-500 to-green-600",
  "from-slate-500 to-slate-700",
];

export const CategoryDistribution: React.FC<CategoryDistributionProps> = ({
  categories,
  totalExpenses,
}) => {
  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <PieChart className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Expense Categorization</h3>
              <p className="text-xs text-slate-400">Exact proportional allocation of outflows</p>
            </div>
          </div>

          <span className="text-xs font-mono font-medium text-slate-300 bg-slate-800 px-2.5 py-1 rounded-md">
            Total: ${totalExpenses.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </span>
        </div>

        {categories.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500">
            No expense categories recorded for this period.
          </div>
        ) : (
          <div className="space-y-3.5 max-h-[300px] overflow-y-auto pr-1">
            {categories.map((cat, idx) => {
              const gradient = CATEGORY_COLORS[idx % CATEGORY_COLORS.length];
              return (
                <div key={cat.category} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">{cat.category}</span>
                    <div className="flex items-center gap-2 font-mono">
                      <span className="text-white font-bold">
                        ${cat.total_amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                      </span>
                      <span className="text-slate-400 text-[11px] w-12 text-right">
                        {cat.percentage_share}%
                      </span>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full bg-gradient-to-r ${gradient} transition-all duration-500`}
                      style={{ width: `${Math.min(100, Math.max(3, cat.percentage_share))}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-slate-800/60 text-[11px] text-slate-400 text-center flex items-center justify-center gap-1">
        <Layers className="h-3 w-3 text-indigo-400" />
        <span>Categorization auto-maps incoming invoices to treasury budget buckets.</span>
      </div>
    </div>
  );
};

