"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Search,
  Filter,
  RefreshCw,
  UserCheck,
  Bot,
  CheckCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Clock,
  Layers,
  Webhook,
  Activity,
  Copy,
  Check,
  Key,
  Eye,
  SlidersHorizontal,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  AuditLogItem,
  ExplainabilityReport,
  WebhookEventItem,
} from "@/types";

interface SecurityActivityProps {
  initialDecisionId?: number | null;
  onSelectDraft?: (draftId: number) => void;
}

const STAGES = [
  "ALL",
  "UNDERSTAND",
  "ANALYZE",
  "INVESTIGATE",
  "DECIDE",
  "APPROVE",
  "PAY",
  "MONITOR",
  "EXPLAIN",
];

const ACTORS = [
  "ALL",
  "USER",
  "AI_CFO",
  "GUARDIAN_AI",
  "PAYMENT_AGENT",
  "SYSTEM",
];

export const SecurityActivity: React.FC<SecurityActivityProps> = ({
  initialDecisionId,
  onSelectDraft,
}) => {
  const [activeTab, setActiveTab] = useState<"audit" | "explain" | "webhooks">("audit");

  // Audit Logs State
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [isLoadingLogs, setIsLoadingLogs] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStage, setSelectedStage] = useState("ALL");
  const [selectedActor, setSelectedActor] = useState("ALL");
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null);

  // Explainability Inspector State
  const [explainDecisionId, setExplainDecisionId] = useState<string>(
    initialDecisionId ? String(initialDecisionId) : ""
  );
  const [explainReport, setExplainReport] = useState<ExplainabilityReport | null>(null);
  const [isLoadingExplain, setIsLoadingExplain] = useState(false);
  const [explainError, setExplainError] = useState<string | null>(null);

  // Webhooks State
  const [webhookEvents, setWebhookEvents] = useState<WebhookEventItem[]>([]);
  const [isLoadingWebhooks, setIsLoadingWebhooks] = useState(false);
  const [webhookStatusFilter, setWebhookStatusFilter] = useState<string>("ALL");
  const [expandedWebhookId, setExpandedWebhookId] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  // Fetch Audit Logs
  const fetchAuditLogs = useCallback(async () => {
    setIsLoadingLogs(true);
    try {
      const data = await api.getAuditLogs({
        search: searchQuery || undefined,
        stage: selectedStage !== "ALL" ? selectedStage : undefined,
        actor: selectedActor !== "ALL" ? selectedActor : undefined,
        limit: 100,
      });
      setLogs(data);
    } catch (err) {
      console.error("Failed to load audit logs:", err);
    } finally {
      setIsLoadingLogs(false);
    }
  }, [searchQuery, selectedStage, selectedActor]);

  // Fetch Explainability
  const loadExplainability = useCallback(async (id: number) => {
    setIsLoadingExplain(true);
    setExplainError(null);
    try {
      const rep = await api.explainDecision(id);
      setExplainReport(rep);
      setActiveTab("explain");
      setExplainDecisionId(String(id));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load explainability report";
      setExplainError(msg);
      setExplainReport(null);
    } finally {
      setIsLoadingExplain(false);
    }
  }, []);

  // Fetch Webhook Events
  const fetchWebhookEvents = useCallback(async () => {
    setIsLoadingWebhooks(true);
    try {
      const statusParam = webhookStatusFilter !== "ALL" ? webhookStatusFilter : undefined;
      const data = await api.getWebhookEvents(statusParam, 50);
      setWebhookEvents(data);
    } catch (err) {
      console.error("Failed to load webhook events:", err);
    } finally {
      setIsLoadingWebhooks(false);
    }
  }, [webhookStatusFilter]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  useEffect(() => {
    if (activeTab === "webhooks") {
      fetchWebhookEvents();
    }
  }, [activeTab, fetchWebhookEvents]);

  useEffect(() => {
    if (initialDecisionId) {
      loadExplainability(initialDecisionId);
    }
  }, [initialDecisionId, loadExplainability]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAuditLogs();
  };

  const copyToClipboard = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getActorBadge = (actor: string) => {
    switch (actor.toUpperCase()) {
      case "AI_CFO":
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-400 bg-indigo-950/70 px-2 py-0.5 rounded border border-indigo-800/80">
            <Bot className="h-3 w-3" />
            AI CFO
          </span>
        );
      case "GUARDIAN_AI":
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 bg-rose-950/70 px-2 py-0.5 rounded border border-rose-800/80">
            <ShieldAlert className="h-3 w-3" />
            Guardian AI
          </span>
        );
      case "PAYMENT_AGENT":
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-cyan-400 bg-cyan-950/70 px-2 py-0.5 rounded border border-cyan-800/80">
            <CheckCircle className="h-3 w-3" />
            Payment Agent
          </span>
        );
      case "SYSTEM":
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400 bg-amber-950/70 px-2 py-0.5 rounded border border-amber-800/80">
            <SlidersHorizontal className="h-3 w-3" />
            System
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-300 bg-slate-800/90 px-2 py-0.5 rounded border border-slate-700">
            <UserCheck className="h-3 w-3" />
            {actor}
          </span>
        );
    }
  };

  const getStageBadge = (stage: string) => {
    const stageColors: Record<string, string> = {
      UNDERSTAND: "text-blue-400 bg-blue-950/60 border-blue-800",
      ANALYZE: "text-purple-400 bg-purple-950/60 border-purple-800",
      INVESTIGATE: "text-amber-400 bg-amber-950/60 border-amber-800",
      DECIDE: "text-orange-400 bg-orange-950/60 border-orange-800",
      APPROVE: "text-emerald-400 bg-emerald-950/60 border-emerald-800",
      PAY: "text-cyan-400 bg-cyan-950/60 border-cyan-800",
      MONITOR: "text-teal-400 bg-teal-950/60 border-teal-800",
      EXPLAIN: "text-pink-400 bg-pink-950/60 border-pink-800",
    };
    const cls = stageColors[stage.toUpperCase()] || "text-slate-400 bg-slate-800 border-slate-700";
    return (
      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${cls}`}>
        {stage}
      </span>
    );
  };

  const violationCount = logs.filter(
    (l) => l.action === "POLICY_VIOLATION" || l.stage === "INVESTIGATE"
  ).length;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/60 to-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                Security Activity & Explainability Center
              </h2>
            </div>
            <p className="text-sm text-slate-400">
              Immutable 8-stage audit ledger, transparent 6-question reasoning engine, and verified PayPal webhooks.
            </p>
          </div>

          {/* Quick Metrics */}
          <div className="flex items-center gap-3">
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-center">
              <div className="text-[10px] font-mono uppercase text-slate-400">Total Logs</div>
              <div className="text-lg font-bold text-indigo-300">{logs.length}</div>
            </div>
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-center">
              <div className="text-[10px] font-mono uppercase text-slate-400">Security Events</div>
              <div className="text-lg font-bold text-rose-400">{violationCount}</div>
            </div>
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-center">
              <div className="text-[10px] font-mono uppercase text-slate-400">Webhooks</div>
              <div className="text-lg font-bold text-cyan-400">{webhookEvents.length}</div>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 mt-6 pt-4 border-t border-slate-800/80">
          <button
            onClick={() => setActiveTab("audit")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeTab === "audit"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
                : "bg-slate-800/80 hover:bg-slate-800 text-slate-300"
            }`}
          >
            <Activity className="h-3.5 w-3.5" />
            Audit Ledger Timeline
          </button>
          <button
            onClick={() => setActiveTab("explain")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeTab === "explain"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
                : "bg-slate-800/80 hover:bg-slate-800 text-slate-300"
            }`}
          >
            <Eye className="h-3.5 w-3.5" />
            6-Question Explainability Inspector
          </button>
          <button
            onClick={() => setActiveTab("webhooks")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
              activeTab === "webhooks"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
                : "bg-slate-800/80 hover:bg-slate-800 text-slate-300"
            }`}
          >
            <Webhook className="h-3.5 w-3.5" />
            PayPal Webhooks Stream
          </button>
        </div>
      </div>

      {/* TAB 1: AUDIT TIMELINE */}
      {activeTab === "audit" && (
        <div className="space-y-4">
          {/* Filter Controls Bar */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl space-y-3">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              {/* Search Form */}
              <form onSubmit={handleSearchSubmit} className="relative flex-1">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search logs by keyword, action (e.g. POLICY_VIOLATION), or rationale..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </form>

              <div className="flex items-center gap-2">
                <button
                  onClick={fetchAuditLogs}
                  disabled={isLoadingLogs}
                  className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold transition"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${isLoadingLogs ? "animate-spin" : ""}`} />
                  Refresh
                </button>
              </div>
            </div>

            {/* Stage Filter Pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
              <span className="text-[11px] text-slate-500 font-mono mr-1 flex items-center gap-1">
                <Layers className="h-3 w-3" /> Stage:
              </span>
              {STAGES.map((st) => (
                <button
                  key={st}
                  onClick={() => setSelectedStage(st)}
                  className={`px-2.5 py-1 rounded-lg font-mono text-[11px] transition ${
                    selectedStage === st
                      ? "bg-indigo-600 text-white font-bold"
                      : "bg-slate-950 hover:bg-slate-800 text-slate-400 border border-slate-800/80"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            {/* Actor Filter Pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
              <span className="text-[11px] text-slate-500 font-mono mr-1 flex items-center gap-1">
                <Filter className="h-3 w-3" /> Actor:
              </span>
              {ACTORS.map((ac) => (
                <button
                  key={ac}
                  onClick={() => setSelectedActor(ac)}
                  className={`px-2.5 py-1 rounded-lg font-mono text-[11px] transition ${
                    selectedActor === ac
                      ? "bg-indigo-600 text-white font-bold"
                      : "bg-slate-950 hover:bg-slate-800 text-slate-400 border border-slate-800/80"
                  }`}
                >
                  {ac}
                </button>
              ))}
            </div>
          </div>

          {/* Audit Logs List */}
          {isLoadingLogs ? (
            <div className="py-16 text-center text-xs text-slate-400 bg-slate-900/50 border border-slate-800 rounded-2xl">
              <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-indigo-400" />
              Loading immutable audit ledger entries...
            </div>
          ) : logs.length === 0 ? (
            <div className="py-16 text-center text-xs text-slate-500 bg-slate-900/50 border border-slate-800 rounded-2xl">
              No audit logs matched your query. Try clearing filters or creating a payment draft.
            </div>
          ) : (
            <div className="space-y-2.5">
              {logs.map((log) => {
                const isExpanded = expandedLogId === log.id;
                const isViolation = log.action === "POLICY_VIOLATION";

                return (
                  <div
                    key={log.id}
                    className={`rounded-2xl border transition overflow-hidden ${
                      isViolation
                        ? "bg-rose-950/20 border-rose-900/60 hover:border-rose-700"
                        : "bg-slate-900/90 border-slate-800/90 hover:border-slate-700"
                    }`}
                  >
                    <div
                      onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                      className="p-4 flex items-center justify-between cursor-pointer gap-3"
                    >
                      <div className="flex items-center gap-2.5 flex-wrap">
                        {getStageBadge(log.stage)}
                        {getActorBadge(log.actor)}
                        <span className="text-xs font-mono font-bold text-white">
                          {log.action}
                        </span>
                        {log.decision_id && (
                          <span className="text-[10px] font-mono text-indigo-300 bg-indigo-950/70 border border-indigo-800/80 px-2 py-0.5 rounded">
                            Draft #{log.decision_id}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
                          {new Date(log.timestamp).toLocaleString([], {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </span>
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-slate-400" />
                        )}
                      </div>
                    </div>

                    <div className="px-4 pb-3">
                      <p className="text-xs font-medium text-slate-200">
                        {log.summary}
                      </p>
                    </div>

                    {isExpanded && (
                      <div className="px-4 pb-4 pt-2 border-t border-slate-800/80 bg-slate-950/70 space-y-3">
                        {log.rationale && (
                          <div className="text-xs text-slate-300 bg-slate-900/80 p-3 rounded-xl border border-slate-800">
                            <span className="font-bold text-indigo-400">Explainability Rationale: </span>
                            {log.rationale}
                          </div>
                        )}

                        {log.details && (
                          <div className="text-xs text-slate-400 font-mono bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/60 break-all">
                            <span className="font-bold text-slate-300">Details: </span>
                            {log.details}
                          </div>
                        )}

                        <div className="flex items-center justify-between pt-1 text-[11px] text-slate-500">
                          <span className="font-mono">
                            Event ID: #{log.id} {log.ip_address ? `| IP: ${log.ip_address}` : ""}
                          </span>
                          {log.decision_id && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                if (log.decision_id) loadExplainability(log.decision_id);
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-700/60 rounded-lg text-xs font-semibold transition"
                            >
                              <Eye className="h-3 w-3" />
                              Inspect 6 Questions for #{log.decision_id}
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: 6-QUESTION EXPLAINABILITY INSPECTOR */}
      {activeTab === "explain" && (
        <div className="space-y-6">
          {/* Search/Input bar for Decision ID */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl">
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  Enter Payment Draft / Decision ID to inspect:
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    placeholder="e.g. 101, 102..."
                    value={explainDecisionId}
                    onChange={(e) => setExplainDecisionId(e.target.value)}
                    className="w-48 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                  <button
                    onClick={() => {
                      const idNum = parseInt(explainDecisionId, 10);
                      if (!isNaN(idNum)) loadExplainability(idNum);
                    }}
                    disabled={isLoadingExplain || !explainDecisionId}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    Inspect Explainability
                  </button>
                </div>
              </div>
            </div>

            {explainError && (
              <div className="mt-3 p-3 rounded-xl bg-rose-950/40 border border-rose-900/60 text-xs text-rose-300 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
                {explainError}
              </div>
            )}
          </div>

          {/* Explainability Report Card */}
          {isLoadingExplain ? (
            <div className="py-20 text-center text-xs text-slate-400 bg-slate-900/50 border border-slate-800 rounded-2xl">
              <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-indigo-400" />
              Loading transparent 6-question reasoning report...
            </div>
          ) : explainReport ? (
            <div className="space-y-4">
              {/* Report Header */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                      DECISION #{explainReport.decision_id}
                    </span>
                    <h3 className="text-lg font-bold text-white">
                      {explainReport.title}
                    </h3>
                  </div>
                  <p className="text-xs text-slate-400">
                    Payee: <span className="font-semibold text-slate-200">{explainReport.vendor}</span> | Status:{" "}
                    <span className="font-mono text-cyan-400 font-bold">{explainReport.current_status}</span>
                  </p>
                </div>

                <div className="text-right">
                  <div className="text-2xl font-black text-white tracking-tight">
                    {explainReport.currency} {explainReport.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                  <div className="text-[11px] text-slate-400">Authorized Treasury Currency</div>
                  {onSelectDraft && (
                    <button
                      onClick={() => onSelectDraft(explainReport.decision_id)}
                      className="mt-2 text-xs font-semibold px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 ml-auto inline-flex items-center gap-1"
                    >
                      Open in Payment Center
                    </button>
                  )}
                </div>
              </div>

              {/* The 6 Core Question Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 1. What Happened? */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold font-mono text-indigo-400">
                    <Clock className="h-4 w-4" />
                    1. WHAT HAPPENED?
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {explainReport.what_happened}
                  </p>
                </div>

                {/* 2. Why was it flagged? */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold font-mono text-amber-400">
                    <AlertTriangle className="h-4 w-4" />
                    2. WHY WAS IT FLAGGED?
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {explainReport.why_flagged}
                  </p>
                </div>

                {/* 3. What evidence was detected? */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold font-mono text-rose-400">
                    <ShieldAlert className="h-4 w-4" />
                    3. WHAT EVIDENCE WAS DETECTED?
                  </div>
                  {explainReport.evidence_detected && explainReport.evidence_detected.length > 0 ? (
                    <div className="space-y-1.5 pt-1">
                      {explainReport.evidence_detected.map((ev, idx) => (
                        <div
                          key={idx}
                          className="text-[11px] text-slate-300 bg-slate-950/70 border border-slate-800 rounded-lg px-2.5 py-1.5 flex items-center gap-2"
                        >
                          <span className="h-1.5 w-1.5 rounded-full bg-rose-400 shrink-0" />
                          <span>{ev}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">No adverse risk signals triggered.</p>
                  )}
                </div>

                {/* 4. What action was taken? */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold font-mono text-cyan-400">
                    <CheckCircle className="h-4 w-4" />
                    4. WHAT ACTION WAS TAKEN?
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-200 font-medium">
                    {explainReport.action_taken}
                  </div>
                  {explainReport.cfo_reasoning && (
                    <div className="text-[11px] text-slate-400 italic">
                      CFO Rationalization: &ldquo;{explainReport.cfo_reasoning}&rdquo;
                    </div>
                  )}
                </div>

                {/* 5. Who approved or rejected it? */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold font-mono text-emerald-400">
                      <UserCheck className="h-4 w-4" />
                      5. WHO APPROVED OR REJECTED IT?
                    </div>
                    {explainReport.approval_details?.requires_dual_approval && (
                      <span className="text-[10px] font-mono text-amber-300 bg-amber-950/70 border border-amber-800 px-2 py-0.5 rounded">
                        Dual-Control Required
                      </span>
                    )}
                  </div>

                  {explainReport.approval_details?.approvers &&
                  explainReport.approval_details.approvers.length > 0 ? (
                    <div className="space-y-2">
                      {explainReport.approval_details.approvers.map((ap) => (
                        <div
                          key={ap.step}
                          className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs flex items-center justify-between"
                        >
                          <div>
                            <div className="font-bold text-white flex items-center gap-1.5">
                              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                                Signer {ap.step}
                              </span>
                              {ap.name}
                            </div>
                            <div className="text-[11px] text-slate-400">{ap.email || ap.role}</div>
                            {ap.notes && (
                              <div className="text-[11px] text-slate-300 italic mt-0.5">
                                &ldquo;{ap.notes}&rdquo;
                              </div>
                            )}
                          </div>
                          <span className="text-[10px] font-mono text-slate-500">
                            {new Date(ap.approved_at).toLocaleDateString([], {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : explainReport.approval_details?.rejected_by ? (
                    <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-900 text-xs text-rose-300">
                      <div className="font-bold text-rose-200">
                        Rejected by: {explainReport.approval_details.rejected_by.name}
                      </div>
                      <div className="mt-1">
                        Reason: {explainReport.approval_details.rejected_by.reason}
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-slate-500 py-2">
                      Pending executive authorization. No sign-off recorded yet.
                    </div>
                  )}
                </div>

                {/* 6. What is the final provider status? */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold font-mono text-blue-400">
                      <Key className="h-4 w-4" />
                      6. FINAL PROVIDER STATUS
                    </div>
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
                      {explainReport.final_provider_status?.mode || "SANDBOX"} MODE
                    </span>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Payment Gateway:</span>
                      <span className="font-semibold text-white">
                        {explainReport.final_provider_status?.provider}
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Settlement State:</span>
                      <span className="font-mono font-bold text-cyan-400">
                        {explainReport.final_provider_status?.status}
                      </span>
                    </div>

                    {explainReport.final_provider_status?.order_id && (
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">PayPal Order ID:</span>
                        <span className="font-mono text-indigo-300">
                          {explainReport.final_provider_status.order_id}
                        </span>
                      </div>
                    )}

                    {explainReport.final_provider_status?.capture_id && (
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400">PayPal Capture ID:</span>
                        <span className="font-mono text-emerald-300">
                          {explainReport.final_provider_status.capture_id}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Immutable Decision Audit Trail */}
              {explainReport.audit_trail && explainReport.audit_trail.length > 0 && (
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3 mt-4">
                  <h4 className="text-xs font-bold font-mono uppercase text-slate-400 flex items-center gap-2">
                    <Layers className="h-4 w-4 text-indigo-400" />
                    Dedicated Audit Checkpoints for Decision #{explainReport.decision_id}
                  </h4>
                  <div className="space-y-2">
                    {explainReport.audit_trail.map((lg) => (
                      <div
                        key={lg.id}
                        className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2">
                          {getStageBadge(lg.stage)}
                          {getActorBadge(lg.actor)}
                          <span className="text-slate-200 font-medium">{lg.summary}</span>
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">
                          {new Date(lg.timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="py-20 text-center text-xs text-slate-500 bg-slate-900/50 border border-slate-800 rounded-2xl">
              Enter a Decision ID above or click &ldquo;Inspect 6 Questions&rdquo; on any audit timeline item to analyze.
            </div>
          )}
        </div>
      )}

      {/* TAB 3: PAYPAL WEBHOOKS STREAM */}
      {activeTab === "webhooks" && (
        <div className="space-y-4">
          {/* Webhooks Filter Bar */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-mono">Status Filter:</span>
              {["ALL", "PROCESSED", "RECEIVED", "FAILED"].map((st) => (
                <button
                  key={st}
                  onClick={() => setWebhookStatusFilter(st)}
                  className={`px-3 py-1 rounded-lg font-mono text-xs transition ${
                    webhookStatusFilter === st
                      ? "bg-indigo-600 text-white font-bold"
                      : "bg-slate-950 hover:bg-slate-800 text-slate-400 border border-slate-800"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            <button
              onClick={fetchWebhookEvents}
              disabled={isLoadingWebhooks}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold transition"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoadingWebhooks ? "animate-spin" : ""}`} />
              Refresh Webhooks
            </button>
          </div>

          {/* Webhooks Stream List */}
          {isLoadingWebhooks ? (
            <div className="py-16 text-center text-xs text-slate-400 bg-slate-900/50 border border-slate-800 rounded-2xl">
              <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-indigo-400" />
              Loading verified PayPal webhook events...
            </div>
          ) : webhookEvents.length === 0 ? (
            <div className="py-16 text-center text-xs text-slate-500 bg-slate-900/50 border border-slate-800 rounded-2xl">
              No PayPal webhook events received yet. Events dispatched from PayPal Sandbox will append live with cryptographic verification.
            </div>
          ) : (
            <div className="space-y-2.5">
              {webhookEvents.map((evt) => {
                const isExpanded = expandedWebhookId === evt.id;
                const isProcessed = evt.status === "PROCESSED";
                const isFailed = evt.status === "FAILED";

                return (
                  <div
                    key={evt.id}
                    className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden transition hover:border-slate-700"
                  >
                    <div
                      onClick={() => setExpandedWebhookId(isExpanded ? null : evt.id)}
                      className="p-4 flex items-center justify-between cursor-pointer gap-3"
                    >
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                            isProcessed
                              ? "text-emerald-400 bg-emerald-950/70 border-emerald-800"
                              : isFailed
                              ? "text-rose-400 bg-rose-950/70 border-rose-800"
                              : "text-amber-400 bg-amber-950/70 border-amber-800"
                          }`}
                        >
                          {evt.status}
                        </span>

                        <span className="text-xs font-mono font-bold text-cyan-300">
                          {evt.event_type}
                        </span>

                        <span className="text-[10px] font-mono text-slate-400">
                          ID: {evt.event_id}
                        </span>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="text-[10px] font-mono text-slate-500 hidden sm:inline">
                          {new Date(evt.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </span>
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-slate-400" />
                        )}
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="px-4 pb-4 pt-2 border-t border-slate-800/80 bg-slate-950/80 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono text-slate-400">
                            Signature Verification:{" "}
                            <span className="text-emerald-400 font-bold">
                              PASS (Cryptographically Verified via REST API)
                            </span>
                          </span>

                          <button
                            onClick={() => copyToClipboard(evt.payload, evt.id)}
                            className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-300 font-mono transition"
                          >
                            {copiedId === evt.id ? (
                              <>
                                <Check className="h-3 w-3 text-emerald-400" />
                                Copied!
                              </>
                            ) : (
                              <>
                                <Copy className="h-3 w-3" />
                                Copy JSON
                              </>
                            )}
                          </button>
                        </div>

                        {evt.error_message && (
                          <div className="p-2.5 rounded-xl bg-rose-950/50 border border-rose-900 text-xs text-rose-300">
                            Error: {evt.error_message}
                          </div>
                        )}

                        <pre className="text-[11px] font-mono text-slate-300 bg-slate-900/90 p-3 rounded-xl border border-slate-800/80 overflow-x-auto max-h-64 overflow-y-auto">
                          {(() => {
                            try {
                              return JSON.stringify(JSON.parse(evt.payload), null, 2);
                            } catch {
                              return evt.payload;
                            }
                          })()}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
