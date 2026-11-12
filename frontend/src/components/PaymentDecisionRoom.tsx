"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  AlertTriangle,
  CheckCircle2,
  Lock,
  ArrowRight,
  TrendingDown,
  Clock,
  ExternalLink,
  RefreshCw,
  Copy,
  Check,
  Scale,
  AlertOctagon,
  Sparkles,
  Info,
  Calendar,
  Layers,
  ChevronDown,
  UserCheck,
  CreditCard,
  Building2,
  FileText,
  PauseCircle,
  HelpCircle,
  Send,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  PaymentDecisionRoomResponse,
  PaymentDraft,
  DecisionRoomRiskSignal,
  DecisionRoomCommitmentItem,
  DecisionRoomAuditItem,
} from "@/types";

interface PaymentDecisionRoomProps {
  initialDraftId?: number | null;
  onRefreshParent?: () => void;
  currency?: string;
}

export const PaymentDecisionRoom: React.FC<PaymentDecisionRoomProps> = ({
  initialDraftId,
  onRefreshParent,
}) => {
  const [data, setData] = useState<PaymentDecisionRoomResponse | null>(null);
  const [draftsList, setDraftsList] = useState<PaymentDraft[]>([]);
  const [selectedDraftId, setSelectedDraftId] = useState<number | null>(initialDraftId || null);
  const [loading, setLoading] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Modals state
  const [rejectModalOpen, setRejectModalOpen] = useState<boolean>(false);
  const [rejectReason, setRejectReason] = useState<string>("");
  const [holdModalOpen, setHoldModalOpen] = useState<boolean>(false);
  const [holdNotes, setHoldNotes] = useState<string>("");
  const [reviewModalOpen, setReviewModalOpen] = useState<boolean>(false);
  const [reviewNotes, setReviewNotes] = useState<string>("");
  const [approvalNotes, setApprovalNotes] = useState<string>("");

  // Sandbox dual approval bypass option (for solo testing in hackathon demo)
  const [dualApprovalOverride, setDualApprovalOverride] = useState<boolean>(false);

  // Copied hash tooltip
  const [copiedHash, setCopiedHash] = useState<boolean>(false);

  // Load available drafts list for switcher
  const loadDraftsList = useCallback(async () => {
    try {
      const list = await api.getPaymentDrafts();
      setDraftsList(list);
      return list;
    } catch {
      return [];
    }
  }, []);

  // Fetch full decision room intelligence package
  const fetchDecisionRoom = useCallback(
    async (draftId: number, forceRecalculate: boolean = false) => {
      setLoading(true);
      setErrorMessage(null);
      try {
        const res = await api.getDecisionRoom(draftId, forceRecalculate);
        setData(res);
        setSelectedDraftId(res.overview.draft_id);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load Payment Decision Room";
        setErrorMessage(msg);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Initial load
  useEffect(() => {
    const init = async () => {
      const list = await loadDraftsList();
      if (initialDraftId) {
        fetchDecisionRoom(initialDraftId);
      } else if (list.length > 0) {
        fetchDecisionRoom(list[0].id);
      } else {
        // Automatically preload Normal demo scenario if database is empty
        handleLoadScenario("normal");
      }
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialDraftId]);

  // Load demo scenario helper
  const handleLoadScenario = async (scenario: "normal" | "suspicious") => {
    setLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const res = await api.loadDemoScenario(scenario);
      setData(res);
      setSelectedDraftId(res.overview.draft_id);
      await loadDraftsList();
      setSuccessMessage(
        scenario === "normal"
          ? "Loaded Hackathon Scenario 1: Normal Payment (Datadog Cloud Observability $280.00)"
          : "Loaded Hackathon Scenario 2: Suspicious Payment (Global Offshore FinTech $25,000.00)"
      );
      if (onRefreshParent) onRefreshParent();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load demo scenario";
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  // Re-run Guardian AI Scan
  const handleRescanRisk = async () => {
    if (!selectedDraftId) return;
    setActionLoading(true);
    setErrorMessage(null);
    try {
      await fetchDecisionRoom(selectedDraftId, true);
      setSuccessMessage("Guardian AI 10-signal risk evaluation refreshed successfully.");
      if (onRefreshParent) onRefreshParent();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Risk re-scan failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Approval Handlers
  const handleApprove = async () => {
    if (!data) return;
    setActionLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const draftId = data.overview.draft_id;
      const expectedHash = data.approval_workflow.details_hash || data.overview.details_hash || undefined;

      await api.approvePaymentDraft(draftId, approvalNotes || undefined, expectedHash, dualApprovalOverride);
      setApprovalNotes("");
      setSuccessMessage(
        data.approval_workflow.requires_dual_approval && data.approval_workflow.current_step === 1
          ? "Primary executive approval recorded. Step 1 of dual authorization complete."
          : "Payment authorization granted. Payment is now unlocked for settlement execution."
      );
      await fetchDecisionRoom(draftId);
      await loadDraftsList();
      if (onRefreshParent) onRefreshParent();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Approval failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Hold Handler
  const handleConfirmHold = async () => {
    if (!data) return;
    setActionLoading(true);
    try {
      await api.holdPaymentDraft(data.overview.draft_id, holdNotes || undefined);
      setHoldModalOpen(false);
      setHoldNotes("");
      setSuccessMessage("Payment draft placed on executive hold for further inquiry.");
      await fetchDecisionRoom(data.overview.draft_id);
      await loadDraftsList();
      if (onRefreshParent) onRefreshParent();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Hold request failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Review Handler
  const handleConfirmReview = async () => {
    if (!data) return;
    setActionLoading(true);
    try {
      await api.requestReviewDraft(data.overview.draft_id, reviewNotes || undefined);
      setReviewModalOpen(false);
      setReviewNotes("");
      setSuccessMessage("Review request broadcast to executive officers.");
      await fetchDecisionRoom(data.overview.draft_id);
      await loadDraftsList();
      if (onRefreshParent) onRefreshParent();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Review request failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Reject Handler
  const handleConfirmReject = async () => {
    if (!data) return;
    setActionLoading(true);
    try {
      await api.rejectPaymentDraft(data.overview.draft_id, rejectReason || "Declined by executive committee.");
      setRejectModalOpen(false);
      setRejectReason("");
      setSuccessMessage("Payment proposal formally rejected and archived in audit timeline.");
      await fetchDecisionRoom(data.overview.draft_id);
      await loadDraftsList();
      if (onRefreshParent) onRefreshParent();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Rejection failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Execute Payment via PayPal Sandbox or Provider
  const handleExecutePayment = async (method: "PAYPAL_SANDBOX" | "SIMULATED_PROVIDER") => {
    if (!data) return;
    setActionLoading(true);
    setErrorMessage(null);
    try {
      const res = await api.executePayment({
        draft_id: data.overview.draft_id,
        payment_method: method,
        idempotency_key: `exec-${data.overview.draft_id}-${Date.now()}`,
      });

      if (res.approval_url) {
        window.open(res.approval_url, "_blank");
      }
      setSuccessMessage(`Payment executed via ${method}. Transaction ID #${res.transaction_id}`);
      await fetchDecisionRoom(data.overview.draft_id);
      await loadDraftsList();
      if (onRefreshParent) onRefreshParent();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Execution failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  // Helpers for Risk Styling
  const getRiskColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case "CRITICAL":
        return {
          bg: "bg-red-950/60",
          border: "border-red-600/50",
          text: "text-red-400",
          badge: "bg-red-500/20 text-red-300 border-red-500/40",
          ring: "stroke-red-500",
          fill: "text-red-500",
        };
      case "HIGH":
        return {
          bg: "bg-amber-950/50",
          border: "border-amber-600/50",
          text: "text-amber-400",
          badge: "bg-amber-500/20 text-amber-300 border-amber-500/40",
          ring: "stroke-amber-500",
          fill: "text-amber-500",
        };
      case "MEDIUM":
        return {
          bg: "bg-yellow-950/40",
          border: "border-yellow-600/40",
          text: "text-yellow-400",
          badge: "bg-yellow-500/20 text-yellow-300 border-yellow-500/40",
          ring: "stroke-yellow-500",
          fill: "text-yellow-500",
        };
      default:
        return {
          bg: "bg-emerald-950/40",
          border: "border-emerald-600/40",
          text: "text-emerald-400",
          badge: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
          ring: "stroke-emerald-500",
          fill: "text-emerald-500",
        };
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status?.toUpperCase()) {
      case "APPROVED":
        return "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40";
      case "AWAITING_APPROVAL":
        return "bg-blue-500/20 text-blue-300 border border-blue-500/40";
      case "REVIEW_REQUIRED":
        return "bg-amber-500/20 text-amber-300 border border-amber-500/40";
      case "REJECTED":
        return "bg-red-500/20 text-red-300 border border-red-500/40";
      case "COMPLETED":
        return "bg-purple-500/20 text-purple-300 border border-purple-500/40";
      case "PROVIDER_PENDING":
        return "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40";
      default:
        return "bg-slate-700/50 text-slate-300 border border-slate-600";
    }
  };

  const riskColors = getRiskColor(data?.risk_assessment.risk_level || "LOW");

  return (
    <div className="space-y-6">
      {/* ========================================================================= */}
      {/* 1. DECISION ROOM CONTROL BAR & SCENARIO SELECTOR                          */}
      {/* ========================================================================= */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 md:p-6 shadow-xl backdrop-blur-md">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 rounded-xl">
              <Scale className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-xl font-bold text-white tracking-tight">Payment Decision Room</h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  Dual-Control Gateway
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic 10-signal risk evaluation, liquidity impact preview, and cryptographic dual-authorization.
              </p>
            </div>
          </div>

          {/* Quick Scenario & Switcher Pills */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => handleLoadScenario("normal")}
              disabled={loading || actionLoading}
              className="px-3 py-2 rounded-xl text-xs font-semibold bg-emerald-950/60 hover:bg-emerald-900/70 text-emerald-300 border border-emerald-600/50 flex items-center space-x-1.5 transition-all shadow-sm"
              title="Loads clean recurring vendor payment: Datadog $280.00"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Scenario 1: Normal ($280)</span>
            </button>

            <button
              onClick={() => handleLoadScenario("suspicious")}
              disabled={loading || actionLoading}
              className="px-3 py-2 rounded-xl text-xs font-semibold bg-red-950/60 hover:bg-red-900/70 text-red-300 border border-red-600/50 flex items-center space-x-1.5 transition-all shadow-sm"
              title="Loads critical risk offshore payment: Global Offshore $25,000.00"
            >
              <AlertOctagon className="w-3.5 h-3.5 text-red-400" />
              <span>Scenario 2: Suspicious ($25k)</span>
            </button>

            {/* Draft Switcher Dropdown */}
            <div className="relative">
              <select
                aria-label="Select Payment Proposal Draft"
                value={selectedDraftId || ""}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  if (id) {
                    setSelectedDraftId(id);
                    fetchDecisionRoom(id);
                  }
                }}
                disabled={loading || draftsList.length === 0}
                className="appearance-none bg-slate-950 text-slate-200 border border-slate-700 rounded-xl px-3 py-2 pr-8 text-xs font-medium focus:outline-none focus:border-cyan-500 transition-colors cursor-pointer"
              >
                {draftsList.map((d) => (
                  <option key={d.id} value={d.id}>
                    #{d.id} • {d.vendor_name || d.title} ({d.currency} ${d.amount?.toLocaleString()}) - {d.status}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            <button
              onClick={() => selectedDraftId && fetchDecisionRoom(selectedDraftId)}
              disabled={loading || !selectedDraftId}
              className="p-2 rounded-xl bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition"
              title="Refresh intelligence"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-cyan-400" : ""}`} />
            </button>
          </div>
        </div>

        {/* Global Success / Error Notification */}
        {successMessage && (
          <div className="mt-4 p-3 rounded-xl bg-emerald-950/50 border border-emerald-500/40 text-emerald-300 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{successMessage}</span>
            </div>
            <button
              onClick={() => setSuccessMessage(null)}
              className="text-emerald-400 hover:text-white font-bold text-sm ml-2"
            >
              ×
            </button>
          </div>
        )}

        {errorMessage && (
          <div className="mt-4 p-3 rounded-xl bg-red-950/50 border border-red-500/40 text-red-300 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-red-400 hover:text-white font-bold text-sm ml-2"
            >
              ×
            </button>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      {loading && !data ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-16 text-center">
          <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-4" />
          <h3 className="text-white font-semibold">Aggregating Financial Telemetry & Risk Assessment...</h3>
          <p className="text-slate-500 text-xs mt-1">Executing deterministic verification algorithms...</p>
        </div>
      ) : !data ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-16 text-center">
          <HelpCircle className="w-10 h-10 text-slate-500 mx-auto mb-4" />
          <h3 className="text-white font-semibold">No Payment Draft Selected</h3>
          <p className="text-slate-400 text-xs mt-1 max-w-md mx-auto">
            Choose an existing payment draft or load one of the PayPal AI Hackathon demonstration scenarios.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={() => handleLoadScenario("normal")}
              className="px-4 py-2 rounded-xl bg-emerald-600 text-white font-medium text-xs hover:bg-emerald-500 transition"
            >
              Load Scenario 1 (Normal $280)
            </button>
            <button
              onClick={() => handleLoadScenario("suspicious")}
              className="px-4 py-2 rounded-xl bg-red-600 text-white font-medium text-xs hover:bg-red-500 transition"
            >
              Load Scenario 2 (Suspicious $25k)
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* ========================================================================= */}
          {/* TOP BANNER: HERO PAYMENT OVERVIEW & RISK GAUGE                            */}
          {/* ========================================================================= */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md relative overflow-hidden">
            <div className="absolute -top-12 -right-12 w-48 h-48 bg-gradient-to-br from-cyan-600/10 to-blue-600/10 rounded-full blur-2xl pointer-events-none" />

            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
              {/* Left: Proposal Summary */}
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-mono text-cyan-400 font-semibold bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/50">
                    DRAFT #{data.overview.draft_id}
                  </span>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${getStatusBadge(data.overview.status)}`}>
                    {data.overview.status}
                  </span>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${riskColors.badge}`}>
                    RISK: {data.risk_assessment.risk_level} ({data.risk_assessment.risk_score}/100)
                  </span>
                  {data.risk_assessment.vendor_verified ? (
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-950/50 text-emerald-300 border border-emerald-500/30 flex items-center space-x-1">
                      <ShieldCheck className="w-3 h-3 text-emerald-400" />
                      <span>Verified Payee Domain</span>
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-950/50 text-amber-300 border border-amber-500/30 flex items-center space-x-1">
                      <AlertTriangle className="w-3 h-3 text-amber-400" />
                      <span>First-Time / Unverified Payee</span>
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-baseline gap-3">
                  <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
                    {data.overview.title}
                  </h1>
                  <span className="text-2xl md:text-3xl font-mono font-bold text-cyan-400">
                    {data.overview.currency} ${data.overview.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
                  <div className="flex items-center space-x-1.5">
                    <Building2 className="w-3.5 h-3.5 text-slate-500" />
                    <span>Vendor:</span>
                    <span className="text-slate-200 font-medium">{data.overview.vendor_name}</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="text-slate-500">Email:</span>
                    <span className="text-slate-300 font-mono">{data.overview.vendor_email}</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span>Created:</span>
                    <span className="text-slate-300">{new Date(data.overview.created_at).toLocaleDateString()}</span>
                  </div>
                  {data.overview.invoice_number && (
                    <div className="flex items-center space-x-1.5">
                      <FileText className="w-3.5 h-3.5 text-slate-500" />
                      <span>Invoice:</span>
                      <span className="text-cyan-300 font-mono">#{data.overview.invoice_number}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Right: Circular Score Ring & Verdict */}
              <div className="flex items-center gap-5 bg-slate-950/70 p-4 rounded-xl border border-slate-800">
                <div className="relative w-20 h-20 flex items-center justify-center shrink-0">
                  <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-slate-800"
                      strokeWidth="3.5"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className={`${riskColors.ring} transition-all duration-700 ease-out`}
                      strokeDasharray={`${data.risk_assessment.risk_score}, 100`}
                      strokeWidth="3.5"
                      strokeLinecap="round"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <div className="absolute flex flex-col items-center justify-center text-center">
                    <span className="text-lg font-bold font-mono text-white leading-none">
                      {Math.round(data.risk_assessment.risk_score)}
                    </span>
                    <span className="text-[9px] uppercase tracking-wider text-slate-400 mt-0.5">/ 100</span>
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Guardian Verdict</div>
                  <div className="text-sm font-bold text-white flex items-center space-x-1.5">
                    {data.risk_assessment.verdict === "SAFE_TO_PAY" ? (
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    ) : data.risk_assessment.verdict === "BLOCKED" ? (
                      <ShieldX className="w-4 h-4 text-red-400" />
                    ) : (
                      <ShieldAlert className="w-4 h-4 text-amber-400" />
                    )}
                    <span>{data.risk_assessment.verdict.replace(/_/g, " ")}</span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Recommended: <span className="text-slate-200 font-medium">{data.risk_assessment.recommended_action}</span>
                  </p>
                  <button
                    onClick={handleRescanRisk}
                    disabled={actionLoading}
                    className="mt-1 text-[11px] text-cyan-400 hover:text-cyan-300 font-medium flex items-center space-x-1 transition"
                  >
                    <RefreshCw className={`w-3 h-3 ${actionLoading ? "animate-spin" : ""}`} />
                    <span>Re-evaluate 10 Signals</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* ========================================================================= */}
          {/* TWO-COLUMN GRID: SECTION A & B & D (LEFT), SECTION C & E (RIGHT)          */}
          {/* ========================================================================= */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* ----------------------------------------------------------------------- */}
            {/* LEFT COLUMN: OVERVIEW, 10 SIGNALS RISK BREAKDOWN, CASH FLOW IMPACT      */}
            {/* ----------------------------------------------------------------------- */}
            <div className="lg:col-span-7 space-y-6">
              {/* SECTION A: PAYMENT OVERVIEW & CRYPTOGRAPHIC DETAILS */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-cyan-400" />
                    <span>Section A • Commercial Parameters & Tamper Fingerprint</span>
                  </h3>
                  <span className="text-[11px] text-slate-500 font-mono">Immutable Registry</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                    <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider">Payment Purpose</span>
                    <p className="text-slate-200 font-medium mt-1">
                      {data.overview.purpose || "Operational invoice payment"}
                    </p>
                  </div>

                  <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                    <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider">Category & Scope</span>
                    <p className="text-slate-200 font-medium mt-1">
                      {data.overview.category} • {data.overview.vendor_status} Vendor
                    </p>
                  </div>
                </div>

                {/* SHA-256 Fingerprint */}
                {data.overview.details_hash && (
                  <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs flex items-center justify-between">
                    <div className="space-y-0.5 overflow-hidden">
                      <div className="flex items-center space-x-1.5">
                        <Lock className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                        <span className="text-slate-400 font-semibold text-[11px]">Details Hash (SHA-256 Anti-Tamper):</span>
                      </div>
                      <p className="font-mono text-cyan-300 text-[11px] truncate">
                        {data.overview.details_hash}
                      </p>
                    </div>
                    <button
                      onClick={() => handleCopyHash(data.overview.details_hash!)}
                      className="ml-3 p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition shrink-0"
                      title="Copy fingerprint"
                    >
                      {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                )}
              </div>

              {/* SECTION B: INTELLIGENT 10-SIGNAL RISK ASSESSMENT */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                    <ShieldAlert className="w-4 h-4 text-cyan-400" />
                    <span>Section B • Guardian AI 10-Signal Risk Engine</span>
                  </h3>
                  <span className="text-[11px] text-slate-400">
                    {data.risk_assessment.signals.length} Signals Detected
                  </span>
                </div>

                {/* Plain-Language Explanation */}
                <div className={`p-4 rounded-xl border text-xs leading-relaxed ${riskColors.bg} ${riskColors.border}`}>
                  <div className="font-bold mb-1 flex items-center space-x-1.5 text-white">
                    <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span>Executive Summary & Risk Rationale:</span>
                  </div>
                  <p className="text-slate-200">{data.risk_assessment.plain_explanation}</p>
                </div>

                {/* Detected Signals Table */}
                <div className="space-y-2">
                  <span className="text-[11px] uppercase font-bold text-slate-400 tracking-wider">
                    Discrete Signal Breakdown
                  </span>
                  {data.risk_assessment.signals.length === 0 ? (
                    <div className="p-4 bg-emerald-950/30 border border-emerald-600/30 rounded-xl text-xs text-emerald-300 flex items-center space-x-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Zero fraud signals detected. Payment complies with all financial governance policies.</span>
                    </div>
                  ) : (
                    data.risk_assessment.signals.map((sig: DecisionRoomRiskSignal) => (
                      <div
                        key={sig.id}
                        className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                sig.severity === "CRITICAL"
                                  ? "bg-red-500/20 text-red-300 border border-red-500/30"
                                  : sig.severity === "HIGH"
                                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                                  : "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30"
                              }`}
                            >
                              {sig.severity}
                            </span>
                            <span className="text-xs font-semibold text-white">{sig.name}</span>
                          </div>
                          <span className="text-xs font-mono font-bold text-red-400">
                            +{sig.score_impact.toFixed(1)} pts
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-snug">{sig.description}</p>
                        <div className="text-[11px] text-cyan-300 font-mono bg-slate-900/80 px-2 py-1 rounded border border-slate-800">
                          Evidence: {sig.evidence}
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Missing Information / Required Audits */}
                {data.risk_assessment.missing_information.length > 0 && (
                  <div className="p-3 bg-amber-950/30 border border-amber-600/30 rounded-xl space-y-1 text-xs">
                    <span className="font-bold text-amber-300 flex items-center space-x-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                      <span>Missing Compliance Information:</span>
                    </span>
                    <ul className="list-disc list-inside text-slate-300 space-y-0.5 text-[11px] mt-1">
                      {data.risk_assessment.missing_information.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* SECTION D: CASH-FLOW IMPACT PREVIEW (DECIMAL-ACCURATE) */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                    <TrendingDown className="w-4 h-4 text-cyan-400" />
                    <span>Section D • Cash-Flow & Liquidity Impact Preview</span>
                  </h3>
                  <span className="text-[11px] text-slate-400 font-mono">Decimal-Accurate Arithmetic</span>
                </div>

                {/* 4 Financial Metrics Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider">Treasury Before</span>
                    <div className="text-sm font-bold font-mono text-white mt-1">
                      ${data.cash_flow_impact.available_cash_before.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider">Payout Amount</span>
                    <div className="text-sm font-bold font-mono text-cyan-400 mt-1">
                      -${data.cash_flow_impact.payment_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider">Treasury After</span>
                    <div className="text-sm font-bold font-mono text-emerald-400 mt-1">
                      ${data.cash_flow_impact.projected_cash_after.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider">Runway Impact</span>
                    <div className="text-sm font-bold font-mono text-amber-400 mt-1">
                      -{data.cash_flow_impact.runway_impact_days} Days
                    </div>
                  </div>
                </div>

                {/* Budget Consumption Bar */}
                <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex justify-between text-xs text-slate-300">
                    <span>
                      Monthly Budget: <span className="font-mono text-white">${data.cash_flow_impact.monthly_budget.toLocaleString()}</span>
                    </span>
                    <span>
                      Consumes: <span className="font-mono font-bold text-cyan-400">{data.cash_flow_impact.percentage_budget_consumed.toFixed(1)}%</span> of monthly budget
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-2 rounded-full transition-all duration-500 ${
                        data.cash_flow_impact.percentage_budget_consumed > 50
                          ? "bg-red-500"
                          : data.cash_flow_impact.percentage_budget_consumed > 20
                          ? "bg-amber-500"
                          : "bg-cyan-500"
                      }`}
                      style={{ width: `${Math.min(100, Math.max(2, data.cash_flow_impact.percentage_budget_consumed))}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>Current Spent: ${data.cash_flow_impact.monthly_spent_before.toLocaleString()}</span>
                    <span>Remaining After: ${data.cash_flow_impact.projected_remaining_budget.toLocaleString()}</span>
                  </div>
                </div>

                {/* Monthly Recurring Commitments Insight */}
                <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white flex items-center space-x-1.5">
                      <Layers className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Existing Monthly Recurring Commitments</span>
                    </span>
                    <span className="font-mono font-bold text-slate-200">
                      ${data.cash_flow_impact.commitments_monthly_total.toLocaleString()}/mo ({data.cash_flow_impact.active_commitments_count} subscriptions)
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                    {data.cash_flow_impact.commitments_sample.slice(0, 4).map((c: DecisionRoomCommitmentItem, idx: number) => (
                      <div key={idx} className="flex justify-between items-center p-2 rounded bg-slate-900 border border-slate-800 text-[11px]">
                        <span className="text-slate-300 truncate max-w-[120px]">{c.vendor_name}</span>
                        <span className="font-mono text-cyan-300">${c.amount.toLocaleString()}/mo</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* ----------------------------------------------------------------------- */}
            {/* RIGHT COLUMN: SECTION C (AI RECOMMENDATION) & SECTION E (DUAL APPROVE)  */}
            {/* ----------------------------------------------------------------------- */}
            <div className="lg:col-span-5 space-y-6">
              {/* SECTION C: GROUNDED AI RECOMMENDATION */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                    <span>Section C • AI CFO Advisory Intelligence</span>
                  </h3>
                  <span className="text-[10px] uppercase font-bold text-cyan-400 bg-cyan-950/70 px-2 py-0.5 rounded border border-cyan-800/40">
                    Grounded Telemetry
                  </span>
                </div>

                {/* 5 Structured Dimensions */}
                <div className="space-y-3 text-xs">
                  {/* 1. Why Risky */}
                  <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800 space-y-1">
                    <span className="font-bold text-amber-300 text-[11px] uppercase tracking-wider">
                      1. Root Cause Risk Analysis
                    </span>
                    <p className="text-slate-200 leading-relaxed text-[11px]">
                      {data.ai_recommendation.why_risky}
                    </p>
                  </div>

                  {/* 2. Verified Facts */}
                  <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800 space-y-1">
                    <span className="font-bold text-emerald-300 text-[11px] uppercase tracking-wider">
                      2. Verified Database Facts
                    </span>
                    <ul className="list-disc list-inside text-slate-300 space-y-0.5 text-[11px]">
                      {data.ai_recommendation.verified_facts.map((fact, idx) => (
                        <li key={idx}>{fact}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 3. Cash Flow Impact */}
                  <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800 space-y-1">
                    <span className="font-bold text-cyan-300 text-[11px] uppercase tracking-wider">
                      3. Cash-Flow & Liquidity Impact
                    </span>
                    <p className="text-slate-200 text-[11px] leading-relaxed">
                      {data.ai_recommendation.cash_flow_impact}
                    </p>
                  </div>

                  {/* 4. Required Verifications */}
                  <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800 space-y-1">
                    <span className="font-bold text-blue-300 text-[11px] uppercase tracking-wider">
                      4. Required Executive Verifications
                    </span>
                    <ul className="list-disc list-inside text-slate-300 space-y-0.5 text-[11px]">
                      {data.ai_recommendation.required_verifications.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 5. Recommended Reviewer Action */}
                  <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800 space-y-1">
                    <span className="font-bold text-purple-300 text-[11px] uppercase tracking-wider">
                      5. Recommended Sign-Off Action
                    </span>
                    <p className="text-slate-200 font-semibold text-[11px]">
                      {data.ai_recommendation.recommended_reviewer_action}
                    </p>
                  </div>
                </div>

                {/* AI Advisory Disclaimer */}
                <div className="p-2.5 rounded-lg bg-slate-950 text-[10px] text-slate-500 border border-slate-800/80 leading-normal">
                  <span className="font-semibold text-slate-400">Governance Guardrail: </span>
                  {data.ai_recommendation.disclaimer}
                </div>
              </div>

              {/* SECTION E: HUMAN-CONTROLLED PAYMENT APPROVAL & DUAL AUTHORIZATION */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                    <UserCheck className="w-4 h-4 text-cyan-400" />
                    <span>Section E • Dual Authorization Governance</span>
                  </h3>
                  <span className="text-[11px] font-semibold text-cyan-400">
                    Step {data.approval_workflow.current_step} of {data.approval_workflow.total_steps}
                  </span>
                </div>

                {/* Step indicator */}
                <div className="flex items-center justify-between gap-2 p-3 bg-slate-950/70 rounded-xl border border-slate-800">
                  <div className="flex items-center space-x-2">
                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        data.approval_workflow.primary_approver
                          ? "bg-emerald-500 text-white"
                          : data.approval_workflow.current_step === 1
                          ? "bg-cyan-600 text-white animate-pulse"
                          : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      1
                    </div>
                    <div className="text-xs">
                      <div className="font-semibold text-white">Primary Approval</div>
                      <div className="text-[10px] text-slate-400">
                        {data.approval_workflow.primary_approver
                          ? `Signed by ${data.approval_workflow.primary_approver.name}`
                          : "Pending Initial Officer"}
                      </div>
                    </div>
                  </div>

                  <ArrowRight className="w-4 h-4 text-slate-600" />

                  <div className="flex items-center space-x-2">
                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        data.approval_workflow.secondary_approver
                          ? "bg-emerald-500 text-white"
                          : data.approval_workflow.current_step === 2
                          ? "bg-cyan-600 text-white animate-pulse"
                          : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      2
                    </div>
                    <div className="text-xs">
                      <div className="font-semibold text-white">Secondary Sign-off</div>
                      <div className="text-[10px] text-slate-400">
                        {data.approval_workflow.secondary_approver
                          ? `Signed by ${data.approval_workflow.secondary_approver.name}`
                          : data.approval_workflow.requires_dual_approval
                          ? "Pending Co-Signer"
                          : "Not Required (Single Approval)"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Policy Reason & Warnings */}
                <div className="text-xs text-slate-300 p-3 bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-1">
                  <div className="font-semibold text-white">Policy Directives:</div>
                  <p className="text-[11px] text-slate-300">{data.approval_workflow.reason}</p>
                </div>

                {/* Mandatory Block Alert */}
                {data.approval_workflow.mandatory_block && (
                  <div className="p-3 bg-red-950/80 border border-red-500/60 rounded-xl text-xs text-red-200 space-y-1">
                    <div className="font-bold flex items-center space-x-1.5 text-red-400">
                      <AlertOctagon className="w-4 h-4" />
                      <span>CRITICAL POLICY BLOCK ACTIVE</span>
                    </div>
                    <p className="text-[11px]">
                      Guardian AI detected critical fraud or security violations. Approval is strictly locked to prevent unauthorized disbursement.
                    </p>
                  </div>
                )}

                {/* Four-Eyes Principle Separation Override (for Hackathon Testing) */}
                {data.approval_workflow.requires_dual_approval && data.approval_workflow.current_step === 2 && (
                  <div className="p-2.5 bg-blue-950/40 border border-blue-600/30 rounded-xl text-[11px] text-blue-300 flex items-center justify-between">
                    <span>Sandbox Four-Eyes Override (Hackathon Solo Demo)</span>
                    <input
                      type="checkbox"
                      checked={dualApprovalOverride}
                      onChange={(e) => setDualApprovalOverride(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-700 text-cyan-600 focus:ring-0 cursor-pointer"
                    />
                  </div>
                )}

                {/* Primary Action Buttons */}
                <div className="space-y-2 pt-2">
                  {/* Approve Button */}
                  {data.approval_workflow.can_approve && !data.approval_workflow.mandatory_block && (
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={approvalNotes}
                        onChange={(e) => setApprovalNotes(e.target.value)}
                        placeholder="Optional executive authorization notes..."
                        className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                      />
                      <button
                        onClick={handleApprove}
                        disabled={actionLoading}
                        className="w-full py-2.5 rounded-xl font-bold text-xs bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-lg shadow-emerald-900/30 flex items-center justify-center space-x-2 transition disabled:opacity-50"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>
                          {data.approval_workflow.requires_dual_approval && data.approval_workflow.current_step === 1
                            ? "Sign Step 1: Initial Executive Approval"
                            : data.approval_workflow.requires_dual_approval && data.approval_workflow.current_step === 2
                            ? "Sign Step 2: Final Dual Executive Authorization"
                            : "Authorize & Approve Payment"}
                        </span>
                      </button>
                    </div>
                  )}

                  {/* PayPal Sandbox Execution Button */}
                  {data.overview.status === "APPROVED" && (
                    <div className="pt-2 border-t border-slate-800 space-y-2">
                      <div className="text-[11px] text-emerald-400 font-semibold flex items-center space-x-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Payment Fully Approved • Ready for Disbursement</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          onClick={() => handleExecutePayment("PAYPAL_SANDBOX")}
                          disabled={actionLoading}
                          className="py-2.5 rounded-xl font-bold text-xs bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white shadow-md flex items-center justify-center space-x-1.5 transition disabled:opacity-50"
                        >
                          <CreditCard className="w-3.5 h-3.5" />
                          <span>PayPal Sandbox</span>
                        </button>
                        <button
                          onClick={() => handleExecutePayment("SIMULATED_PROVIDER")}
                          disabled={actionLoading}
                          className="py-2.5 rounded-xl font-bold text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center justify-center space-x-1.5 transition disabled:opacity-50"
                        >
                          <Send className="w-3.5 h-3.5" />
                          <span>Direct Settlement</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Secondary Management Buttons: Hold, Review, Reject */}
                  {data.overview.status !== "COMPLETED" && (
                    <div className="grid grid-cols-3 gap-2 pt-2">
                      <button
                        onClick={() => setHoldModalOpen(true)}
                        disabled={actionLoading}
                        className="py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs flex items-center justify-center space-x-1 transition"
                      >
                        <PauseCircle className="w-3.5 h-3.5" />
                        <span>Hold</span>
                      </button>

                      <button
                        onClick={() => setReviewModalOpen(true)}
                        disabled={actionLoading}
                        className="py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs flex items-center justify-center space-x-1 transition"
                      >
                        <HelpCircle className="w-3.5 h-3.5" />
                        <span>Inquire</span>
                      </button>

                      <button
                        onClick={() => setRejectModalOpen(true)}
                        disabled={actionLoading}
                        className="py-2 rounded-xl bg-red-950/60 hover:bg-red-900/60 text-red-300 border border-red-800/50 font-semibold text-xs flex items-center justify-center space-x-1 transition"
                      >
                        <ShieldX className="w-3.5 h-3.5" />
                        <span>Reject</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* PayPal Order Details if already in flight or settled */}
                {data.paypal_status.order_id && (
                  <div className="mt-3 p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs space-y-1">
                    <div className="text-[10px] uppercase font-bold text-cyan-400">PayPal REST Gateway Status</div>
                    <div className="flex justify-between font-mono text-[11px]">
                      <span className="text-slate-400">Order ID:</span>
                      <span className="text-slate-200">{data.paypal_status.order_id}</span>
                    </div>
                    {data.paypal_status.capture_id && (
                      <div className="flex justify-between font-mono text-[11px]">
                        <span className="text-slate-400">Capture ID:</span>
                        <span className="text-emerald-400">{data.paypal_status.capture_id}</span>
                      </div>
                    )}
                    {data.paypal_status.approval_url && (
                      <a
                        href={data.paypal_status.approval_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-cyan-400 hover:underline flex items-center space-x-1 text-[11px] mt-1"
                      >
                        <span>Open PayPal Sandbox Approval Flow</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ========================================================================= */}
          {/* SECTION F: PAYMENT AUDIT TIMELINE (CHRONOLOGICAL EVENT STREAM)             */}
          {/* ========================================================================= */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>Section F • Payment Audit & Verification Timeline</span>
              </h3>
              <span className="text-xs text-slate-400 font-mono">
                {data.audit_timeline.length} Recorded Events
              </span>
            </div>

            {data.audit_timeline.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500">
                No prior audit events recorded for this proposal.
              </div>
            ) : (
              <div className="space-y-3 relative before:absolute before:inset-0 before:left-4 before:w-0.5 before:bg-slate-800">
                {data.audit_timeline.map((item: DecisionRoomAuditItem) => (
                  <div key={item.id} className="relative flex items-start space-x-3 pl-8">
                    <div className="absolute left-2.5 top-1.5 w-3 h-3 rounded-full bg-cyan-500 border-2 border-slate-950 shadow" />
                    <div className="w-full bg-slate-950/70 border border-slate-800 p-3 rounded-xl space-y-1">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center space-x-2">
                          <span className="text-[10px] font-bold uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/40">
                            {item.stage}
                          </span>
                          <span className="text-xs font-semibold text-white">{item.action}</span>
                          <span className="text-[11px] text-slate-400">by {item.actor}</span>
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">
                          {new Date(item.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-xs text-slate-200">{item.summary}</p>
                      {item.details && (
                        <p className="text-[11px] font-mono text-slate-400 bg-slate-900/60 p-1.5 rounded">
                          {item.details}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* ========================================================================= */}
      {/* MODALS: REJECT, HOLD, REVIEW INQUIRY                                      */}
      {/* ========================================================================= */}
      {/* Reject Modal */}
      {rejectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center space-x-3 text-red-400">
              <ShieldX className="w-6 h-6" />
              <h3 className="text-lg font-bold text-white">Reject Payment Proposal</h3>
            </div>
            <p className="text-xs text-slate-400">
              Please specify the audit rationale for declining payment. This explanation will be permanently recorded in the immutable audit trail.
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g., Unverified offshore entity with critical risk flags."
              rows={3}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setRejectModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmReject}
                disabled={actionLoading}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-red-600 hover:bg-red-500 text-white transition disabled:opacity-50"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Hold Modal */}
      {holdModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center space-x-3 text-amber-400">
              <PauseCircle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-white">Place Payment on Executive Hold</h3>
            </div>
            <p className="text-xs text-slate-400">
              Holding a payment suspends approval and resets status to REVIEW_REQUIRED until questions are answered.
            </p>
            <textarea
              value={holdNotes}
              onChange={(e) => setHoldNotes(e.target.value)}
              placeholder="Reason for hold, e.g. awaiting contract addendum..."
              rows={3}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setHoldModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmHold}
                disabled={actionLoading}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white transition disabled:opacity-50"
              >
                Place on Hold
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Review Request Modal */}
      {reviewModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center space-x-3 text-blue-400">
              <HelpCircle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-white">Request Executive Review</h3>
            </div>
            <p className="text-xs text-slate-400">
              Notify the executive team to review this proposal before any further actions can proceed.
            </p>
            <textarea
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="Explain what needs to be reviewed..."
              rows={3}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setReviewModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmReview}
                disabled={actionLoading}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition disabled:opacity-50"
              >
                Broadcast Review Request
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

