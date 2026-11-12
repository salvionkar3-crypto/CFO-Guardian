"use client";

import React from "react";
import { History, ShieldCheck, UserCheck, Bot, CheckCircle } from "lucide-react";
import { AuditLogItem } from "@/types";

interface AuditTimelineProps {
  logs: AuditLogItem[];
  selectedDecisionId: number | null;
  onClearFilter: () => void;
}

export const AuditTimeline: React.FC<AuditTimelineProps> = ({ logs, selectedDecisionId, onClearFilter }) => {
  const getActorBadge = (actor: string) => {
    switch (actor.toUpperCase()) {
      case "AI_CFO":
        return (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800">
            <Bot className="h-2.5 w-2.5" />
            AI CFO
          </span>
        );
      case "GUARDIAN_AI":
        return (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800">
            <ShieldCheck className="h-2.5 w-2.5" />
            Guardian AI
          </span>
        );
      case "PAYMENT_AGENT":
        return (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
            <CheckCircle className="h-2.5 w-2.5" />
            Payment Agent
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[10px] font-semibold text-slate-300 bg-slate-800 px-2 py-0.5 rounded">
            <UserCheck className="h-2.5 w-2.5" />
            {actor}
          </span>
        );
    }
  };

  const filteredLogs = selectedDecisionId
    ? logs.filter((l) => l.decision_id === selectedDecisionId)
    : logs;

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <History className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Explainability & Audit Ledger</h3>
            <p className="text-xs text-slate-400">
              {selectedDecisionId
                ? `Showing decision rationale & step trace for Decision #${selectedDecisionId}`
                : "Real-time immutable trace of all algorithmic and payment decisions"}
            </p>
          </div>
        </div>

        {selectedDecisionId && (
          <button
            onClick={onClearFilter}
            className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 transition"
          >
            Show All Events
          </button>
        )}
      </div>

      {filteredLogs.length === 0 ? (
        <div className="py-8 text-center text-xs text-slate-500">
          No audit entries recorded yet. Events will append live as invoices process.
        </div>
      ) : (
        <div className="space-y-3 max-h-[420px] overflow-y-auto pr-2">
          {filteredLogs.map((log) => (
            <div
              key={log.id}
              className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 hover:border-slate-700 transition"
            >
              <div className="flex items-center justify-between mb-1.5 flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {log.stage}
                  </span>
                  {getActorBadge(log.actor)}
                  {log.decision_id && (
                    <span className="text-[10px] font-mono text-slate-400">
                      #DEC-{log.decision_id}
                    </span>
                  )}
                </div>
                <span className="text-[10px] text-slate-400 font-mono">
                  {new Date(log.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
              </div>

              <div className="text-xs font-semibold text-white mb-1">
                {log.summary}
              </div>

              {log.rationale && (
                <div className="text-[11px] text-slate-400 bg-slate-900/90 rounded-lg p-2 border border-slate-800/50 mt-1.5">
                  <span className="font-semibold text-slate-300">Rationale: </span>
                  {log.rationale}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

