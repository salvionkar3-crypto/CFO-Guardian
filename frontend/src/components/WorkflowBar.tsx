"use client";

import React from "react";
import {
  Brain,
  BarChart3,
  SearchCheck,
  CheckCircle2,
  ThumbsUp,
  CreditCard,
  LineChart,
  FileText,
} from "lucide-react";

interface WorkflowBarProps {
  currentStage?: string;
}

const STAGES = [
  {
    key: "UNDERSTAND",
    label: "1. Understand",
    subtext: "Ingest & Context",
    icon: Brain,
    color: "from-blue-500 to-indigo-600",
  },
  {
    key: "ANALYZE",
    label: "2. Analyze",
    subtext: "Budget & Runway",
    icon: BarChart3,
    color: "from-indigo-500 to-violet-600",
  },
  {
    key: "INVESTIGATE",
    label: "3. Investigate",
    subtext: "Guardian AI Scan",
    icon: SearchCheck,
    color: "from-violet-500 to-purple-600",
  },
  {
    key: "DECIDE",
    label: "4. Decide",
    subtext: "Risk Scoring",
    icon: CheckCircle2,
    color: "from-purple-500 to-pink-600",
  },
  {
    key: "APPROVE",
    label: "5. Approve",
    subtext: "Dual Authorization",
    icon: ThumbsUp,
    color: "from-pink-500 to-rose-600",
  },
  {
    key: "PAY",
    label: "6. Pay",
    subtext: "PayPal REST Agent",
    icon: CreditCard,
    color: "from-cyan-500 to-blue-600",
  },
  {
    key: "MONITOR",
    label: "7. Monitor",
    subtext: "Settlement Audit",
    icon: LineChart,
    color: "from-emerald-500 to-teal-600",
  },
  {
    key: "EXPLAIN",
    label: "8. Explain",
    subtext: "Audit Trail & Why",
    icon: FileText,
    color: "from-amber-500 to-yellow-600",
  },
];

export const WorkflowBar: React.FC<WorkflowBarProps> = ({ currentStage }) => {
  return (
    <div className="w-full bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl">
      <div className="flex items-center justify-between mb-3 px-1">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">
            Autonomous Financial Execution Pipeline
          </h3>
          <p className="text-xs text-slate-400">
            Every transaction rigorously completes all 8 checkpoints before money leaves the bank.
          </p>
        </div>
        <span className="text-xs font-mono font-medium px-2.5 py-1 rounded-md bg-cyan-950 text-cyan-400 border border-cyan-800">
          Zero-Trust Guardrails
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
        {STAGES.map((stage) => {
          const Icon = stage.icon;
          const isHighlighted = currentStage ? currentStage.toUpperCase() === stage.key : false;

          return (
            <div
              key={stage.key}
              className={`relative rounded-xl p-3 border transition-all duration-200 ${
                isHighlighted
                  ? "bg-slate-800/90 border-cyan-500 shadow-md shadow-cyan-500/20 scale-[1.02]"
                  : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <div
                  className={`h-7 w-7 rounded-lg flex items-center justify-center bg-gradient-to-br ${stage.color} text-white shadow-sm`}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <span className="text-[11px] font-bold text-slate-200">{stage.label}</span>
              </div>
              <p className="text-[10px] text-slate-400 font-medium pl-1 truncate">
                {stage.subtext}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
