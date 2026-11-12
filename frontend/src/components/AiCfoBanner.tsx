"use client";

import React from "react";
import {
  Sparkles,
  Bot,
  TrendingUp,
  PieChart,
  DollarSign,
  Scale,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";

interface AiCfoBannerProps {
  onOpenChat: (initialPrompt?: string) => void;
  currency?: string;
}

const QUICK_QUESTIONS = [
  {
    icon: TrendingUp,
    label: "Monthly Performance",
    prompt: "How is my business performing this month?",
  },
  {
    icon: PieChart,
    label: "Biggest Expenses",
    prompt: "What are my biggest expenses?",
  },
  {
    icon: DollarSign,
    label: "Top Cost Vendor",
    prompt: "Which vendor costs me the most?",
  },
  {
    icon: Scale,
    label: "Period Comparison",
    prompt: "Compare this month with last month.",
  },
  {
    icon: DollarSign,
    label: "Affordability Check",
    prompt: "Can I afford a $15,000 payment?",
  },
  {
    icon: AlertTriangle,
    label: "Unusual Spending",
    prompt: "Identify unusual spending patterns.",
  },
];

export const AiCfoBanner: React.FC<AiCfoBannerProps> = ({
  onOpenChat,
  currency = "USD",
}) => {
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-cyan-950/40 border border-cyan-800/40 p-5 shadow-xl">
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        {/* Left: AI CFO Identity & Capabilities */}
        <div className="flex items-start space-x-3.5">
          <div className="p-3 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-500/20 flex-shrink-0">
            <Bot className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <h3 className="text-base font-bold text-white tracking-tight">
                AI CFO Financial Intelligence
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-950 text-cyan-400 border border-cyan-800 flex items-center space-x-1">
                <Sparkles className="w-2.5 h-2.5 animate-spin" />
                <span>Zero Hallucination</span>
              </span>
            </div>
            <p className="text-xs text-slate-300 max-w-xl">
              Ask natural language questions about your revenue ({currency}), runway, top vendors, or payment affordability.
              Guardian CFO analyzes your live ledger using structured tool calling.
            </p>
          </div>
        </div>

        {/* Right: Primary Chat Button */}
        <button
          onClick={() => onOpenChat()}
          className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold flex items-center space-x-2 shadow-lg shadow-cyan-600/20 transition flex-shrink-0"
        >
          <span>Consult AI CFO</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Bottom: Quick-Prompt Pills */}
      <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center gap-2 overflow-x-auto pb-1">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex-shrink-0 mr-1">
          Quick Questions:
        </span>
        {QUICK_QUESTIONS.map((q, idx) => {
          const Icon = q.icon;
          return (
            <button
              key={idx}
              onClick={() => onOpenChat(q.prompt)}
              className="px-3 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-800 border border-slate-700/80 hover:border-cyan-500/50 text-slate-300 hover:text-white text-xs font-medium flex items-center space-x-1.5 transition whitespace-nowrap group shadow-sm"
            >
              <Icon className="w-3 h-3 text-cyan-400 group-hover:scale-110 transition-transform" />
              <span>{q.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
